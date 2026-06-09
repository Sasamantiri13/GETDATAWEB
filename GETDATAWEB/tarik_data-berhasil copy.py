import pandas as pd
import time
import os
import io
import urllib3
import subprocess
import shutil
import tempfile
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- KONFIGURASI ---
BASE_PATH = r"C:\Users\200248\Documents\GETDATAWEB"
CHROME_USER_DATA = r"C:\Users\200248\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME = "Profile 6"

# Credentials
USERNAME = "bfi\200248"
PASSWORD = "Indomes1@raya"

os.chdir(BASE_PATH)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Verifikasi profil ada
profile_path = os.path.join(CHROME_USER_DATA, PROFILE_NAME)
if not os.path.exists(profile_path):
    print(f"[ERROR] Profil '{PROFILE_NAME}' tidak ditemukan di: {profile_path}")
    exit()
else:
    print(f"[OK] Profil '{PROFILE_NAME}' ditemukan di Chrome User Data.")

def chrome_is_running():
    """Check if Chrome process is running"""
    try:
        out = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], text=True)
        return 'chrome.exe' in out.lower()
    except Exception:
        return False

def kill_all_chrome_aggressive():
    """Aggressively kill all Chrome processes multiple times"""
    processes = ['chrome.exe', 'chromedriver.exe', 'chromeenterprisecompanion.exe']
    
    for attempt in range(3):
        killed_any = False
        for proc in processes:
            try:
                result = subprocess.run(['taskkill', '/F', '/IM', proc], 
                                      capture_output=True, 
                                      text=True)
                if 'SUCCESS' in result.stdout:
                    killed_any = True
                    print(f"[INFO] Killed {proc}")
            except Exception:
                pass
        
        if not killed_any:
            break
            
        time.sleep(2)
    
    # Final check
    if chrome_is_running():
        print("[WARNING] Chrome masih berjalan setelah kill attempts")
        time.sleep(3)
    else:
        print("[OK] Semua proses Chrome berhasil dihentikan")

