import pandas as pd
import time
import os
import io
import urllib3
import subprocess
import shutil
import tempfile
import urllib.request
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- KONFIGURASI ---
BASE_PATH = r"C:\Users\200248\Documents\GETDATAWEB"
CHROME_USER_DATA = r"C:\Users\200248\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME = "Profile 6"
# If True, start Chrome manually with remote debugging and attach to it.
# This is recommended when you want to use an existing profile without ChromeDriver
# creating a new Chrome instance (avoids DevToolsActivePort errors).
ATTACH_MODE = True

# Optional: hardcode credentials here as fallback to environment variables.
# Leave empty string to require manual login or environment vars.
USERNAME = "bfi\200248"
PASSWORD = "Indones1@raya"
# ATTACH_MODE: Jika True, akan coba attach ke Chrome dengan remote debugging
# Jika timeout, akan auto-fallback ke ATTACH_MODE=False (direct ChromeDriver launch)
# Untuk stabilitas, disarankan False (direct launch lebih simple dan reliable)
ATTACH_MODE = True
ATTACH_MODE_TIMEOUT = 5  # Kurangi dari 8 detik menjadi 5 detik untuk lebih cepat fallback

os.chdir(BASE_PATH)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Verifikasi profil ada
profile_path = os.path.join(CHROME_USER_DATA, PROFILE_NAME)
if not os.path.exists(profile_path):
    print(f"[ERROR] Profil '{PROFILE_NAME}' tidak ditemukan di: {profile_path}")
    exit()
else:
    print(f"[OK] Profil '{PROFILE_NAME}' ditemukan di Chrome User Data.")

# SETUP CHROME
chrome_options = Options()
# If not attaching to an already-running Chrome, tell ChromeDriver to use the real user data dir
if not ATTACH_MODE:
    chrome_options.add_argument(f"--user-data-dir={CHROME_USER_DATA}") 
    chrome_options.add_argument(f"--profile-directory={PROFILE_NAME}")
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--allow-running-insecure-content')

# Tambahan agar tidak crash
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

print("Menyiapkan Chrome dengan Local Profile...")

def chrome_is_running():
    try:
        out = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], text=True)
        out2 = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq chromeenterprisecompanion.exe'], text=True)
        return 'chrome.exe' in out.lower() or 'chromeenterprisecompanion.exe' in out2.lower()
    except Exception:
        return False

if chrome_is_running():
    print("[WARNING] Terdeteksi proses Chrome berjalan. Tutup semua jendela Chrome supaya profile dapat digunakan.")
    input("Setelah menutup semua Chrome, tekan [ENTER]...")

