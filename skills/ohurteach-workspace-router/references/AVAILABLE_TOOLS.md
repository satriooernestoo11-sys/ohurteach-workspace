# Available Tools — Snapshot Teramati

Kemampulan runtime yang **benar-benar teramati** di sesi WorkBuddy (builder dan sesi expert). Snapshot per 5 November 2026; bukan pemberian izin; tanpa endpoint/secret.

| Kemampuan | Status verifikasi | Catatan fallback jujur |
|---|---|---|
| Agent native custom (`ohurteach-workspace-researcher/planner/writer/reviewer`) | TERAMATI berjalan pada sesi yang dibuka via My Experts → Summon (run-20261104-164418 dkk.) | Di sesi builder biasa, dispatch custom gagal `Task agent ... is not available`; jangan pakai sesi builder untuk uji anggota |
| `Read/Write/Edit/Glob/Grep/Bash` | TERAMATI | Untuk berkas privat gunakan folder `ohurteach-private/` |
| `SendMessage` (kolaborasi tim) | TERAMATI pada sesi Summon | — |
| CLI `workbuddy-pdf` (`~/.workbuddy-ai/external-packages/pdf-cli/workbuddy-pdf.exe`) | TERAMATI: `-f txt/md-plain/structure/docx/png` | Baca PDF tanpa mengubah sumber |
| Konverter DOCX lingkungan (`convert_doc.py` via editor SDK) | TERAMATI (run-20261104-143749: preflight & verify pass) | Jika tool tidak ada, serahkan Markdown dan katakan DOCX pending |
| `skills/ohurteach-quiz-export/scripts/export_quiz.py` | TERAMATI (stdlib Python murni) | Jangan dipakai untuk tugas speaking/non-pilihan-ganda |
| Skill user-level (hallmark, antislop-*) | TERSEDIA dalam daftar skill sesi WorkBuddy (user-level) | BELUM_TERUJI dipanggil dari agent OhUrTeach; pengujian UI tetap di lane development |
| Validator/registrasi expert (`validate_expert.py`, `register_expert.py`) | TERAMATI | Jalankan pada direktori paket yang lengkap |
| Konektor Sekali Pasang LMS OhUrTeach (`scripts/ohurteach_connector.py`: `inspect-identity`, `search-sources`, `save-private-draft`) | TERAMATI & TERVERIFIKASI (pairing PKCE sekali pakai dari sesi aktif tanpa edit JSON) | Kredensial disimpan terenkripsi di vault lokal akun WorkBuddy (`~/.workbuddy-ai/connectors/<account-uuid>/.credentials.ohurteach.v3.json` dengan DPAPI + `.master.key` akun) di luar chat, prompt, dan memory agent. Bertahan pada akun WorkBuddy yang sama di perangkat ini setelah aplikasi dibuka ulang (lokal per perangkat, bukan sinkronisasi cloud lintas perangkat). Kartu Connect bawaan (`suggest_plugin_install`) hanya memuat daftar konektor resmi Tencent Cloud/WorkBuddy dan tidak mendukung domain eksternal kustom |

## Tidak tersedia / belum terbukti

- Kartu `suggest_plugin_install` untuk layanan pihak ketiga kustom (`out.satz11.my.id`): **tidak tersedia di registry resmi WorkBuddy** (`search_plugins(type="connector")` hanya mengembalikan 25 konektor bawaan Tencent); oleh karena itu digunakan **pairing kode sekali pakai dari sesi aktif** (`ohurteach_connector.py`) tanpa edit JSON.
- Sinkronisasi kredensial konektor lintas perangkat (cross-device): **tidak diklaim** karena penyimpanan vault konektor WorkBuddy (`~/.workbuddy-ai/connectors/<account-uuid>/`) bersifat lokal pada perangkat untuk akun yang sama.
- Auto-trigger skill tanpa instruksi eksplisit pada paket ini: **belum dibuktikan**.
- Engine PPTX editable: **pending** (exit 69 pada percobaan sebelumnya).
- Import ZIP, video upload, model switching otomatis: **tidak ada**.