def cleanup_chrome_files_aggressive():
    """Aggressively cleanup Chrome lock and temp files"""
    files_to_delete = [
        'DevToolsActivePort',
        'SingletonLock',
        'SingletonSocket',
        'SingletonCookie',
        'lockfile'
    ]
    
    print("[INFO] Membersihkan lock files...")
    deleted_count = 0
    
    for filename in files_to_delete:
        file_path = os.path.join(profile_path, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
                print(f"[OK] Deleted: {filename}")
        except Exception as e:
            print(f"[WARNING] Gagal menghapus {filename}: {e}")
    
    # Also try to delete in parent directory
    parent_files = ['SingletonLock', 'SingletonSocket', 'SingletonCookie']
    for filename in parent_files:
        file_path = os.path.join(CHROME_USER_DATA, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
                print(f"[OK] Deleted parent: {filename}")
        except Exception as e:
            pass
    
    print(f"[INFO] Deleted {deleted_count} lock file(s)")

def copy_profile_to_temp():
    """Copy profile to temp directory to avoid lock issues"""
    try:
        temp_dir = tempfile.mkdtemp(prefix='chrome_profile_')
        temp_profile = os.path.join(temp_dir, PROFILE_NAME)
        
        print(f"[INFO] Menyalin profile ke: {temp_dir}")
        
        # Exclude large/unnecessary folders
        exclude_dirs = ['cache', 'code cache', 'gpucache', 'service worker', 
                       'storage', 'indexeddb', 'local storage', 'session storage']
        
        def ignore_patterns(directory, files):
            ignored = []
            for name in files:
                name_lower = name.lower()
                if any(ex in name_lower for ex in exclude_dirs):
                    ignored.append(name)
            return ignored
        
        shutil.copytree(profile_path, temp_profile, ignore=ignore_patterns)
        print(f"[OK] Profile berhasil disalin")
        return temp_dir
        
    except Exception as e:
        print(f"[ERROR] Gagal menyalin profile: {e}")
        return None

# CLEANUP PROCESS
print("\n" + "="*60)
print("STEP 1: CLEANUP CHROME PROCESSES")
print("="*60)

print("[INFO] Menutup semua Chrome yang sedang berjalan...")
kill_all_chrome_aggressive()
time.sleep(2)

print("\n" + "="*60)
print("STEP 2: CLEANUP LOCK FILES")
print("="*60)
cleanup_chrome_files_aggressive()
time.sleep(1)

# COPY PROFILE TO TEMP
print("\n" + "="*60)
print("STEP 3: SETUP CHROME PROFILE")
print("="*60)

temp_profile_dir = copy_profile_to_temp()
if not temp_profile_dir:
    print("[ERROR] Gagal menyiapkan profile. Menggunakan profile asli...")
    user_data_to_use = CHROME_USER_DATA
    profile_to_use = PROFILE_NAME
else:
    user_data_to_use = temp_profile_dir
    profile_to_use = PROFILE_NAME

# SETUP CHROME OPTIONS
chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={user_data_to_use}") 
chrome_options.add_argument(f"--profile-directory={profile_to_use}")
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--allow-running-insecure-content')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration
chrome_options.add_argument('--disable-software-rasterizer')
chrome_options.add_argument('--no-first-run')
chrome_options.add_argument('--no-default-browser-check')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--disable-popup-blocking')
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--remote-debugging-port=0')  # Random port to avoid conflicts
chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Disable images and CSS for faster loading (optional - comment out if you need to see the page)
# prefs = {
#     "profile.managed_default_content_settings.images": 2,
#     "profile.default_content_setting_values.notifications": 2,
# }
# chrome_options.add_experimental_option("prefs", prefs)

# Set Chrome binary location
possible_bins = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
]
CHROME_BINARY = None
for p in possible_bins:
    if os.path.exists(p):
        CHROME_BINARY = p
        break

if CHROME_BINARY:
    chrome_options.binary_location = CHROME_BINARY
    print(f"[OK] Using Chrome binary: {CHROME_BINARY}")
else:
    print("[WARNING] Chrome binary tidak ditemukan")

print(f"[INFO] Using Chrome user-data-dir: {user_data_to_use}")
print(f"[INFO] Using profile: {profile_to_use}")

# LAUNCH CHROME
print("\n" + "="*60)
print("STEP 4: LAUNCHING CHROME")
print("="*60)

driver = None
max_launch_attempts = 3

for attempt in range(1, max_launch_attempts + 1):
    try:
        print(f"\n[INFO] Launch attempt {attempt}/{max_launch_attempts}...")
        service = Service(ChromeDriverManager().install())
        service.log_path = 'NUL'  # Suppress ChromeDriver logs
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Test if browser is responsive
        driver.set_page_load_timeout(30)
        print('[OK] ChromeDriver berhasil terbuka!')
        break
        
    except Exception as e:
        print(f"[ERROR] Attempt {attempt} gagal: {e}")
        
        if attempt < max_launch_attempts:
            print("[INFO] Mencoba cleanup dan retry...")
            
            # Cleanup
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            kill_all_chrome_aggressive()
            cleanup_chrome_files_aggressive()
            time.sleep(3)
        else:
            print("\n" + "="*60)
            print("GAGAL MEMBUKA CHROME SETELAH 3 ATTEMPTS")
            print("="*60)
            print("\nSOLUSI MANUAL:")
            print("1. Buka Task Manager (Ctrl+Shift+Esc)")
            print("2. Cari dan End Task semua proses 'Google Chrome'")
            print("3. Cari dan End Task semua proses 'chromedriver'")
            print("4. Restart komputer jika masalah berlanjut")
            print("5. Jalankan script ini lagi")
            exit(1)

# --- LOGIN / NAVIGATION CONFIG ---
LOGIN_URL = "https://dc-bmc-master.bfi.co.id:1611/webconsole/home"
DEVICE_URL_TEMPLATE = "https://dc-bmc-master.bfi.co.id:1611/webconsole/device/{aid}/inventories?invindex=2&sortasc=true&standalone=false&sortparam=&cat=1"

def is_logged_in(driver):
    """Check if user is logged in"""
    try:
        cur = driver.current_url.lower()
        if '/webconsole/home' in cur or '/webconsole/device' in cur:
            return True
        if 'login' in cur or 'signin' in cur:
            return False
        return True
    except Exception:
        return False

def attempt_login(driver, username, password):
    """Attempt login with improved selector matching"""
    wait = WebDriverWait(driver, 15)
    
    try:
        time.sleep(2)
        
        # Find username field
        user_el = None
        user_selectors = [
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.CSS_SELECTOR, "input[name='user']"),
            (By.CSS_SELECTOR, "input[id='username']"),
            (By.CSS_SELECTOR, "input[placeholder*='username' i]"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]
        
        for by, selector in user_selectors:
            try:
                user_el = wait.until(EC.presence_of_element_located((by, selector)))
                print(f"[OK] Found username field: {selector}")
                break
            except Exception:
                continue
        
        # Find password field
        pass_el = None
        pass_selectors = [
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[id='password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]
        
        for by, selector in pass_selectors:
            try:
                pass_el = wait.until(EC.presence_of_element_located((by, selector)))
                print(f"[OK] Found password field: {selector}")
                break
            except Exception:
                continue
        
        if not user_el or not pass_el:
            print("[ERROR] Tidak dapat menemukan form login")
            return False
        
        # Fill credentials
        print(f"[INFO] Mengisi username: {username}")
        user_el.clear()
        time.sleep(0.5)
        user_el.send_keys(username)
        time.sleep(1)
        
        print(f"[INFO] Mengisi password...")
        pass_el.clear()
        time.sleep(0.5)
        pass_el.send_keys(password)
        time.sleep(1.5)
        
        # Submit
        submit_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "button[id*='signin' i]"),
            (By.CSS_SELECTOR, "button[class*='signin' i]"),
            (By.CSS_SELECTOR, "input[type='submit']"),
        ]
        
        submitted = False
        for by, selector in submit_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((by, selector)))
                print(f"[INFO] Klik tombol submit: {selector}")
                btn.click()
                submitted = True
                break
            except Exception:
                continue
        
        if not submitted:
            print("[INFO] Mencoba Enter key untuk submit")
            pass_el.send_keys('\n')
        
        time.sleep(4)
        return True
        
    except Exception as e:
        print(f"[ERROR] Login gagal: {e}")
        return False

