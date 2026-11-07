#!/usr/bin/env python3
"""WorkBuddy <-> OhUrTeach LMS One-Time Pairing & Scoped MCP Connector CLI.

Security & Credential Storage Invariants (WB-SUMMON-PAIRING-105):
1. Credentials (scoped connector token `omt_mcp_...` and PKCE `code_verifier`) are stored
   ONLY inside the WorkBuddy account-scoped connector vault:
   `~/.workbuddy-ai/connectors/<account-uuid>/.credentials.ohurteach.v3.json`
2. Payload encryption binds Windows DPAPI (`CryptProtectData`) + HMAC-SHA256 entropy
   derived from the WorkBuddy account's `.master.key` and `accountIdentityKey`
   (with authenticated HMAC-SHA256 stream cipher fallback on non-Windows POSIX).
3. Raw tokens and PKCE verifiers are NEVER printed to stdout, stderr, logs, chat,
   prompt context, or agent memory.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
import ctypes.wintypes
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

PUBLIC_LMS_URL = "https://out.satz11.my.id"
DEFAULT_LMS_URL = os.environ.get("OMT_LMS_URL", PUBLIC_LMS_URL).rstrip("/")
VAULT_FILENAME = ".credentials.ohurteach.v3.json"


def _test_mode() -> bool:
    return os.environ.get("OMT_PAIRING_TEST_MODE") == "1" and bool(os.environ.get("WORKBUDDY_CONFIG_DIR"))


def _vault_filename() -> str:
    return ".credentials.ohurteach.test.v3.json" if _test_mode() else VAULT_FILENAME


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_encrypt(plaintext: bytes, entropy: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_buf = ctypes.create_string_buffer(plaintext, len(plaintext))
    ent_buf = ctypes.create_string_buffer(entropy, len(entropy))
    in_blob = DATA_BLOB(len(plaintext), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
    ent_blob = DATA_BLOB(len(entropy), ctypes.cast(ent_buf, ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    CRYPTPROTECT_UI_FORBIDDEN = 0x01
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "OhUrTeachWorkBuddyConnector",
        ctypes.byref(ent_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise RuntimeError("Windows DPAPI CryptProtectData failed")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_decrypt(ciphertext: bytes, entropy: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_buf = ctypes.create_string_buffer(ciphertext, len(ciphertext))
    ent_buf = ctypes.create_string_buffer(entropy, len(entropy))
    in_blob = DATA_BLOB(len(ciphertext), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
    ent_blob = DATA_BLOB(len(entropy), ctypes.cast(ent_buf, ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    CRYPTPROTECT_UI_FORBIDDEN = 0x01
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        ctypes.byref(ent_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise RuntimeError("Windows DPAPI CryptUnprotectData failed (account/key mismatch)")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _stream_xor(data: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    while offset < len(data):
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        chunk = data[offset : offset + 32]
        for i, b in enumerate(chunk):
            out[offset + i] = b ^ block[i]
        offset += len(chunk)
        counter += 1
    return bytes(out)


def resolve_workbuddy_account_vault(override_account: str | None = None) -> tuple[Path, str, bytes]:
    wb_root = Path(os.environ.get("WORKBUDDY_CONFIG_DIR", Path.home() / ".workbuddy-ai"))
    connectors_dir = wb_root / "connectors"
    candidates: list[Path] = []
    if override_account:
        try:
            account = str(UUID(override_account))
        except ValueError as exc:
            raise ValueError("WorkBuddy account must be a UUID") from exc
        candidates.append(connectors_dir / account)
    elif connectors_dir.is_dir():
        for child in sorted(connectors_dir.iterdir()):
            if child.is_dir() and (child / ".master.key").is_file():
                candidates.append(child)
    if not candidates:
        raise RuntimeError("WorkBuddy account connector directory with .master.key not found")
    if len(candidates) != 1:
        raise RuntimeError("Multiple WorkBuddy accounts found. Select the active account explicitly.")
    acct_dir = candidates[0]
    master_key = (acct_dir / ".master.key").read_bytes()
    if len(master_key) < 16:
        raise RuntimeError("Invalid WorkBuddy .master.key")
    account_identity_key = acct_dir.name + "||enterprise"
    states_v3 = acct_dir / "connector-states.v3.json"
    if states_v3.is_file():
        try:
            meta = json.loads(states_v3.read_text(encoding="utf-8"))
            if isinstance(meta.get("accountIdentityKey"), str) and meta["accountIdentityKey"]:
                account_identity_key = meta["accountIdentityKey"]
        except Exception:
            pass
    entropy = hmac.new(master_key, account_identity_key.encode("utf-8"), hashlib.sha256).digest()
    return acct_dir, account_identity_key, entropy


def save_vault_state(state: dict, override_account: str | None = None) -> Path:
    acct_dir, account_identity_key, entropy = resolve_workbuddy_account_vault(override_account)
    raw = json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")
    nonce = secrets.token_bytes(16)
    enc_key = hmac.new(entropy, b"enc:" + nonce, hashlib.sha256).digest()
    mac_key = hmac.new(entropy, b"mac:" + nonce, hashlib.sha256).digest()
    masked = _stream_xor(raw, enc_key, nonce)
    if os.name == "nt":
        sealed = _dpapi_encrypt(masked, entropy)
        scheme = "dpapi+hkdf-sha256"
    else:
        sealed = masked
        scheme = "hkdf-sha256-stream"
    tag = hmac.new(mac_key, sealed, hashlib.sha256).hexdigest()
    envelope = {
        "version": 3,
        "connector": "ohurteach-lms",
        "accountIdentityKeyHash": hashlib.sha256(account_identity_key.encode("utf-8")).hexdigest()[:16],
        "scheme": scheme,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(sealed).decode("ascii"),
        "tag": tag,
        "updatedAt": int(time.time()),
    }
    vault_path = acct_dir / _vault_filename()
    vault_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return vault_path


def load_vault_state(override_account: str | None = None) -> tuple[dict, Path, str]:
    acct_dir, account_identity_key, entropy = resolve_workbuddy_account_vault(override_account)
    vault_path = acct_dir / _vault_filename()
    if not vault_path.is_file():
        return {}, vault_path, account_identity_key
    envelope = json.loads(vault_path.read_text(encoding="utf-8"))
    expected_acct_hash = hashlib.sha256(account_identity_key.encode("utf-8")).hexdigest()[:16]
    if envelope.get("accountIdentityKeyHash") != expected_acct_hash:
        raise RuntimeError("Vault accountIdentityKey mismatch")
    nonce = base64.b64decode(envelope["nonce"])
    sealed = base64.b64decode(envelope["ciphertext"])
    mac_key = hmac.new(entropy, b"mac:" + nonce, hashlib.sha256).digest()
    expected_tag = hmac.new(mac_key, sealed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_tag, envelope.get("tag", "")):
        raise RuntimeError("Vault authentication tag verification failed")
    if envelope.get("scheme") == "dpapi+hkdf-sha256" and os.name == "nt":
        masked = _dpapi_decrypt(sealed, entropy)
    else:
        masked = sealed
    enc_key = hmac.new(entropy, b"enc:" + nonce, hashlib.sha256).digest()
    raw = _stream_xor(masked, enc_key, nonce)
    return json.loads(raw.decode("utf-8")), vault_path, account_identity_key


def _http_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> tuple[int, dict]:
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin != PUBLIC_LMS_URL and not (_test_mode() and origin == "http://127.0.0.1:18871"):
        raise ValueError("Untrusted LMS origin")
    req_headers = {
        "Accept": "application/json",
        "User-Agent": "OhUrTeach-WorkBuddy-Connector/1.1.6",
    }
    if headers:
        req_headers.update(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body.strip() else {"detail": body}
        except Exception:
            parsed = {"detail": body}
        return err.code, parsed


def _try_exchange_pending(state: dict, base_url: str, override_account: str | None = None) -> tuple[dict, bool]:
    pending = state.get("pending_pairing")
    if not isinstance(pending, dict):
        return state, False
    req_id = pending.get("request_id")
    code = pending.get("pairing_code")
    verifier = pending.get("code_verifier")
    expires_at = float(pending.get("expires_at") or 0)
    if not req_id or not code or not verifier:
        return state, False
    if expires_at <= time.time():
        state["last_expired_pairing"] = {
            "request_id": req_id,
            "pairing_code": code,
            "expired_at": expires_at,
        }
        state.pop("pending_pairing", None)
        save_vault_state(state, override_account)
        return state, False

    status_code, body = _http_json(
        f"{base_url}/mcp/pairing/exchange",
        method="POST",
        payload={
            "request_id": req_id,
            "pairing_code": code,
            "code_verifier": verifier,
        },
    )
    if status_code == 200 and body.get("status") == "CONSUMED" and body.get("token"):
        state["active_credential"] = {
            "token": body["token"],
            "token_id": body.get("token_id", ""),
            "role": body.get("role", "connector"),
            "actor": body.get("actor", "owner"),
            "workspace": body.get("workspace", "personal"),
            "expires": body.get("expires", 0),
            "scope": body.get("scope", []),
            "paired_at": time.time(),
            "paired_via_request_id": req_id,
            "paired_code_masked": code[:8] + "-****",
        }
        state["last_consumed_pairing"] = {
            "request_id": req_id,
            "pairing_code": code,
            "code_verifier": verifier,
            "consumed_at": time.time(),
        }
        state.pop("pending_pairing", None)
        state.pop("last_disconnect_reason", None)
        save_vault_state(state, override_account)
        return state, True
    if status_code in (403, 409):
        state.pop("pending_pairing", None)
        save_vault_state(state, override_account)
    return state, False


def _verify_active_token(state: dict, base_url: str, override_account: str | None = None) -> tuple[bool, dict | None, str | None]:
    cred = state.get("active_credential")
    if not isinstance(cred, dict) or not cred.get("token"):
        return False, None, state.get("last_disconnect_reason")
    token = cred["token"]
    status_code, rpc_body = _http_json(
        f"{base_url}/mcp",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": base_url,
        },
        payload={
            "jsonrpc": "2.0",
            "id": "ident-check",
            "method": "tools/call",
            "params": {"name": "ohurteach_inspect_identity", "arguments": {}},
        },
    )
    if status_code == 200 and "result" in rpc_body and not rpc_body["result"].get("isError"):
        ident = rpc_body["result"].get("structuredContent")
        if not ident:
            text_items = rpc_body["result"].get("content") or []
            if text_items and "text" in text_items[0]:
                ident = json.loads(text_items[0]["text"])
        return True, ident, None

    if status_code == 403:
        reason = "TOKEN_REVOKED_OR_EXPIRED"
        state.pop("active_credential", None)
        state["last_disconnect_reason"] = reason
        save_vault_state(state, override_account)
        return False, None, reason
    return False, None, f"HTTP_{status_code}"


def cmd_inspect_identity(args: argparse.Namespace) -> int:
    base_url = args.lms_url.rstrip("/")
    state, vault_path, account_identity_key = load_vault_state(args.account)
    account_id = account_identity_key.split("||")[0]

    # Step 1: If there is a pending pairing that was approved in LMS, exchange it automatically
    state, just_exchanged = _try_exchange_pending(state, base_url, args.account)

    # Step 2: Verify active credential with MCP identity tool
    valid, ident, disconnect_reason = _verify_active_token(state, base_url, args.account)
    if valid and ident:
        cred = state.get("active_credential") or {}
        out = {
            "connection_status": "CONNECTED",
            "authenticated": True,
            "just_paired": just_exchanged,
            "account_id": account_id,
            "vault_file": str(vault_path.name),
            "credential_storage": "local_workbuddy_account_vault_dpapi_hkdf (outside chat, prompt, and agent memory)",
            "token_id": cred.get("token_id", ""),
            "paired_code_masked": cred.get("paired_code_masked", ""),
            "actor": ident.get("actor", "owner"),
            "workspace": ident.get("workspace", "personal"),
            "role": ident.get("role", "connector"),
            "allowed_tools": ident.get("allowed_tools", []),
            "forbidden_capabilities": ident.get("forbidden_capabilities", []),
            "lms_url": base_url + "/",
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    # Step 3: Not connected (missing, expired, or revoked)
    if not args.pair_if_disconnected:
        out = {
            "connection_status": "DISCONNECTED",
            "authenticated": False,
            "reason": disconnect_reason or "NOT_CONNECTED",
            "account_id": account_id,
            "lms_url": base_url + "/",
            "hint": "Jalankan kembali dengan --pair-if-disconnected ketika guru ingin menyambungkan WorkBuddy ke LMS.",
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    # Check if there is still a fresh pending pairing in the vault (unless --force-new-code)
    pending = state.get("pending_pairing")
    now = time.time()
    if (
        not args.force_new_code
        and isinstance(pending, dict)
        and float(pending.get("expires_at") or 0) - now > 90
    ):
        out = {
            "connection_status": "PAIRING_REQUIRED",
            "authenticated": False,
            "reason": disconnect_reason or "NOT_CONNECTED",
            "pairing_code": pending["pairing_code"],
            "request_id": pending["request_id"],
            "expires_in_seconds": int(float(pending["expires_at"]) - now),
            "verification_uri": base_url + "/",
            "requested_scope": pending.get("requested_scope", []),
            "account_id": account_id,
            "credential_storage": "local_workbuddy_account_vault_dpapi_hkdf (outside chat, prompt, and agent memory)",
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    # Request a new short-lived one-time pairing code from LMS
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).hexdigest()
    status_code, start_body = _http_json(
        f"{base_url}/mcp/pairing/start",
        method="POST",
        payload={
            "code_challenge": code_challenge,
            "client_label": "workbuddy-ohurteach-workspace",
            "ttl_seconds": args.ttl,
        },
    )
    if status_code != 200 or "pairing_code" not in start_body:
        print(
            json.dumps(
                {
                    "connection_status": "PAIRING_ERROR",
                    "authenticated": False,
                    "http_status": status_code,
                    "error": start_body.get("detail", "Failed to start pairing"),
                    "lms_url": base_url + "/",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1

    state["pending_pairing"] = {
        "request_id": start_body["request_id"],
        "pairing_code": start_body["pairing_code"],
        "code_verifier": code_verifier,
        "created_at": start_body.get("created_at", now),
        "expires_at": start_body["expires_at"],
        "requested_scope": start_body.get("requested_scope", []),
    }
    save_vault_state(state, args.account)
    out = {
        "connection_status": "PAIRING_REQUIRED",
        "authenticated": False,
        "reason": disconnect_reason or "NOT_CONNECTED",
        "pairing_code": start_body["pairing_code"],
        "request_id": start_body["request_id"],
        "expires_in_seconds": start_body.get("expires_in_seconds", args.ttl),
        "verification_uri": start_body.get("verification_uri", base_url + "/"),
        "requested_scope": start_body.get("requested_scope", []),
        "account_id": account_id,
        "credential_storage": "local_workbuddy_account_vault_dpapi_hkdf (outside chat, prompt, and agent memory)",
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_search_sources(args: argparse.Namespace) -> int:
    base_url = args.lms_url.rstrip("/")
    state, _, _ = load_vault_state(args.account)
    state, _ = _try_exchange_pending(state, base_url, args.account)
    cred = state.get("active_credential")
    if not isinstance(cred, dict) or not cred.get("token"):
        print(json.dumps({"error": "NOT_CONNECTED", "hint": "Run inspect-identity --pair-if-disconnected first."}, ensure_ascii=False))
        return 1
    tool_args: dict = {"projection": args.projection}
    if args.source_id:
        tool_args["source_id"] = args.source_id
    if args.query:
        tool_args["query"] = args.query
    status_code, rpc_body = _http_json(
        f"{base_url}/mcp",
        method="POST",
        headers={
            "Authorization": f"Bearer {cred['token']}",
            "Origin": base_url,
        },
        payload={
            "jsonrpc": "2.0",
            "id": "search-sources",
            "method": "tools/call",
            "params": {"name": "ohurteach_search_library_sources", "arguments": tool_args},
        },
    )
    if status_code != 200 or "result" not in rpc_body or rpc_body["result"].get("isError"):
        print(json.dumps({"error": "MCP_SEARCH_FAILED", "http_status": status_code, "response": rpc_body}, ensure_ascii=False))
        return 1
    structured = rpc_body["result"].get("structuredContent")
    if structured is None:
        structured = json.loads(rpc_body["result"]["content"][0]["text"])
    print(json.dumps({"ok": True, "sources": structured}, indent=2, ensure_ascii=False))
    return 0


def cmd_save_private_draft(args: argparse.Namespace) -> int:
    base_url = args.lms_url.rstrip("/")
    state, _, _ = load_vault_state(args.account)
    state, _ = _try_exchange_pending(state, base_url, args.account)
    cred = state.get("active_credential")
    if not isinstance(cred, dict) or not cred.get("token"):
        print(json.dumps({"error": "NOT_CONNECTED", "hint": "Run inspect-identity --pair-if-disconnected first."}, ensure_ascii=False))
        return 1
    payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    status_code, rpc_body = _http_json(
        f"{base_url}/mcp",
        method="POST",
        headers={
            "Authorization": f"Bearer {cred['token']}",
            "Origin": base_url,
        },
        payload={
            "jsonrpc": "2.0",
            "id": "save-private-draft",
            "method": "tools/call",
            "params": {"name": "ohurteach_save_private_draft", "arguments": payload},
        },
        timeout=30,
    )
    if status_code != 200 or "result" not in rpc_body or rpc_body["result"].get("isError"):
        print(json.dumps({"error": "MCP_SAVE_DRAFT_FAILED", "http_status": status_code, "response": rpc_body}, ensure_ascii=False))
        return 1
    structured = rpc_body["result"].get("structuredContent")
    if structured is None:
        structured = json.loads(rpc_body["result"]["content"][0]["text"])
    print(json.dumps({"ok": True, "receipt": structured}, indent=2, ensure_ascii=False))
    return 0


def cmd_verify_negative(args: argparse.Namespace) -> int:
    base_url = args.lms_url.rstrip("/")
    state, _, _ = load_vault_state(args.account)
    cred = state.get("active_credential") or {}
    last_consumed = state.get("last_consumed_pairing") or {}
    token = cred.get("token")
    if not token:
        print(json.dumps({"error": "NO_ACTIVE_TOKEN"}, ensure_ascii=False))
        return 1

    results: dict = {}
    if last_consumed.get("request_id") and last_consumed.get("pairing_code") and last_consumed.get("code_verifier"):
        sc_reuse, body_reuse = _http_json(
            f"{base_url}/mcp/pairing/exchange",
            method="POST",
            payload={
                "request_id": last_consumed["request_id"],
                "pairing_code": last_consumed["pairing_code"],
                "code_verifier": last_consumed["code_verifier"],
            },
        )
        results["old_pairing_code_reuse_exchange"] = {
            "pairing_code_masked": last_consumed["pairing_code"][:8] + "-****",
            "http_status": sc_reuse,
            "rejected": sc_reuse == 409,
            "detail": body_reuse.get("detail", ""),
        }

    auth_headers = {"Authorization": f"Bearer {token}", "Origin": base_url}
    sc_appr, body_appr = _http_json(
        f"{base_url}/jobs/{args.run_id}/approve",
        method="POST",
        headers=auth_headers,
        payload={"manifest": args.manifest, "visual_confirmed": True},
    )
    results["token_approve_draft"] = {
        "http_status": sc_appr,
        "rejected": sc_appr == 403,
        "detail": body_appr.get("detail", ""),
    }

    sc_pub, body_pub = _http_json(
        f"{base_url}/jobs/{args.run_id}/publish",
        method="POST",
        headers=auth_headers,
        payload={"manifest": args.manifest},
    )
    results["token_publish_draft"] = {
        "http_status": sc_pub,
        "rejected": sc_pub == 403,
        "detail": body_pub.get("detail", ""),
    }

    sc_tok, body_tok = _http_json(
        f"{base_url}/mcp/tokens",
        method="POST",
        headers=auth_headers,
        payload={"label": "illegal-escalation"},
    )
    results["token_issue_new_token"] = {
        "http_status": sc_tok,
        "rejected": sc_tok == 403,
        "detail": body_tok.get("detail", ""),
    }

    print(json.dumps({"ok": True, "negative_tests": results}, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OhUrTeach WorkBuddy One-Time Pairing & MCP Connector")
    p.add_argument("--lms-url", default=DEFAULT_LMS_URL, help="Base URL of OhUrTeach LMS")
    p.add_argument("--account", default=None, help="Optional WorkBuddy account UUID override")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_id = sub.add_parser("inspect-identity", help="Verify connection identity or request a one-time pairing code")
    p_id.add_argument("--pair-if-disconnected", action="store_true", help="Request a short-lived one-time pairing code if not connected")
    p_id.add_argument("--force-new-code", action="store_true", help="Force generating a fresh pairing code when disconnected")
    p_id.add_argument("--ttl", type=int, default=300, help="Pairing code TTL in seconds (60..600)")
    p_id.set_defaults(func=cmd_inspect_identity)

    p_src = sub.add_parser("search-sources", help="Read authorized sources from LMS Library via MCP")
    p_src.add_argument("--source-id", default=None, help="Source ID (e.g. BIO-01 or BIO-01-v1)")
    p_src.add_argument("--query", default=None, help="Optional search query")
    p_src.add_argument("--projection", choices=["student", "teacher"], default="student")
    p_src.set_defaults(func=cmd_search_sources)

    p_save = sub.add_parser("save-private-draft", help="Save validated draft to LMS as UNAPPROVED PRIVATE_ONLY draft")
    p_save.add_argument("--payload-file", required=True, help="Path to JSON payload for ohurteach_save_private_draft")
    p_save.set_defaults(func=cmd_save_private_draft)

    p_neg = sub.add_parser("verify-negative-boundaries", help="Verify old pairing code reuse rejection and token approve/publish 403")
    p_neg.add_argument("--run-id", required=True, help="Draft run_id to test approve/publish rejection")
    p_neg.add_argument("--manifest", required=True, help="Draft manifest hash")
    p_neg.set_defaults(func=cmd_verify_negative)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