# Jika setelah konfirmasi masih ada proses Chrome, hentikan paksa agar profil bisa dipakai
# Dengan retry multiple times dan cleanup files
for attempt in range(1, 4):
    if chrome_is_running():
        print(f"[INFO] Attempt {attempt}: Menghentikan Chrome process...")
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['taskkill', '/F', '/IM', 'chromeenterprisecompanion.exe'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
        except Exception as e:
            print(f"[WARNING] Gagal kill Chrome: {e}")

# Clean up DevToolsActivePort file jika ada (sering menyebabkan error)
try:
    port_file = os.path.join(profile_path, 'DevToolsActivePort')
    if os.path.exists(port_file):
        os.remove(port_file)
        print(f"[INFO] Deleted DevToolsActivePort file")
except Exception as e:
    print(f"[WARNING] Gagal delete DevToolsActivePort: {e}")

# Tunggu lebih lama agar process benar-benar selesai
if chrome_is_running():
    print("[WARNING] Chrome masih berjalan setelah kill. Menunggu 5 detik...")
    time.sleep(5)

print(f"Using Chrome user-data-dir: {CHROME_USER_DATA}")
print(f"Using profile: {PROFILE_NAME}")

# Set explicit Chrome binary if available
possible_bins = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                 os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\User Data\..\Application\chrome.exe")]
CHROME_BINARY = None
for p in possible_bins:
    if p and os.path.exists(p):
        CHROME_BINARY = p
        break
if CHROME_BINARY:
    chrome_options.binary_location = CHROME_BINARY
    print(f"Using Chrome binary: {CHROME_BINARY}")
else:
    print("[WARNING] Tidak menemukan chrome.exe otomatis; akan gunakan default PATH.")

# Add recommended flags to avoid DevToolsActivePort errors
if not ATTACH_MODE:
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-component-update')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
else:
    # In attach mode we must avoid sending experimental options unsupported by the running browser.
    print('[INFO] ATTACH_MODE active: skipping experimental chromeOptions to avoid attach errors')

def copy_profile_to_temp(profile_path, profile_name):
    """Copy Chrome profile to a temp folder while excluding large cache/storage directories."""
    try:
        temp_root = tempfile.mkdtemp(prefix='chrome_profile_')
        dest = os.path.join(temp_root, profile_name)

        # Directories to exclude (case-insensitive substring match)
        exclude_substrings = [
            'cache', 'gpucache', 'code cache', 'service worker', 'serviceworker',
            'indexeddb', 'local storage', 'session storage', 'shadercache', 'cache storage',
            'media cache', 'application cache', 'storage'
        ]

        def _ignore(src, names):
            ignored = []
            for n in list(names):
                low = n.lower()
                for sub in exclude_substrings:
                    if sub in low:
                        ignored.append(n)
                        break
            return set(ignored)

        shutil.copytree(profile_path, dest, ignore=_ignore)
        print(f"[INFO] Profile copied to: {dest} (excluded cache/storage folders)")
        return temp_root
    except Exception as ce:
        print(f"[ERROR] Gagal menyalin profile: {ce}")
        return None

if ATTACH_MODE:
    print('\nATTACH MODE ENABLED:')
    # Try to start Chrome automatically with remote debugging if we found chrome binary
    if CHROME_BINARY:
        # ensure no existing chrome processes (start fresh)
        if chrome_is_running():
            print('[INFO] Existing Chrome detected; attempting to stop it so we can start with remote debugging...')
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
            except Exception:
                pass

        cmd = [CHROME_BINARY, '--remote-debugging-port=9222', f'--user-data-dir={CHROME_USER_DATA}', f'--profile-directory={PROFILE_NAME}']
        print('[INFO] Starting Chrome with remote debugging...')
        try:
            chrome_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[WARNING] Gagal menjalankan Chrome otomatis: {e}")
            print('Silakan jalankan Chrome secara manual dengan flag --remote-debugging-port=9222 lalu tekan ENTER.')
            input('Press [ENTER] after Chrome is running with remote debugging...')
            chrome_proc = None

        # Wait until the remote debugging HTTP endpoint responds
        def wait_for_debugger(host='127.0.0.1', port=9222, timeout=None):
            if timeout is None:
                timeout = ATTACH_MODE_TIMEOUT
            url = f'http://{host}:{port}/json/version'
            waited = 0
            interval = 0.5
            while waited < timeout:
                try:
                    with urllib.request.urlopen(url, timeout=2) as resp:
                        data = resp.read().decode('utf-8')
                        try:
                            info = json.loads(data)
                        except Exception:
                            info = {'raw': data}
                        print(f"[INFO] Remote debugger available")
                        return True
                except Exception:
                    if waited % 2 == 0:  # Print setiap 2 detik saja
                        print(f"[INFO] Waiting for remote debugger... ({int(waited)}s / {timeout}s)")
                    time.sleep(interval)
                    waited += interval
            return False

        print('[INFO] Waiting for Chrome remote debugging endpoint...')
        ready = wait_for_debugger()
        if not ready:
            print('[WARNING] Remote debugger not ready. Switching to direct ChromeDriver launch (ATTACH_MODE=False).')
            # Fallback otomatis: set ATTACH_MODE ke False dan lanjut dengan direct launch
            ATTACH_MODE = False
        
        # Attempt to attach if ready
        attach_success = False
        if ready:
            chrome_options.debugger_address = '127.0.0.1:9222'
            try:
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                print('[OK] Attached to running Chrome via remote debugging port 9222')
                attach_success = True
            except Exception as e:
                print(f"[INFO] Attach attempt failed: {e}")
                print('[INFO] Falling back to direct ChromeDriver launch...')
                ATTACH_MODE = False
        
        # Jika ATTACH_MODE sudah diset False atau attach gagal, gunakan non-attach
        if not attach_success and ATTACH_MODE == False:
            try:
                # Buat fresh Options tanpa debugger_address
                direct_options = Options()
                direct_options.add_argument(f"--user-data-dir={CHROME_USER_DATA}") 
                direct_options.add_argument(f"--profile-directory={PROFILE_NAME}")
                direct_options.add_argument('--ignore-certificate-errors')
                direct_options.add_argument('--allow-running-insecure-content')
                direct_options.add_argument('--no-sandbox')
                direct_options.add_argument('--disable-dev-shm-usage')
                direct_options.add_argument('--no-first-run')
                direct_options.add_argument('--no-default-browser-check')
                direct_options.add_argument('--disable-extensions')
                direct_options.add_argument('--disable-component-update')
                direct_options.add_argument('--disable-background-networking')
                direct_options.add_argument('--disable-popup-blocking')
                direct_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                direct_options.add_experimental_option('useAutomationExtension', False)
                if CHROME_BINARY:
                    direct_options.binary_location = CHROME_BINARY
                
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=direct_options)
                print('[OK] Launched ChromeDriver with direct mode (Profile 6)')
            except Exception as e:
                print(f"[ERROR] Direct launch failed: {e}")
                exit()
    else:
        print('CHROME binary not found. Start Chrome manually with this command:')
        print(f'"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="{CHROME_USER_DATA}" --profile-directory="{PROFILE_NAME}"')
        input('Press [ENTER] after Chrome is running with remote debugging...')
        chrome_options.debugger_address = '127.0.0.1:9222'
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            print('[OK] Attached to running Chrome via remote debugging port 9222')
        except Exception as e:
            print(f"\n[ERROR] Gagal meng-attach ke Chrome yang berjalan: {e}")
            print('Pastikan Chrome sudah dijalankan dengan --remote-debugging-port=9222 dan Profile 6 aktif.')
            exit()