def scroll_and_load_table(driver, max_attempts=20):
    """Scroll INSIDE table container untuk memuat semua data dengan locked header"""
    print("[INFO] Mencari dan scrolling tabel dengan locked header...")
    
    try:
        # Wait for table to load
        time.sleep(2)
        
        # Find table container - try multiple selectors
        table_container = None
        container_selectors = [
            "div.dataTables_scrollBody",  # DataTables plugin
            "div[class*='table-scroll']",
            "div[class*='scroll-body']",
            "div[style*='overflow']",
            "div.table-responsive",
            "div[class*='tbody']",
            ".ag-body-viewport",  # AG Grid
            ".ReactVirtualized__Grid",  # React Virtualized
        ]
        
        for selector in container_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    # Check if element has scrollable content
                    scroll_height = driver.execute_script("return arguments[0].scrollHeight;", elem)
                    client_height = driver.execute_script("return arguments[0].clientHeight;", elem)
                    
                    if scroll_height > client_height:
                        table_container = elem
                        print(f"[OK] Found scrollable table container: {selector}")
                        print(f"     Scroll height: {scroll_height}px, Visible: {client_height}px")
                        break
                
                if table_container:
                    break
            except Exception:
                continue
        
        if not table_container:
            print("[WARNING] Tidak menemukan table container dengan scroll, mencoba scroll halaman...")
            # Fallback to page scroll
            last_height = driver.execute_script("return document.body.scrollHeight")
            for attempt in range(10):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            return True
        
        # Scroll inside the table container
        print("[INFO] Scrolling di dalam tabel...")
        last_scroll_top = 0
        scroll_pause = 1.5
        no_change_count = 0
        
        for attempt in range(max_attempts):
            # Get current scroll position
            current_scroll = driver.execute_script("return arguments[0].scrollTop;", table_container)
            scroll_height = driver.execute_script("return arguments[0].scrollHeight;", table_container)
            client_height = driver.execute_script("return arguments[0].clientHeight;", table_container)
            
            # Scroll down inside container
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", table_container)
            time.sleep(scroll_pause)
            
            # Check new position
            new_scroll = driver.execute_script("return arguments[0].scrollTop;", table_container)
            new_scroll_height = driver.execute_script("return arguments[0].scrollHeight;", table_container)
            
            print(f"[INFO] Scroll #{attempt + 1} - Position: {new_scroll}/{new_scroll_height}px")
            
            # Check if we've reached the bottom or no new data loaded
            if new_scroll == last_scroll_top:
                no_change_count += 1
                if no_change_count >= 3:
                    print(f"[INFO] Tidak ada perubahan setelah {no_change_count} attempts - scroll selesai")
                    break
            else:
                no_change_count = 0
            
            # Check if scroll height increased (lazy loading)
            if new_scroll_height > scroll_height:
                print(f"[INFO] Data baru dimuat: {scroll_height}px -> {new_scroll_height}px")
            
            # If we're at the bottom and no new data
            if new_scroll + client_height >= new_scroll_height - 10:
                if new_scroll_height == scroll_height:
                    print("[OK] Mencapai akhir tabel")
                    break
            
            last_scroll_top = new_scroll
        
        # Scroll back to top of table
        driver.execute_script("arguments[0].scrollTop = 0;", table_container)
        time.sleep(1)
        
        # Also scroll page to top to ensure we can extract all HTML
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        print("[OK] Semua data tabel sudah dimuat")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error saat scrolling tabel: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    global driver
    
    if not os.path.exists("id_aset.txt"):
        print("[ERROR] id_aset.txt tidak ditemukan!")
        driver.quit()
        return

    with open("id_aset.txt", "r") as f:
        asset_ids = [line.strip() for line in f if line.strip()]

    all_data = []
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    excel_filename = f"Inventory_Master_Software_{timestamp}.xlsx"

    print("\n" + "="*60)
    print("STEP 5: LOGIN & DATA EXTRACTION")
    print("="*60)
    
    print("\n[INFO] Membuka halaman login...")
    try:
        driver.get(LOGIN_URL)
        time.sleep(3)
    except Exception as e:
        print(f"[ERROR] Gagal membuka LOGIN_URL: {e}")
        driver.quit()
        return

    # Login
    if not is_logged_in(driver):
        env_user = os.environ.get('GETDATA_USER', USERNAME)
        env_pass = os.environ.get('GETDATA_PASS', PASSWORD)
        
        if env_user and env_pass:
            print('[INFO] Mencoba login otomatis...')
            success = attempt_login(driver, env_user, env_pass)
            if success:
                time.sleep(3)
        
        if not is_logged_in(driver):
            print('[ACTION] LOGIN MANUAL di Chrome, lalu tekan [ENTER]')
            input('Tekan [ENTER] setelah login berhasil...')
    
    print('[OK] Login berhasil!')
    time.sleep(3)
    
    # Process assets
    for index, aid in enumerate(asset_ids, 1):
        url = DEVICE_URL_TEMPLATE.format(aid=aid)
        try:
            print(f"\n{'='*60}")
            print(f"[{index}/{len(asset_ids)}] Processing Asset ID: {aid}")
            print(f"{'='*60}")
            
            driver.get(url)
            time.sleep(5)
            
            if not is_logged_in(driver):
                print(f"[WARNING] Session expired, login ulang...")
                attempt_login(driver, USERNAME, PASSWORD)
                time.sleep(3)
                driver.get(url)
                time.sleep(5)
            
            print(f"[INFO] URL: {driver.current_url}")
            print(f"[INFO] Title: {driver.title}")
            
            scroll_and_load_table(driver)
            
            html_source = driver.page_source
            tables = pd.read_html(io.StringIO(html_source), flavor='html5lib')
            
            if tables:
                df = max(tables, key=lambda x: len(x))
                
                if not df.empty:
                    df.insert(0, 'Asset_ID', aid)
                    all_data.append(df)
                    print(f"[OK] Berhasil: {len(df)} baris data")
                else:
                    print(f"[WARNING] Tabel kosong")
            else:
                print(f"[WARNING] Tidak ada tabel")
            
            # Autosave every 20
            if index % 20 == 0 and all_data:
                temp_df = pd.concat(all_data, ignore_index=True)
                temp_df.to_excel(excel_filename, index=False)
                print(f"\n[AUTOSAVE] Progress saved: {len(all_data)} assets")

        except Exception as e:
            print(f"[ERROR] Gagal: {e}")
            continue

    # Final save
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_excel(excel_filename, index=False)
        print(f"\n{'='*60}")
        print(f"[SUCCESS] SELESAI!")
        print(f"Total Assets: {len(asset_ids)}")
        print(f"Berhasil: {len(all_data)}")
        print(f"Total Rows: {len(final_df)}")
        print(f"File: {excel_filename}")
        print(f"{'='*60}")
    else:
        print("\n[WARNING] Tidak ada data")
    
    print("\n[INFO] Menutup browser...")
    driver.quit()
    
    # Cleanup temp profile
    if temp_profile_dir and os.path.exists(temp_profile_dir):
        try:
            shutil.rmtree(temp_profile_dir)
            print("[INFO] Temp profile dibersihkan")
        except:
            pass
    
    print("[OK] Selesai!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Program dihentikan")
        try:
            driver.quit()
        except:
            pass
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        try:
            driver.quit()
        except:
            pass