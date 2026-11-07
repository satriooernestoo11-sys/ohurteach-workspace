# Katalog Skill — OhUrTeach Workspace

Snapshot katalog untuk router. Status: **TERSEDIA** (file ada dan mekanisme didukung), **BELUM_TERUJI** (ada tetapi belum dibuktikan pada jalur ini), **TIDAK_TERSEDAIA** (tidak ada; jangan dijanjikan). Daftar ini snapshot lokal, bukan pemberian izin, dan bukan field standard yang pasti diinterpretasi host.

| Skill | Kapan dipakai | Path/ID aktual | Status | Kebutuhan tool |
|---|---|---|---|---|
| `ohurteach-workspace-router` | Setiap permintaan masuk, untuk memilih rute | `skills/ohurteach-workspace-router/SKILL.md` (paket) | TERSEDIA | — |
| `ohurteach-rulepack` (RP-OHURTEACH v1.0.3, 15 aturan) | Reviewer menilai setiap draft; Head mengutip batasan aturan | `skills/ohurteach-rulepack/SKILL.md` (paket) | TERSEDIA; teruji pada siklus review run terdahulu | — |
| `ohurteach-quiz-export` | Head memisahkan kuis gabungan menjadi berkas siswa/guru (Phase 6 Workflow A/B) | `skills/ohurteach-quiz-export/SKILL.md` + `scripts/export_quiz.py` (paket) | TERSEDIA; teruji (WB-QUIZ-EXPORT-01/FIX) | `python3` stdlib saja, tanpa dependensi eksternal |
| Lane delivery Head & ekspor PDF (Phase 6) | Serah-terima hasil run yang sudah direview menjadi 3 PDF terpisah (RPP, lembar siswa, panduan guru) di chat guru tanpa regenerasi | `agents/ohurteach-workspace-team-lead.md` (Kontrak serah-terima Phase 6) | TERSEDIA; teruji ekspor lokal via Edge headless pada `run-20261106-213422` | Renderer headless lokal (`msedge.exe --headless --print-to-pdf`); fallback ke Markdown (`PDF_PENDING`) bila gagal |
| `hallmark` (v2.0.0, MIT) | Pekerjaan desain UI baru di lane development | `C:/Users/Lenovo/.codebuddy/skills/hallmark/` (user-level; tampil dalam daftar skill sesi WorkBuddy) | TERSEDIA di sesi WorkBuddy; BELUM_TERUJI dijalankan dari agent OhUrTeach | lane development, bukan jalur guru |
| `antislop`, `antislop-ui`, `antislop-human`, `antislop-layoutmobile`, `antislop-copywriting` | Pemeriksaan UI pada pekerjaan development terkait (kontras, keyboard/fokus, mobile, copy) | `C:/Users/Lenovo/.codebuddy/skills/<nama>/` (user-level; tampil dalam daftar skill sesi WorkBuddy) | TERSEDIA di sesi WorkBuddy; BELUM_TERUJI dijalankan dari agent OhUrTeach | lane development; muat hanya subskill yang relevan |

## Tidak tersedia (jangan dijanjikan)

- Import otomatis paket dari `.zip` (tidak ada importer; instalasi via direktori + `register_expert.py`).
- Engine presentasi PPTX editable (pending di lingkungan ini).
- Konektor LMS/Classroom, pengumpulan tugas, atau pengiriman ke siswa.
- Model/provider switching otomatis; DNS/firewall/auth changes.
- OS skill lengkap, pruning otomatis, pencarian skill internet per permintaan (ditunda pasca-demo).

## Catatan

- Skill paket dibaca dari paket; skill user-level dibaca dari jalur user. Keberadaan file tidak membuktikan auto-trigger; bukti perilaku nyata memerlukan sesi Summon baru.
- Lisensi/atribusi: Hallmark MIT (file LICENSE menyertai). Antislop: periksa atribusi pada folder skill sebelum redistribusi; penggunaan internal untuk pemeriksaan tidak mengubah atribusi.
