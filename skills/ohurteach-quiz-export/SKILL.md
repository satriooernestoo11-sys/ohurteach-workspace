---
name: ohurteach-quiz-export
description: "Mekanisme deterministik untuk memisahkan kuis dua proyeksi menjadi berkas siswa (*_siswa.json/*_siswa.md) dan panduan guru (*_guru.json/*_guru.md) terpisah berbasis allowlist ketat."
---

# OhUrTeach Quiz Export Skill

Skill ini menyediakan utilitas CLI deterministik `scripts/export_quiz.py` bagi tim OhUrTeach Workspace untuk memisahkan data kuis gabungan (yang memuat proyeksi siswa dan proyeksi guru) menjadi dua berkas fisik terpisah:

1. **Berkas Siswa (`*_siswa.json` dan `*_siswa.md`)**:
   - Memuat data pertanyaan dan opsi pilihan yang siap dibagikan kepada peserta didik.
   - Menggunakan **Strict Allowlist** (hanya field `nomor`, `id_soal`, `pertanyaan`, `opsi`/`pilihan` pada soal; dan metadata umum seperti `judul`, `mata_pelajaran`, `kelas`, `petunjuk`).
   - Validasi struktur opsi ketat: menolak opsi bersarang (dict/list) guna mencegah kebocoran semantik kunci/catatan guru melalui stringifikasi mentah.
   - Dijamin 100% bebas (*zero-leak*) dari kunci jawaban, pembahasan, skor, rubrik, atau catatan guru.
2. **Berkas Panduan Guru (`*_guru.json` dan `*_guru.md`)**:
   - Memuat soal lengkap beserta kunci jawaban benar, kutipan bukti sumber asli, pembahasan pedagogis, analisis opsi/distraktor, dan pedoman penskoran.
   - Tanpa fabrikasi sumber: tidak mengisi rujukan bawaan fiktif. Jika rujukan tidak ada, ditandai sebagai `sumber belum tersedia`.
   - Transparansi kelengkapan: jika kunci jawaban belum lengkap, ditandai secara eksplisit sebagai `draf_panduan_guru_tidak_lengkap` (`kunci_tersedia: false`) dengan peringatan jelas agar tidak disajikan sebagai panduan final.
   - Memuat klausul batasan tata kelola dokumen vs penegakan izin server (`R-PRIV-01 v1.0.1 [HOLD]`).

## Cara Menggunakan (CLI)
```bash
python skills/ohurteach-quiz-export/scripts/export_quiz.py --input <path/ke/kuis_gabungan.json> --out-dir <path/direktori_tujuan> [--prefix <nama_prefix>] [--overwrite] [--no-markdown]
```

## Jaminan Penulisan Berkas
- **Pencegahan Overwrite Diam-Diam**: Menolak penulisan jika berkas tujuan sudah ada, kecuali flag `--overwrite` diberikan secara eksplisit.
- **Safe Staging & Rollback**: Berkas ditulis ke berkas pementasan sementara (`.tmp`) terlebih dahulu. Jika terjadi kegagalan tulis di tengah jalan, seluruh berkas pementasan dan berkas parsial yang baru dibuat akan dihapus secara otomatis (rollback). Ini adalah mekanisme perlindungan level aplikasi agar tidak meninggalkan artefak parsial/menyesatkan (bukan transaksi multi-file ACID tingkat sistem operasi).

## Ketentuan Tata Kelola Dokumen
Pemisahan berkas ini merupakan pemisahan konten/data pada level dokumen, **bukan bukti atau klaim penegakan kontrol izin/hak akses server (permission server)** di level infrastruktur jaringan atau LMS. Berkas gabungan dan berkas guru tetap berstatus privat dan tidak boleh dibagikan kepada peserta didik.
