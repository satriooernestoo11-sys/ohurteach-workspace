---
name: ohurteach-workspace-router
description: "Router tipis untuk OhUrTeach Workspace: memilih prosedur/skill yang benar-benar tersedia dari permintaan bahasa alami guru tanpa slash. Head membaca katalog (references/SKILL_CATALOG.md) lalu hanya memuat skill relevan. Gunakan saat menerima permintaan apa pun dari guru sebelum menugaskan anggota."
---

# OhUrTeach Workspace Router

Skill ini adalah **router prosedur**, bukan pembuat konten. Ia memastikan Head memilih jalur kerja yang benar dan hanya membaca skill yang relevan, memakai agent native yang sudah ada. Skill tidak menambah tool, hak akses, provider, atau jatah review; tidak menggantikan rule pack.

## Cara pakai (untuk Head)

1. Terima permintaan guru dalam bahasa apa pun, tanpa perlu slash command.
2. Baca `references/SKILL_CATALOG.md` untuk mencocokkan permintaan dengan rute yang tersedia.
3. Baca **hanya** SKILL.md dari rute terpilih; jangan memuat semua skill sekaligus.
4. Jalankan rute dengan agent native existing (`ohurteach-workspace-*`) dan SOP tim yang berlaku.
5. Jika rute ambigu atau skill tidak tersedia: pilih prosedur existing yang benar-benar tersedia, dan **ungkapkan keterbatasannya** kepada guru. Jangan mengarang tool, agent, output, atau keberhasilan.

## Rute minimum

| Permintaan guru (contoh) | Rute | Skill yang dibaca | Prasyarat |
|---|---|---|---|
| "Buat rencana pembelajaran/kuis/kerangka slide dari sumber saya" | Workflow agent existing (A/B/C sesuai permintaan) via Researcher→Planner→Writer→Reviewer | `ohurteach-rulepack` (dibaca Reviewer saat menilai draft) | Sumber berizin; konteks jenjang/mapel/tujuan diketahui atau ditanyakan |
| "Pisahkan/ekspor kuis ini jadi berkas siswa dan guru" | Ekspor deterministik oleh Head (Phase 6) | `ohurteach-quiz-export` | Draft kuis gabungan sudah lolos review; berkas disimpan di folder privat run |
| "Tampilkan/lanjutkan/ekspor PDF hasil run yang sudah ada" | Lane delivery Head (Phase 6), tanpa regenerasi | `ohurteach-quiz-export` hanya bila berkas hasil belum terpisah | `run_record` + berkas hasil sudah ada dan terverifikasi; konter review dipertahankan |
| "Bikin/desain tampilan (UI) untuk saya" | **Bukan dikerjakan agent guru secara otomatis.** Arahkan ke lane development; sebut skill desain yang tersedia (Hallmark, antislop-ui, antislop-human, antislop-layoutmobile, antislop-copywriting) dan minta keputusan guru untuk membuka pekerjaan development | tidak ada skill guru yang dimuat | Pekerjaan UI = proyek development terpisah |

## Pertanyaan konteks

Tanyakan hanya yang belum diketahui: (1) sumber berizin untuk tugas ini; (2) jenjang/mapel; (3) tujuan dan format keluaran; (4) kebutuhan khusus. Gunakan preferensi guru yang sudah dikonfirmasi dan mudah dikoreksi. Jangan menyimpulkan persona atau kemampuan siswa dari data pribadi.

## Template-preservation

Jika format baku (template sekolah, format dokumen asli guru) belum terbukti dapat dipertahankan pada keluaran, **jangan menjanjikan format identik dan jangan menimpa sumber**. Kerjakan pada salinan, catat pemeriksaan tata letak sebelum/sesudah, dan laporkan perbedaan yang teramati.

## Kontrak komunikasi hasil dan serah-terima PDF (ringkas)

Router mengarahkan Head ke "## Kontrak serah-terima ke guru (Phase 6)" pada prompt Head untuk rincian. Ringkasnya: satu kalimat hasil di awal; update hanya bila ada informasi baru; verdict Reviewer disampaikan di chat guru; pada tahap serah-terima setelah review, jadikan PDF format utama untuk RPP, lembar kuis siswa (Zero Key Leakage), dan panduan guru (privat pemilik draf) menggunakan renderer lokal yang tersedia, sementara Markdown/JSON dipertahankan sebagai sumber kerja; tampilkan 3 berkas aktual di chat guru (present/attach bila tersedia, atau path absolut yang valid); bila renderer lokal belum tersedia, serahkan Markdown sementara dengan status `PDF_PENDING` dan sebutkan kendalanya; final memuat ringkasan 2–3 kalimat, batas, status pending approval, selisih/errata durasi bila ada (tanpa ubah artefak diam-diam), dan satu pertanyaan keputusan. Bila berkas belum valid, nyatakan PARTIAL/WAITING dengan blocker, bukan DONE. Router tidak menduplikasi aturan sumber, izin, privasi, atau approval.

## Aturan yang tetap berlaku (tidak diduplikasi di sini)

- Izin sumber, provenance, aturan berversi, pemisahan keluaran guru/siswa, batas review maksimal 3, dan human approval diatur oleh prompt Head dan `ohurteach-rulepack`. Router tidak mengubah isinya.
- PASS Reviewer berarti lolos pemeriksaan yang dicatat — bukan persetujuan manusia atau izin publikasi.
- Error upstream (tool/model gagal): simpan checkpoint tersanitasi, hentikan. Jangan auto-retry, auto-respawn, atau ganti provider dalam tugas yang sama.
- Jangan membaca konten yang dilarang hanya untuk membuktikan penolakan.

## Kemampuan aktual

Daftar tool dan dukungan yang benar-benar teramati ada di `references/AVAILABLE_TOOLS.md` (snapshot, bukan pemberian izin). Jangan menebak nama API, dukungan model switching, atau fitur LMS yang belum terbukti.