else:
    try:
        # Pastikan Chrome sudah benar-benar ditutup sebelum launch
        if chrome_is_running():
            print("[WARNING] Chrome masih berjalan. Menghentikan paksa...")
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
        
        print("[INFO] Launching ChromeDriver dengan Profile 6...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print('[OK] ChromeDriver berhasil terbuka dengan Profile 6')
    except Exception as e:
        print(f"\n[ERROR] Masih gagal membuka Chrome: {e}")
        print("PASTIKAN SEMUA JENDELA CHROME SUDAH DITUTUP!")
        print("[ACTION] Silakan kill Chrome secara manual: Ctrl+Shift+Esc → Cari chrome.exe → End Task")
        exit()

# --- LOGIN / NAVIGATION CONFIG ---
LOGIN_URL = "https://dc-bmc-master.bfi.co.id:1611/webconsole/home"
DEVICE_URL_TEMPLATE = "https://dc-bmc-master.bfi.co.id:1611/webconsole/device/{aid}/inventories?invindex=2&sortasc=true&standalone=false&sortparam=&cat=1"

def is_logged_in(driver):
    cur = driver.current_url.lower()
    if '/webconsole/home' in cur:
        return True
    if 'login' in cur or 'signin' in cur:
        return False
    return True

def attempt_login(driver, username, password):
    """Attempt login dengan delays yang cukup untuk form merespons."""
    # try several common input selectors (including placeholder-based)
    uname_selectors = [
        "input[name='username']",
        "input[name='user']",
        "input[id='username']",
        "input[id='user']",
        "input[placeholder='_COLNAME_USERNAME_']",
        "input[type='text']",
    ]
    pwd_selectors = [
        "input[name='password']",
        "input[id='password']",
        "input[placeholder='Password']",
        "input[type='password']",
    ]
    submit_selectors = [
        "button[type='submit']",
        "button[id*='WC_SIGNIN']",
        "button[class*='signin']",
        "input[type='submit']",
    ]

    wait = WebDriverWait(driver, 10)
    user_el = None
    pass_el = None

    # Find username input dengan wait sampai visible
    for sel in uname_selectors:
        try:
            user_el = wait.until(EC.presence_of_element_located(('css selector', sel)))
            print(f"[OK] Found username field with selector: {sel}")
            break
        except Exception:
            user_el = None

    # Find password input dengan wait sampai visible
    for sel in pwd_selectors:
        try:
            pass_el = wait.until(EC.presence_of_element_located(('css selector', sel)))
            print(f"[OK] Found password field with selector: {sel}")
            break
        except Exception:
            pass_el = None

    if user_el is None or pass_el is None:
        print("[WARNING] Tidak menemukan field username atau password")
        return False

    try:
        # Clear dan fill username dengan delay
        print(f"[INFO] Mengisi username: {username}")
        user_el.clear()
        time.sleep(0.5)
        user_el.send_keys(username)
        time.sleep(1)  # Beri waktu form memproses input
        
        # Clear dan fill password dengan delay lebih panjang
        print(f"[INFO] Mengisi password...")
        pass_el.clear()
        time.sleep(0.5)
        pass_el.send_keys(password)
        time.sleep(1.5)  # Beri waktu lebih untuk password field
        
        # Submit form dengan mencari button
        submitted = False
        for s in submit_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable(('css selector', s)))
                print(f"[INFO] Klik tombol submit: {s}")
                btn.click()
                submitted = True
                break
            except Exception:
                continue
        
        if not submitted:
            print("[INFO] Tidak menemukan tombol submit, mencoba Enter key")
            try:
                pass_el.send_keys('\n')
            except Exception:
                pass
        
        # Tunggu login selesai dengan wait untuk redirect
        time.sleep(3)
        return True
    except Exception as e:
        print(f"[ERROR] Login attempt gagal: {e}")
        return False

