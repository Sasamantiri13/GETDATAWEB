# 📖 Panduan Penggunaan - Sistem Parallel Extraction

## 🎯 Untuk 1000 Assets (~2.5 Jam)

### Langkah 1: Persiapan Awal (Hanya Sekali)

1.  **Pastikan sudah login di Microsoft Edge**
    -   Buka Microsoft Edge normal
    -   Login ke `https://dc-bmc-master.bfi.co.id:1611/webconsole/home`
    -   Pastikan login berhasil

2.  **Setup Profile Shared**
    -   Jalankan script `python setup_shared_profile.py`
    -   Script ini akan menyalin profile Edge Anda (termasuk session login) ke folder project agar bisa digunakan secara paralel.

3.  **Siapkan file ID**
    -   Pastikan file `id_aset.txt` berisi 1000 ID (satu ID per baris)

### Cara Menjalankan
1.  **Single Script (Testing)**
    ```powershell
    python tarik_data.py --input id_aset.txt --id 1
    ```
    *Browser Edge akan terbuka menggunakan profile yang sudah di-setup.*

---

### Langkah 2: Jalankan Parallel Extraction

**Cara Termudah:**
```bash
# Klik 2x file ini di Windows Explorer
run_parallel.bat
```

**Atau via Command Line:**
```bash
.\run_parallel.bat
```

**Yang Terjadi:**
- ✅ Otomatis split `id_aset.txt` menjadi 5 file
- ✅ Buka 5 jendela Chrome (masing-masing 200 assets)
- ✅ Setiap jendela akan login otomatis (pakai profile shared)

**Jika Ada Jendela yang Minta Login:**
- Login manual di jendela pertama yang muncul
- Jendela lainnya biasanya otomatis ikut login

---

### Langkah 3: Pantau Progress (Opsional)

Buka terminal baru:
```bash
python monitor.py
```

Akan muncul:
```
TOTAL PROGRESS: 450 / 1000 (45.0%)
------------------------------
result_p1_20260209_175500.csv: 120 rows
result_p2_20260209_175502.csv: 95 rows
result_p3_20260209_175504.csv: 110 rows
result_p4_20260209_175506.csv: 75 rows
result_p5_20260209_175508.csv: 50 rows
```

---

### Langkah 4: Gabungkan Hasil

Setelah semua jendela selesai (tertutup):
```bash
python merge_csv.py
```

✅ Hasilnya: `FINAL_DATA_1000_YYYYMMDD_HHMMSS.csv`

---

## 🔧 Untuk 3 Assets Saja (Testing/Normal)

Jika hanya ingin ambil beberapa data (seperti biasa):

```bash
# Pastikan id_aset.txt berisi 3 ID
python tarik_data.py
```

**Catatan:** Script otomatis detect:
- Jika dipanggil tanpa parameter → mode normal (baca `id_aset.txt`)
- Jika dipanggil dengan parameter → mode parallel

---

## ⚙️ Troubleshooting

### "Profile not found"
```bash
# Jalankan ulang setup
python setup_shared_profile.py
```

### "Session expired" di semua jendela
- Login manual di jendela pertama
- Jendela lain akan ikut login

### Script berhenti/error
- Cek jendela Chrome yang error
- Lihat pesan error di terminal
- Restart jendela yang error saja:
  ```bash
  python tarik_data.py id_aset_3.txt 3
  ```

### Hasil tidak lengkap
- Cek file `result_p*.csv` mana yang kurang
- Jalankan ulang script yang kurang saja
- Merge ulang dengan `python merge_csv.py`

---

## 📊 File Output

| File | Deskripsi |
|------|-----------|
| `result_p1_*.csv` | Hasil script 1 (Assets 1-200) |
| `result_p2_*.csv` | Hasil script 2 (Assets 201-400) |
| `result_p3_*.csv` | Hasil script 3 (Assets 401-600) |
| `result_p4_*.csv` | Hasil script 4 (Assets 601-800) |
| `result_p5_*.csv` | Hasil script 5 (Assets 801-1000) |
| `FINAL_DATA_1000_*.csv` | **Hasil akhir gabungan** ⭐ |

---

## 💡 Tips

1. **Jangan tutup jendela Chrome** yang sedang berjalan
2. **Jangan jalankan Chrome lain** saat script berjalan
3. **Monitor RAM usage** - jika >90%, tutup aplikasi lain
4. **Backup hasil partial** - File `result_p*.csv` adalah backup otomatis

---

## 🚀 Quick Reference

```bash
# Setup (sekali saja)
python setup_shared_profile.py

# Jalankan parallel (1000 assets)
run_parallel.bat

# Monitor progress
python monitor.py

# Gabungkan hasil
python merge_csv.py

# Normal mode (3 assets)
python tarik_data.py
```
