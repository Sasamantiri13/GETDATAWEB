# Cara Extract Cookies dari Browser

## Langkah 1: Login ke Aplikasi
1. Buka Microsoft Edge dan login ke `https://dc-bmc-master.bfi.co.id:1611/webconsole/home`
2. Pastikan login berhasil dan Anda bisa melihat halaman home

## Langkah 2: Buka Developer Tools
1. Tekan `F12` atau `Ctrl+Shift+I` di Microsoft Edge.
2. Klik tab **Application** (atau **Storage** di Firefox)
3. Di sidebar kiri, expand **Cookies**
4. Klik domain `https://dc-bmc-master.bfi.co.id:1611`

## Langkah 3: Copy Cookie Values
Anda akan melihat daftar cookies. Yang penting biasanya:
- **JSESSIONID** - Session ID utama
- Cookies lain yang terkait dengan authentication

Untuk setiap cookie penting:
1. Klik pada cookie tersebut
2. Copy **Name** dan **Value**
3. Catat juga **Domain**, **Path**, dan **Secure** (true/false)

## Langkah 4: Buat File cookies.json

Buat file `cookies.json` di folder yang sama dengan script:

```json
[
  {
    "name": "JSESSIONID",
    "value": "PASTE_VALUE_DISINI",
    "domain": "dc-bmc-master.bfi.co.id",
    "path": "/",
    "secure": true
  }
]
```

**Contoh lengkap:**
```json
[
  {
    "name": "JSESSIONID",
    "value": "A1B2C3D4E5F6G7H8I9J0",
    "domain": "dc-bmc-master.bfi.co.id",
    "path": "/",
    "secure": true
  },
  {
    "name": "remember-me",
    "value": "somevalue123",
    "domain": "dc-bmc-master.bfi.co.id",
    "path": "/",
    "secure": true
  }
]
```

## Tips
- Cookie biasanya expire setelah beberapa waktu (tergantung server)
- Jika script gagal login, extract cookies lagi dari browser
- Jangan share file `cookies.json` karena berisi session Anda
- Tambahkan `cookies.json` ke `.gitignore` jika menggunakan git

## Troubleshooting

**Script masih gagal login?**
- Pastikan semua cookies penting sudah di-copy
- Cek apakah ada cookies tambahan selain JSESSIONID
- Pastikan format JSON benar (gunakan validator online)
- Cookie mungkin sudah expired, extract ulang dari browser