def main():
    if not os.path.exists("id_aset.txt"):
        print("Error: id_aset.txt tidak ditemukan!")
        return

    with open("id_aset.txt", "r") as f:
        asset_ids = [line.strip() for line in f if line.strip()]

    all_data = []
    
    # Buat nama file dengan timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    excel_filename = f"Inventory_Master_Software_{timestamp}.xlsx"

    print("Membuka halaman... Gunakan jendela Chrome yang muncul.")
    # Ensure we're on the home/login page and logged in before scanning
    try:
        driver.get(LOGIN_URL)
        time.sleep(3)
    except Exception as e:
        print(f"[WARNING] Gagal membuka LOGIN_URL: {e}")

    # If not logged in, try auto-login with environment vars, else prompt user to login manually
    if not is_logged_in(driver):
        env_user = os.environ.get('GETDATA_USER')
        env_pass = os.environ.get('GETDATA_PASS')
        used_creds = False
        if env_user and env_pass:
            print('[INFO] Menemukan credentials di environment; mencoba login otomatis...')
            success = attempt_login(driver, env_user, env_pass)
            used_creds = True
            if success:
                time.sleep(3)
        # Fallback to hardcoded credentials in file if environment vars not provided
        if (not env_user or not env_pass) and USERNAME and PASSWORD:
            print('[INFO] Menggunakan credentials yang dikonfigurasi di file; mencoba login otomatis...')
            success = attempt_login(driver, USERNAME, PASSWORD)
            used_creds = True
            if success:
                time.sleep(3)
        if not is_logged_in(driver):
            if not used_creds:
                print('[ACTION] Silakan LOGIN MANUAL di jendela Chrome yang terbuka (gunakan Profile 6).')
            else:
                print('[ACTION] Otomatisasi login gagal. Silakan LOGIN MANUAL di jendela Chrome yang terbuka.')
            input('Setelah Dashboard / halaman home muncul, tekan [ENTER] untuk melanjutkan...')
    
    # Tunggu 5 detik setelah login sebelum mulai fetch data
    print('[INFO] Login berhasil. Menunggu 5 detik sebelum mulai pengambilan data...')
    for countdown in range(5, 0, -1):
        print(f'[INFO] Siap dalam {countdown} detik...')
        time.sleep(1)
    
    for index, aid in enumerate(asset_ids):
        url = DEVICE_URL_TEMPLATE.format(aid=aid)
        try:
            print(f"\n[{index+1}/{len(asset_ids)}] Navigating to asset {aid}...")
            driver.get(url)
            
            # Halaman pertama perlu delay lebih panjang untuk login manual
            if index == 0:
                print(f"[INFO] Ini adalah halaman pertama. Menunggu 20 detik untuk memastikan login selesai...")
                for countdown in range(20, 0, -1):
                    print(f'[INFO] Siap dalam {countdown} detik...')
                    time.sleep(1)
            else:
                time.sleep(5)  # Halaman berikutnya cukup 5 detik

            cur = driver.current_url if driver.current_url else ''
            print(f"Current URL: {cur}")
            
            # Jika diminta login, lakukan auto-login
            if 'login' in cur.lower() or 'signin' in cur.lower():
                print(f"[WARNING] Login diminta. Mencoba auto-login...")
                success = attempt_login(driver, USERNAME, PASSWORD)
                if success:
                    time.sleep(3)
                    driver.get(url)  # Navigate lagi ke asset URL setelah login
                    time.sleep(5)

            print(f"Final URL: {driver.current_url} | Title: {driver.title}")
            time.sleep(3)  # Buffer sebelum extract data
            
            # Scroll ke bawah untuk load semua data tabel (untuk lazy loading)
            print("[INFO] Scrolling ke bawah untuk memastikan semua data tabel dimuat...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10  # Batasi scroll attempts untuk efisiensi
            
            while scroll_attempts < max_scroll_attempts:
                # Scroll ke bawah
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Tunggu data load
                
                # Hitung tinggi baru
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("[INFO] Semua data sudah dimuat (tidak ada scroll baru)")
                    break
                last_height = new_height
                scroll_attempts += 1
                print(f"[INFO] Scroll #{scroll_attempts} - tinggi halaman: {new_height}px")
            
            # Scroll kembali ke atas sebelum extract HTML
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            html_source = driver.page_source
            tables = pd.read_html(io.StringIO(html_source), flavor='html5lib')
            
            if tables:
                df = max(tables, key=len)
                if not df.empty:
                    df.insert(0, 'Asset_ID', aid)
                    all_data.append(df)
                    print(f"[{index+1}/{len(asset_ids)}] Berhasil ditarik: {aid}")
            
            # Auto-save setiap 20 aset
            if (index + 1) % 20 == 0:
                pd.concat(all_data, ignore_index=True).to_excel(excel_filename, index=False)
                print(">> Progress sementara disimpan.")

        except Exception as e:
            print(f"[{index+1}/{len(asset_ids)}] Gagal di ID {aid}: {e}")

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_excel(excel_filename, index=False)
        print(f"\nSELESAI! Data master disimpan ke: {excel_filename}")
    
    driver.quit()

if __name__ == "__main__":
    main()