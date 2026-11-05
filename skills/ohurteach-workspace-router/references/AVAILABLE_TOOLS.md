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

## Tidak tersedia / belum terbukti

- Auto-trigger skill tanpa instruksi eksplisit pada paket ini: **belum dibuktikan**.
- Engine PPTX editable: **pending** (exit 69 pada percobaan sebelumnya).
- Import ZIP, LMS/Classroom, video upload, model switching otomatis: **tidak ada**.
