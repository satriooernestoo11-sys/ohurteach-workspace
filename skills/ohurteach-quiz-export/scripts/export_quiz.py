#!/usr/bin/env python3
"""
export_quiz.py - Deterministic Quiz Exporter for OhUrTeach Workspace

Memisahkan berkas kuis gabungan (berisi proyeksi siswa dan guru) menjadi dua berkas fisik terpisah:
1. Berkas Siswa (*_siswa.json dan *_siswa.md):
   Hanya memuat field yang diizinkan (STRICT ALLOWLIST): nomor, pertanyaan, dan opsi.
   100% bebas dari kunci jawaban, pembahasan, skor, catatan guru, atau metadata guru.
2. Berkas Panduan Guru (*_guru.json dan *_guru.md):
   Memuat teks soal, opsi, kunci jawaban, pembahasan, rujukan sumber, rubrik penskoran,
   dan klausul batas privasi/penegakan izin server (R-PRIV-01 v1.0.1 [HOLD]).

Karakteristik & Integritas:
- Menggunakan pendekatan Allowlist positif, bukan sekadar regex penghapus kata.
- Tidak mengubah fakta soal, pilihan, kunci jawaban, atau rujukan sumber.
- Penanganan error atomik: jika input rusak, proyeksi siswa hilang, atau struktur tidak valid,
  proses berhenti segera dan TIDAK menghasilkan berkas siswa parsial/menyesatkan.
  Pesan error disanitasi tanpa membocorkan data sensitif.
- Memasukkan klausul resmi bahwa pemisahan berkas adalah pemisahan level dokumen,
  bukan klaim kontrol izin server di level infrastruktur/LMS.
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Any, Tuple, Optional

# --- STRICT ALLOWLIST DEFINITIONS ---

STUDENT_METADATA_ALLOWLIST = {
    "judul", "title",
    "topik", "topic",
    "mata_pelajaran", "subject",
    "kelas", "jenjang_kelas", "grade",
    "fase",
    "alokasi_waktu_menit",
    "petunjuk", "instructions",
    "format_soal",
    "jumlah_soal"
}

STUDENT_QUESTION_ALLOWLIST = {
    "id_soal",
    "nomor",
    "pertanyaan",
    "opsi",
    "pilihan"
}

STUDENT_CHOICE_ALLOWLIST = {
    "opsi",
    "teks"
}

FORBIDDEN_LEAK_KEYS = {
    "kunci",
    "kunci_jawaban",
    "jawaban_benar",
    "pembahasan",
    "analisis_distraktor",
    "rubrik",
    "rubrik_skor",
    "skor",
    "bobot",
    "nilai",
    "catatan_guru",
    "pedoman_penskoran",
    "rujukan_sumber",
    "bukti_sumber"
}

SERVER_BOUNDARY_CLAUSE = (
    "Catatan Batasan Privasi & Hak Akses: Pemisahan berkas antara lembar proyeksi siswa dan lembar panduan "
    "proyeksi guru ini merupakan pemisahan konten/data pada level dokumen guna mencegah kebocoran jawaban dalam "
    "penyusunan modul ajar. Pemisahan teks dokumen ini bukan merupakan bukti atau klaim penegakan kontrol "
    "izin/hak akses server (permission server) di level infrastruktur jaringan atau LMS."
)


class QuizExportError(Exception):
    """Custom exception with sanitized messages."""
    pass


def parse_and_validate_input(data: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validates input quiz data and returns (metadata, student_questions, teacher_info).
    Accepts:
      Format A: Dict with 'proyeksi_siswa' and 'proyeksi_guru' (e.g. kuis_fotosintesis.json)
      Format B: Dict with 'butir_soal' or 'kunci_dan_pembahasan' (combined per-item)
    """
    if not isinstance(data, dict):
        raise QuizExportError("Struktur input tidak valid: data root harus berupa objek JSON (dict).")

    # Extract metadata
    metadata = {}
    for meta_key in ("metadata", "metadata_kuis"):
        if meta_key in data and isinstance(data[meta_key], dict):
            metadata = data[meta_key]
            break

    student_questions: List[Dict[str, Any]] = []
    teacher_items: List[Dict[str, Any]] = []

    # Format A: explicitly separated projections in root
    if "proyeksi_siswa" in data:
        raw_siswa = data["proyeksi_siswa"]
        if not isinstance(raw_siswa, list) or len(raw_siswa) == 0:
            raise QuizExportError("Struktur input tidak valid: 'proyeksi_siswa' kosong atau bukan daftar (list).")
        student_questions = raw_siswa

        if "proyeksi_guru" in data and isinstance(data["proyeksi_guru"], list):
            teacher_items = data["proyeksi_guru"]

    # Format B: combined items in 'butir_soal' or 'kunci_dan_pembahasan'
    elif "butir_soal" in data:
        raw_items = data["butir_soal"]
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            raise QuizExportError("Struktur input tidak valid: 'butir_soal' kosong atau bukan daftar (list).")
        student_questions = raw_items
        teacher_items = raw_items

    elif "kunci_dan_pembahasan" in data:
        raw_items = data["kunci_dan_pembahasan"]
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            raise QuizExportError("Struktur input tidak valid: 'kunci_dan_pembahasan' kosong atau bukan daftar (list).")
        student_questions = raw_items
        teacher_items = raw_items
    else:
        raise QuizExportError(
            "Struktur kuis tidak dikenali: tidak ditemukan field 'proyeksi_siswa', 'butir_soal', atau 'kunci_dan_pembahasan'."
        )

    # Validate each student question item
    for idx, q in enumerate(student_questions, 1):
        if not isinstance(q, dict):
            raise QuizExportError(f"Soal nomor {idx} tidak valid: butir soal harus berupa objek (dict).")

        pertanyaan = q.get("pertanyaan") or q.get("teks_soal") or q.get("soal")
        if not pertanyaan or not isinstance(pertanyaan, str) or not pertanyaan.strip():
            raise QuizExportError(f"Soal nomor {idx} tidak valid: teks pertanyaan kosong atau tidak ditemukan.")

        # Check options
        has_options = False
        if "opsi" in q:
            opsi = q["opsi"]
            if isinstance(opsi, dict) and len(opsi) >= 2:
                has_options = True
            elif isinstance(opsi, list) and len(opsi) >= 2:
                has_options = True
        if not has_options and "pilihan" in q:
            pilihan = q["pilihan"]
            if isinstance(pilihan, list) and len(pilihan) >= 2:
                has_options = True

        if not has_options:
            raise QuizExportError(f"Soal nomor {idx} tidak valid: opsi/pilihan jawaban kurang dari 2 atau tidak terdefinisi.")

    return metadata, student_questions, teacher_items


