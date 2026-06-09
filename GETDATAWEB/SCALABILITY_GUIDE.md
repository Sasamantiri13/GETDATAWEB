# Analisis Skalabilitas - 1000 Assets

## 📊 Estimasi Waktu

### Berdasarkan Test Saat Ini (3 Assets)
- **Total waktu**: ~3 menit untuk 3 assets
- **Rata-rata per asset**: ~60 detik
- **Breakdown**:
  - Startup Chrome: ~30 detik
  - Login: ~5 detik
  - Per asset (scroll + extract): ~30-40 detik

### Estimasi untuk 1000 Assets

**Single Script (Sequential):**
```
1000 assets × 40 detik = 40,000 detik
= 666 menit
= ~11 jam
```

**Dengan Parallel (Recommended):**
```
1000 assets ÷ 5 scripts × 40 detik = 8,000 detik
= 133 menit
= ~2.2 jam
```

---

## 🚀 Rekomendasi: Parallel Execution

### Jumlah Script Optimal

**Faktor yang Perlu Dipertimbangkan:**

1. **Spek Komputer Anda:**
   - RAM: Minimal 8GB (setiap Chrome instance ~500MB-1GB)
   - CPU: 4+ cores recommended
   - **Rekomendasi**: 3-5 script parallel

2. **Server Load:**
   - Jangan overload server
   - **Rekomendasi**: Maksimal 5 concurrent connections
   - Tambahkan delay antar request

3. **Network:**
   - Bandwidth cukup untuk 5 concurrent Chrome
   - **Rekomendasi**: 5-10 Mbps minimum

### Konfigurasi Optimal

| Jumlah Script | RAM Needed | Estimasi Waktu | Server Load |
|---------------|------------|-----------------|-------------|
| 1 script | 2 GB | ~11 jam | Low ✅ |
| 3 scripts | 4 GB | ~4 jam | Medium ✅ |
| **5 scripts** | **6 GB** | **~2.2 jam** | **Medium ✅** |
| 10 scripts | 12 GB | ~1.1 jam | High ⚠️ |

**Rekomendasi: 5 scripts parallel**

---

## 📝 Cara Setup Parallel Execution

### 1. Split ID Assets

Bagi `id_aset.txt` menjadi 5 file:

```bash
# Script akan otomatis split
python split_assets.py
```

Hasil:
- `id_aset_1.txt` (200 IDs)
- `id_aset_2.txt` (200 IDs)
- `id_aset_3.txt` (200 IDs)
- `id_aset_4.txt` (200 IDs)
- `id_aset_5.txt` (200 IDs)

### 2. Modifikasi Script

Edit `tarik_data.py` untuk accept parameter:

```python
# Tambahkan di awal main()
import sys
asset_file = sys.argv[1] if len(sys.argv) > 1 else "id_aset.txt"
```

### 3. Run Parallel

Buka 5 terminal/PowerShell dan jalankan:

```powershell
# Terminal 1
python tarik_data.py id_aset_1.txt

# Terminal 2
python tarik_data.py id_aset_2.txt

# Terminal 3
python tarik_data.py id_aset_3.txt

# Terminal 4
python tarik_data.py id_aset_4.txt

# Terminal 5
python tarik_data.py id_aset_5.txt
```

### 4. Merge Results

Setelah selesai, gabungkan Excel files:

```python
python merge_excel.py
```

---

## ⚠️ Mencegah Server Overload

### 1. Rate Limiting

Tambahkan delay antar request:

```python
# Di dalam loop asset
time.sleep(random.uniform(2, 5))  # Random 2-5 detik
```

### 2. Retry Strategy

Jika server error (429, 503):

```python
if "error" in response:
    time.sleep(60)  # Wait 1 menit
    retry()
```

### 3. Monitoring

Pantau:
- CPU usage (jangan > 80%)
- RAM usage (jangan > 90%)
- Network bandwidth

---

## 🎯 Rekomendasi Final

### Untuk 1000 Assets:

**Setup:**
- ✅ 5 scripts parallel
- ✅ Split 200 assets per script
- ✅ Add 3-5 detik delay per asset
- ✅ Monitor resource usage

**Estimasi:**
- ⏱️ Waktu: ~2.5-3 jam
- 💾 RAM: ~6 GB
- 🌐 Server load: Medium (acceptable)

**Alternatif Jika Komputer Lemah:**
- 3 scripts parallel
- ~4 jam total
- ~4 GB RAM

---

## 📋 Checklist Sebelum Run

- [ ] Split id_aset.txt menjadi 5 file
- [ ] Modifikasi script untuk accept parameter
- [ ] Test dengan 1 script dulu (10-20 assets)
- [ ] Monitor CPU/RAM usage
- [ ] Pastikan server tidak error
- [ ] Setup auto-merge results
- [ ] Backup data existing

---

## 🔧 Tools yang Perlu Dibuat

1. **split_assets.py** - Split ID file
2. **merge_excel.py** - Merge hasil Excel
3. **monitor.py** - Monitor progress semua script
4. **Modified tarik_data.py** - Accept file parameter

Apakah Anda ingin saya buatkan script-script ini?
