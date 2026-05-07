# FASIH-SM Approval Automator

> Aplikasi desktop otomatisasi approval data survei di platform **FASIH-SM BPS**.
Dibuat oleh **M Naufal Faishal** — BPS Kabupaten Lampung Tengah

---

## Fitur Utama

- **Deteksi CSRF Token** — mengekstrak token otomatis setelah login berhasil
- **Pencarian survei fleksibel** — mencari berdasarkan nama survei, mendukung hasil tunggal maupun jamak
- **Filter status data** — pilih status yang ingin di-approve: `SUBMITTED BY Pencacah`, `APPROVED BY PML`, `APPROVED BY Pengawas`, atau `EDITED BY Admin Kabupaten`
- **Urutan tarik data** — pilih Ascending (terlama) atau Descending (terbaru)
- **Batch approval** — memproses approval sejumlah data sekaligus sesuai input
- **Progress real-time** — progress bar, counter, dan chip status (Berhasil / Gagal / Running)
- **Log berwarna** — output log dibedakan warna: ✓ hijau (ok), ✗ merah (error), ⚠ kuning (warn), biru (info)

---

## Prasyarat

- Python 3.8+
- Google Chrome terinstal di sistem

### Install dependencies

```bash
pip install PyQt6 playwright
playwright install chromium
```

---

## Cara Penggunaan

1. **Jalankan aplikasi** — jendela akan muncul
2. **Isi Nama Survei** — masukkan nama survei persis seperti di FASIH-SM (huruf kapital dan spasi diperhatikan)
3. **Isi Jumlah Data** — jumlah record yang ingin di-approve (angka)
4. **Pilih Status Data** — pilih status approval yang menjadi target
5. **Pilih Urutan Tarik Data** — Ascending (terlama lebih dulu) atau Descending (terbaru lebih dulu)
6. **Klik ▶ Mulai Login & Automasi** — browser Chrome akan terbuka
7. **Login manual** — lakukan login SSO dan masukkan OTP di browser yang terbuka
8. **Tunggu proses selesai** — aplikasi akan otomatis memproses approval dan menampilkan progress secara real-time

> ⚠️ **Perhatian:** Jangan tutup browser Chrome yang dibuka oleh aplikasi selama proses berjalan.

---

## Struktur Kode

```
FasihApprovalAutomator.py
│
├── Komponen UI
│   ├── AuroraBackground   — animasi latar aurora
│   ├── GlassPanel         — panel frosted glass
│   ├── GlassButton        — tombol dengan efek glass
│   ├── GlassProgressBar   — progress bar bergradasi
│   ├── GlassLineEdit      — input field transparan
│   ├── GlassComboBox      — dropdown bergaya glass
│   ├── Chip               — status chip berwarna
│   └── TitleBar           — title bar custom + window controls
│
├── FasihApp (QMainWindow)
│   ├── _build_ui()        — membangun layout antarmuka
│   ├── _on_run()          — handler tombol mulai
│   └── _automate()        — worker thread otomatisasi (Playwright)
│
└── Entry Point
    └── __main__
```

---

## Alur Otomatisasi (Backend)

```
Buka browser → Navigasi ke fasih-sm.bps.go.id/login
    ↓
Tunggu login SSO + OTP (manual)
    ↓
Deteksi redirect ke halaman survey → Ekstrak CSRF Token
    ↓
POST /surveys/datatable → Cari Survey ID berdasarkan nama
    ↓
GET /survey-periods/my → Ambil Period ID aktif
    ↓
POST /assignment/datatable-all-user-survey-periode → Tarik antrean data
    ↓
Loop: POST /approval per record → Log hasil per item
    ↓
Tampilkan ringkasan: Berhasil / Gagal → Tutup browser
```

---

## Konfigurasi & Konstan

| Parameter | Nilai Default | Keterangan |
|---|---|---|
| Target URL | `https://fasih-sm.bps.go.id` | Base URL FASIH-SM BPS |
| Browser | Chrome (non-headless) | Diperlukan untuk login SSO manual |
| Timeout login | Tidak terbatas | Menunggu redirect setelah login |
| Delay setelah login | 5 detik | Memberi waktu halaman dimuat |
| Delay setelah cari survei | 3 detik | Anti-rate-limit ringan |

---

## Catatan

- Aplikasi ini hanya berjalan optimal di **Windows**
- Proses login SSO tetap dilakukan **secara manual** oleh pengguna — aplikasi tidak menyimpan kredensial
- Pastikan akun yang digunakan memiliki **hak approval** untuk survei yang ditargetkan
- Seluruh data yang akan di-approve memang sudah diperiksa dan tinggal dilakukan approval
- Mohon digunakan dengan tanggung jawab masing-masing

---

## Lisensi & Kredit

© M Naufal Faishal — BPS Kabupaten Lampung Tengah  
Dikembangkan untuk keperluan internal BPS.