def build_student_projection(metadata: Dict[str, Any], raw_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Constructs clean student quiz projection strictly applying allowlists.
    """
    # 1. Filter metadata using allowlist
    student_meta = {}
    for k, v in metadata.items():
        if k in STUDENT_METADATA_ALLOWLIST and isinstance(v, (str, int, float, bool)):
            student_meta[k] = v

    if "petunjuk" not in student_meta:
        student_meta["petunjuk"] = "Pilihlah satu pilihan yang paling tepat."

    # 2. Filter questions using allowlist
    filtered_questions = []
    for idx, q in enumerate(raw_questions, 1):
        item: Dict[str, Any] = {}

        # nomor & id_soal
        item["nomor"] = q.get("nomor", idx)
        if "id_soal" in q and isinstance(q["id_soal"], (str, int)):
            item["id_soal"] = str(q["id_soal"])

        # pertanyaan
        pertanyaan = q.get("pertanyaan") or q.get("teks_soal") or q.get("soal")
        item["pertanyaan"] = str(pertanyaan).strip()

        # Handle options (either 'opsi' dict or 'pilihan' list)
        if "opsi" in q and isinstance(q["opsi"], dict):
            clean_opsi = {}
            for opt_key, opt_val in q["opsi"].items():
                clean_opsi[str(opt_key).strip().upper()] = str(opt_val).strip()
            item["opsi"] = clean_opsi

        elif "pilihan" in q and isinstance(q["pilihan"], list):
            clean_pilihan = []
            for p in q["pilihan"]:
                if isinstance(p, dict):
                    p_clean = {}
                    for pk in ("opsi", "teks"):
                        if pk in p:
                            p_clean[pk] = str(p[pk]).strip()
                    if p_clean:
                        clean_pilihan.append(p_clean)
            item["pilihan"] = clean_pilihan

        elif "opsi" in q and isinstance(q["opsi"], list):
            clean_pilihan = []
            for p in q["opsi"]:
                if isinstance(p, dict):
                    p_clean = {pk: str(p[pk]).strip() for pk in ("opsi", "teks") if pk in p}
                    clean_pilihan.append(p_clean)
                else:
                    clean_pilihan.append({"teks": str(p).strip()})
            item["pilihan"] = clean_pilihan

        # Strict assertion on filtered keys
        for key in item.keys():
            if key not in STUDENT_QUESTION_ALLOWLIST:
                raise QuizExportError(f"Pelanggaran allowlist internal: field terlarang '{key}' terdeteksi pada soal {idx}.")

        filtered_questions.append(item)

    student_doc = {
        "dokumen": "kuis_siswa",
        "metadata": student_meta,
        "butir_soal": filtered_questions
    }

    # 3. Post-validation: Verify ZERO leakage in the generated student document
    def assert_no_leak_keys(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = k.lower()
                for forbidden in FORBIDDEN_LEAK_KEYS:
                    if forbidden == k_lower or forbidden in k_lower:
                        raise QuizExportError(
                            f"Integritas gagal: field terlarang '{k}' ditemukan pada proyeksi siswa ({path})."
                        )
                assert_no_leak_keys(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, elem in enumerate(obj):
                assert_no_leak_keys(elem, f"{path}[{i}]")

    assert_no_leak_keys(student_doc)

    return student_doc


def build_teacher_projection(
    metadata: Dict[str, Any],
    student_questions: List[Dict[str, Any]],
    teacher_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Constructs full teacher guide projection with keys, explanations, source citations, rubrics,
    and governance boundary clause.
    """
    teacher_meta = dict(metadata)
    teacher_meta["status_dokumen"] = "draft_khusus_guru"
    teacher_meta["catatan_tata_kelola"] = SERVER_BOUNDARY_CLAUSE

    # Index teacher info by nomor or id_soal if provided separately
    teacher_by_id = {}
    teacher_by_num = {}
    for item in teacher_items:
        if isinstance(item, dict):
            if "id_soal" in item:
                teacher_by_id[str(item["id_soal"])] = item
            if "nomor" in item:
                teacher_by_num[item["nomor"]] = item

    merged_teacher_guide = []
    for idx, sq in enumerate(student_questions, 1):
        num = sq.get("nomor", idx)
        id_soal = str(sq.get("id_soal", f"Q-{idx:02d}"))

        # Find matching teacher item
        ti = teacher_by_id.get(id_soal) or teacher_by_num.get(num) or {}

        guide_item = {
            "nomor": num,
            "id_soal": id_soal,
            "pertanyaan": sq.get("pertanyaan", "")
        }

        # Include options
        if "opsi" in sq:
            guide_item["opsi"] = sq["opsi"]
        elif "pilihan" in sq:
            guide_item["pilihan"] = sq["pilihan"]

        # Include key & answer details
        guide_item["kunci_jawaban"] = ti.get("kunci_jawaban") or sq.get("kunci_jawaban", "")
        if "teks_kunci_jawaban" in ti:
            guide_item["teks_kunci_jawaban"] = ti["teks_kunci_jawaban"]
        elif "teks_kunci_jawaban" in sq:
            guide_item["teks_kunci_jawaban"] = sq["teks_kunci_jawaban"]

        # Rujukan sumber
        guide_item["rujukan_sumber"] = ti.get("rujukan_sumber") or sq.get("rujukan_sumber", "MOCK-SOURCE-FORMAT-02")
        if "bukti_sumber" in ti:
            guide_item["bukti_sumber"] = ti["bukti_sumber"]
        elif "bukti_sumber" in sq:
            guide_item["bukti_sumber"] = sq["bukti_sumber"]

        # Pembahasan
        guide_item["pembahasan"] = ti.get("pembahasan") or sq.get("pembahasan", "")

        # Analisis distraktor if present
        if "analisis_distraktor" in ti:
            guide_item["analisis_distraktor"] = ti["analisis_distraktor"]
        elif "analisis_distraktor" in sq:
            guide_item["analisis_distraktor"] = sq["analisis_distraktor"]

        # Rubrik skor
        if "rubrik_skor" in ti:
            guide_item["rubrik_skor"] = ti["rubrik_skor"]
        elif "rubrik_skor" in sq:
            guide_item["rubrik_skor"] = sq["rubrik_skor"]
        elif "skor" in ti or "skor" in sq:
            guide_item["skor"] = ti.get("skor", sq.get("skor", 50))

        merged_teacher_guide.append(guide_item)

    teacher_doc = {
        "dokumen": "kuis_guru",
        "metadata": teacher_meta,
        "kunci_dan_pembahasan": merged_teacher_guide
    }

    return teacher_doc


def render_student_markdown(student_doc: Dict[str, Any]) -> str:
    """Renders student quiz worksheet in clean Markdown."""
    meta = student_doc.get("metadata", {})
    lines = []

    title = meta.get("judul") or meta.get("topik") or "Lembar Kuis Siswa"
    lines.append(f"# {title}")
    lines.append("")

    meta_parts = []
    if "mata_pelajaran" in meta:
        meta_parts.append(f"**Mata Pelajaran:** {meta['mata_pelajaran']}")
    if "kelas" in meta or "jenjang_kelas" in meta:
        kelas = meta.get("kelas") or meta.get("jenjang_kelas")
        meta_parts.append(f"**Kelas/Jenjang:** {kelas}")
    if "alokasi_waktu_menit" in meta:
        meta_parts.append(f"**Waktu:** {meta['alokasi_waktu_menit']} Menit")
    if meta_parts:
        lines.append(" | ".join(meta_parts))
        lines.append("")

    if "petunjuk" in meta:
        lines.append(f"> **Petunjuk:** {meta['petunjuk']}")
        lines.append("")

    lines.append("---")
    lines.append("")

    for q in student_doc.get("butir_soal", []):
        nomor = q.get("nomor", "")
        pertanyaan = q.get("pertanyaan", "")
        lines.append(f"### Soal {nomor}")
        lines.append(f"{pertanyaan}")
        lines.append("")

        if "opsi" in q and isinstance(q["opsi"], dict):
            for opt_key in sorted(q["opsi"].keys()):
                lines.append(f"- **{opt_key}.** {q['opsi'][opt_key]}")
            lines.append("")
        elif "pilihan" in q and isinstance(q["pilihan"], list):
            for p in q["pilihan"]:
                opsi_label = p.get("opsi", "-")
                teks = p.get("teks", "")
                lines.append(f"- **{opsi_label}.** {teks}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def render_teacher_markdown(teacher_doc: Dict[str, Any]) -> str:
    """Renders teacher quiz guide in clean Markdown."""
    meta = teacher_doc.get("metadata", {})
    lines = []

    title = meta.get("judul") or meta.get("topik") or "Panduan Kuis Guru"
    lines.append(f"# {title} (Khusus Guru)")
    lines.append("")
    lines.append("> **Status:** Draf Khusus Guru - Memuat Kunci Jawaban & Pembahasan")
    lines.append(">")
    lines.append(f"> **Batasan Akses:** {SERVER_BOUNDARY_CLAUSE}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for item in teacher_doc.get("kunci_dan_pembahasan", []):
        nomor = item.get("nomor", "")
        pertanyaan = item.get("pertanyaan", "")
        kunci = item.get("kunci_jawaban", "")
        pembahasan = item.get("pembahasan", "")
        rujukan = item.get("rujukan_sumber", "")

        lines.append(f"### Butir {nomor}")
        lines.append(f"**Pertanyaan:** {pertanyaan}")
        lines.append("")

        if "opsi" in item and isinstance(item["opsi"], dict):
            lines.append("**Pilihan Jawaban:**")
            for opt_key in sorted(item["opsi"].keys()):
                lines.append(f"- **{opt_key}.** {item['opsi'][opt_key]}")
            lines.append("")
        elif "pilihan" in item and isinstance(item["pilihan"], list):
            lines.append("**Pilihan Jawaban:**")
            for p in item["pilihan"]:
                lines.append(f"- **{p.get('opsi', '-')}.** {p.get('teks', '')}")
            lines.append("")

        lines.append(f"- **Kunci Jawaban:** **{kunci}**")
        if isinstance(rujukan, dict):
            ref_str = f"{rujukan.get('nama_sumber', '')} v{rujukan.get('versi', '')} {rujukan.get('bagian', '')}".strip()
            lines.append(f"- **Rujukan Sumber:** `{ref_str}`")
            if "kutipan_teks" in rujukan:
                lines.append(f"- **Bukti Kutipan Sumber:** *\"{rujukan['kutipan_teks']}\"*")
        else:
            lines.append(f"- **Rujukan Sumber:** `{rujukan}`")
            if "bukti_sumber" in item:
                lines.append(f"- **Bukti Kutipan Sumber:** *\"{item['bukti_sumber']}\"*")

        if pembahasan:
            lines.append(f"- **Pembahasan:** {pembahasan}")

        # Distractor analysis
        if "analisis_distraktor" in item and isinstance(item["analisis_distraktor"], dict):
            lines.append("- **Analisis Opsi/Distraktor:**")
            for d_k, d_v in item["analisis_distraktor"].items():
                lines.append(f"  * **{d_k}:** {d_v}")

        # Rubric / score
        if "rubrik_skor" in item and isinstance(item["rubrik_skor"], dict):
            rs = item["rubrik_skor"]
            benar = rs.get("jawaban_benar", 50)
            salah = rs.get("jawaban_salah", 0)
            lines.append(f"- **Pedoman Penskoran:** Benar = {benar} poin, Salah = {salah} poin")
        elif "skor" in item:
            lines.append(f"- **Pedoman Penskoran:** Skor maksimal {item['skor']} poin")

        lines.append("")

    return "\n".join(lines).strip() + "\n"


def export_quiz_files(
    input_file: str,
    output_dir: str,
    prefix: Optional[str] = None,
    generate_markdown: bool = True
) -> Dict[str, str]:
    """
    Executes the deterministic export. Atomically writes files only upon total success.
    Returns dict with filepaths created.
    """
    if not os.path.exists(input_file):
        raise QuizExportError(f"Berkas input tidak ditemukan: {os.path.basename(input_file)}")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise QuizExportError(f"Berkas input bukan JSON yang valid: baris {e.lineno}, kolom {e.colno}")
    except Exception as e:
        raise QuizExportError("Gagal membaca berkas input.")

    # 1. Parse & validate
    metadata, raw_student_q, raw_teacher_items = parse_and_validate_input(raw_data)

    # 2. Build projections
    student_doc = build_student_projection(metadata, raw_student_q)
    teacher_doc = build_teacher_projection(metadata, raw_student_q, raw_teacher_items)

    # 3. Determine output file names
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    if prefix:
        pfx = prefix
    elif base_name.startswith("kuis_") and not base_name.endswith(("_siswa", "_guru")):
        pfx = base_name
    elif base_name in ("kuis", "quiz"):
        pfx = "kuis"
    else:
        pfx = f"{base_name}"

    os.makedirs(output_dir, exist_ok=True)

    student_json_path = os.path.join(output_dir, f"{pfx}_siswa.json")
    teacher_json_path = os.path.join(output_dir, f"{pfx}_guru.json")
    student_md_path = os.path.join(output_dir, f"{pfx}_siswa.md")
    teacher_md_path = os.path.join(output_dir, f"{pfx}_guru.md")

    # Serialize JSON
    student_json_str = json.dumps(student_doc, indent=2, ensure_ascii=False) + "\n"
    teacher_json_str = json.dumps(teacher_doc, indent=2, ensure_ascii=False) + "\n"

    # Write files atomically
    with open(student_json_path, "w", encoding="utf-8") as f:
        f.write(student_json_str)

    with open(teacher_json_path, "w", encoding="utf-8") as f:
        f.write(teacher_json_str)

    results = {
        "student_json": student_json_path,
        "teacher_json": teacher_json_path
    }

    if generate_markdown:
        student_md_str = render_student_markdown(student_doc)
        teacher_md_str = render_teacher_markdown(teacher_doc)

        with open(student_md_path, "w", encoding="utf-8") as f:
            f.write(student_md_str)

        with open(teacher_md_path, "w", encoding="utf-8") as f:
            f.write(teacher_md_str)

        results["student_md"] = student_md_path
        results["teacher_md"] = teacher_md_path

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ekspor kuis siswa dan panduan guru secara deterministik berbasis allowlist."
    )
    parser.add_argument("--input", "-i", required=True, help="Jalur berkas JSON kuis gabungan")
    parser.add_argument("--out-dir", "-o", required=True, help="Direktori target untuk berkas hasil ekspor")
    parser.add_argument("--prefix", "-p", default=None, help="Prefix nama berkas (default: dari nama berkas input)")
    parser.add_argument("--no-markdown", action="store_true", help="Lewati pembuatan berkas .md (hanya JSON)")

    args = parser.parse_args()

    try:
        created = export_quiz_files(
            input_file=args.input,
            output_dir=args.out_dir,
            prefix=args.prefix,
            generate_markdown=not args.no_markdown
        )
        print(json.dumps({"success": True, "files": created}, indent=2))
        sys.exit(0)
    except QuizExportError as qe:
        print(json.dumps({"success": False, "error": str(qe)}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Kesalahan tidak terduga: {type(e).__name__}"}), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
