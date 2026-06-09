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
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- KONFIGURASI ---
BASE_PATH = r"C:\Users\200248\Documents\GETDATAWEB"
CHROME_USER_DATA = r"C:\Users\200248\AppData\Local\Google\Chrome\User Data" # This path might need to be updated for Edge, but keeping as per instruction
PROFILE_NAME = "Profile 6" # This profile name might need to be updated for Edge, but keeping as per instruction

# Credentials
USERNAME = ""
PASSWORD = ""

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
    """Check if Chrome/Edge process is running"""
    try:
        out = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq msedge.exe'], text=True)
        return 'msedge.exe' in out.lower()
    except Exception:
        return False

def kill_all_chrome_aggressive():
    """Aggressively kill all Chrome/Edge processes multiple times"""
    processes = ['msedge.exe', 'msedgedriver.exe', 'chrome.exe', 'chromedriver.exe', 'chromeenterprisecompanion.exe'] # Keep chrome for robustness
    
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
    if chrome_is_running(): # Renamed function, but still checks for msedge.exe
        print("[WARNING] Edge masih berjalan setelah kill attempts")
        time.sleep(3)
    else:
        print("[OK] Semua proses Edge berhasil dihentikan")

def cleanup_chrome_files_aggressive():
    """Aggressively cleanup Chrome/Edge lock and temp files"""
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
        file_path = os.path.join(CHROME_USER_DATA, filename) # This path might need to be updated for Edge, but keeping as per instruction
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
        temp_dir = tempfile.mkdtemp(prefix='edge_profile_') # Changed prefix
        temp_profile = os.path.join(temp_dir, PROFILE_NAME)
        
        print(f"[INFO] Menyalin profile ke: {temp_dir}")
        
        # Exclude large/unnecessary folders - MORE AGGRESSIVE
        exclude_dirs = [
            'cache', 'code cache', 'gpucache', 'service worker', 
            'storage', 'indexeddb', 'local storage', 'session storage',
            'blob_storage', 'file_system', 'databases', 'application cache',
            'shared_proto_db', 'optimization guide', 'heavy ad intervention',
            'site characteristics', 'media cache', 'shader cache',
            'download service', 'reporting and nel', 'shared storage',
            'trust tokens', 'webrtc', 'network action predictor',
            'previews', 'safe browsing', 'gcm store', 'platform notifications'
        ]
        
        def ignore_patterns(directory, files):
            ignored = []
            for name in files:
                name_lower = name.lower()
                # Ignore large folders
                if any(ex in name_lower for ex in exclude_dirs):
                    ignored.append(name)
                # Ignore large files
                elif name.endswith(('.log', '.tmp', '.lock', '.dat', '.bak')):
                    ignored.append(name)
            return ignored
        
        shutil.copytree(profile_path, temp_profile, ignore=ignore_patterns)
        print(f"[OK] Profile berhasil disalin (essential files only)")
        return temp_dir
        
    except Exception as e:
        print(f"[ERROR] Gagal menyalin profile: {e}")
        return None

# CLEANUP PROCESS
print("\n" + "="*60)
print("STEP 1: CLEANUP EDGE PROCESSES") # Changed text
print("="*60)

print("[INFO] Menutup semua Edge yang sedang berjalan...") # Changed text
kill_all_chrome_aggressive()
time.sleep(2)

print("\n" + "="*60)
print("STEP 2: CLEANUP LOCK FILES")
print("="*60)
cleanup_chrome_files_aggressive()
time.sleep(1)

# COPY PROFILE TO TEMP
print("\n" + "="*60)
print("STEP 3: SETUP EDGE PROFILE") # Changed text
print("="*60)

temp_profile_dir = copy_profile_to_temp()
if not temp_profile_dir:
    print("[ERROR] Gagal menyiapkan profile. Menggunakan profile asli...")
    user_data_to_use = CHROME_USER_DATA
    profile_to_use = PROFILE_NAME
else:
    user_data_to_use = temp_profile_dir
    profile_to_use = PROFILE_NAME

# SETUP EDGE OPTIONS
edge_options = Options()
edge_options.add_argument(f"--user-data-dir={user_data_to_use}") 
edge_options.add_argument(f"--profile-directory={profile_to_use}")
edge_options.add_argument('--ignore-certificate-errors')
edge_options.add_argument('--allow-running-insecure-content')
edge_options.add_argument('--no-sandbox')
edge_options.add_argument('--disable-dev-shm-usage')
edge_options.add_argument('--disable-gpu')
edge_options.add_argument('--disable-software-rasterizer')
edge_options.add_argument('--no-first-run')
edge_options.add_argument('--no-default-browser-check')
edge_options.add_argument('--disable-extensions')
edge_options.add_argument('--disable-popup-blocking')
edge_options.add_argument('--start-maximized')
edge_options.add_argument('--remote-debugging-port=0')
edge_options.add_argument('--disable-blink-features=AutomationControlled')
edge_options.add_argument('--disable-features=VizDisplayCompositor')

# DISABLE SESSION RESTORE PROMPTS
edge_options.add_argument('--disable-session-crashed-bubble')
edge_options.add_argument('--disable-infobars')
edge_options.add_argument('--hide-crash-restore-bubble')

edge_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
edge_options.add_experimental_option('useAutomationExtension', False)

# Increase page load timeout
edge_options.page_load_strategy = 'normal'

# Preferences to disable restore session and other popups
prefs = {
    "profile.default_content_setting_values.notifications": 2,  # Block notifications
    "profile.exit_type": "Normal",  # Prevent crash restore
    "profile.exited_cleanly": True,  # Mark as clean exit
    "exit_type": "Normal",
    "exited_cleanly": True,
}
edge_options.add_experimental_option("prefs", prefs)

# Optional: Disable images for faster loading (uncomment if needed)
# prefs["profile.managed_default_content_settings.images"] = 2
# prefs["profile.managed_default_content_settings.stylesheets"] = 2

# Set Edge binary location
possible_bins = [
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
]
EDGE_BINARY = None
for p in possible_bins:
    if os.path.exists(p):
        EDGE_BINARY = p
        break

if EDGE_BINARY:
    edge_options.binary_location = EDGE_BINARY
    print(f"[OK] Using Edge binary: {EDGE_BINARY}")
else:
    print("[WARNING] Edge binary tidak ditemukan")

print(f"[INFO] Using Edge user-data-dir: {user_data_to_use}") # Changed text
print(f"[INFO] Using profile: {profile_to_use}")

# LAUNCH EDGE
print("\n" + "="*60)
print("STEP 4: LAUNCHING EDGE") # Changed text
print("="*60)

driver = None
max_launch_attempts = 3
service = None  # Store service for potential recovery

for attempt in range(1, max_launch_attempts + 1):
    try:
        print(f"\n[INFO] Launch attempt {attempt}/{max_launch_attempts}...")
        service = Service(EdgeChromiumDriverManager().install())
        service.log_path = 'NUL'  # Suppress EdgeDriver logs
        
        driver = webdriver.Edge(service=service, options=edge_options) # Changed to webdriver.Edge and edge_options
        
        # Set longer timeouts
        driver.set_page_load_timeout(60)  # Increased from 30 to 60
        driver.set_script_timeout(30)
        driver.implicitly_wait(10)
        
        # Test if browser is responsive with a simple command
        print('[INFO] Testing browser responsiveness...')
        try:
            driver.execute_script("return document.readyState")
            
            # Add stability check - wait a bit and test again
            time.sleep(2)
            driver.execute_script("return 1")
            
            print('[OK] ChromeDriver berhasil terbuka dan responsive!')
        except Exception as e:
            print(f'[WARNING] Browser not responsive: {e}')
            raise Exception("Browser not responsive")
        
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
            time.sleep(5)  # Increased wait time
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

def is_browser_alive(driver):
    """Check if browser window is still open and responsive"""
    try:
        # Try to get current URL
        _ = driver.current_url
        # Try to execute a simple script
        driver.execute_script("return 1")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if any(phrase in error_msg for phrase in ['no such window', 'target window', 'web view not found', 'session deleted']):
            return False
        return True

def is_logged_in(driver):
    """Check if user is logged in"""
    try:
        cur = driver.current_url.lower()
        
        # Check for login page indicators
        if 'login' in cur or 'signin' in cur or 'auth' in cur:
            return False
            
        # Check for authenticated page indicators
        if '/webconsole/home' in cur or '/webconsole/device' in cur:
            return True
        
        # Check page source for login form
        page_source = driver.page_source.lower()
        if 'password' in page_source and 'sign in' in page_source:
            return False
            
        # Check for session timeout message
        if 'session' in page_source and ('expired' in page_source or 'timeout' in page_source):
            return False
            
        return True
    except Exception:
        return False

def recover_browser(driver, chrome_options, service):
    """Try to recover browser if it crashed or was closed"""
    print("[WARNING] Browser window tertutup atau crash, mencoba recovery...")
    
    try:
        driver.quit()
    except:
        pass
    
    # Kill any remaining Chrome processes
    kill_all_chrome_aggressive()
    time.sleep(3)
    
    # Relaunch browser
    try:
        print("[INFO] Meluncurkan ulang Chrome...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)
        driver.implicitly_wait(10)
        print("[OK] Chrome berhasil diluncurkan ulang")
        return driver
    except Exception as e:
        print(f"[ERROR] Gagal recovery: {e}")
        return None
    """Check if user is logged in"""
    try:
        cur = driver.current_url.lower()
        
        # Check for login page indicators
        if 'login' in cur or 'signin' in cur or 'auth' in cur:
            return False
            
        # Check for authenticated page indicators
        if '/webconsole/home' in cur or '/webconsole/device' in cur:
            return True
        
        # Check page source for login form
        page_source = driver.page_source.lower()
        if 'password' in page_source and 'sign in' in page_source:
            return False
            
        # Check for session timeout message
        if 'session' in page_source and ('expired' in page_source or 'timeout' in page_source):
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
        scroll_pause = 1.0  # Reduced from 1.5 to speed up
        no_change_count = 0
        
        for attempt in range(max_attempts):
            # KEEP-ALIVE: Move mouse to prevent session timeout
            try:
                driver.execute_script("document.body.style.cursor = 'pointer';")
            except:
                pass
            
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
    
    # Check browser is alive before proceeding
    if not is_browser_alive(driver):
        print("[ERROR] Browser sudah tertutup sebelum login!")
        driver = recover_browser(driver, chrome_options, service)
        if not driver:
            print("[FATAL] Tidak dapat recovery browser")
            return
    
    try:
        print("[INFO] Navigating to login page (may take up to 60 seconds)...")
        driver.get(LOGIN_URL)
        
        # Wait for page to be ready
        wait = WebDriverWait(driver, 30)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        print("[OK] Login page loaded successfully")
        time.sleep(3)
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Check if browser crashed
        if 'no such window' in error_msg or 'target window' in error_msg:
            print(f"[ERROR] Browser window tertutup: {e}")
            driver = recover_browser(driver, chrome_options, service)
            if not driver:
                print("[FATAL] Recovery gagal")
                return
            
            # Try to load login page again
            try:
                driver.get(LOGIN_URL)
                time.sleep(5)
            except Exception as e2:
                print(f"[ERROR] Masih gagal setelah recovery: {e2}")
                print("[ACTION] Silakan buka Chrome dan login manual")
                input("Tekan [ENTER] setelah login...")
        else:
            print(f"[ERROR] Gagal membuka LOGIN_URL: {e}")
            print("[INFO] Mencoba reload...")
            
            try:
                # Try to stop page load and navigate again
                driver.execute_script("window.stop();")
                time.sleep(2)
                driver.get(LOGIN_URL)
                time.sleep(5)
                print("[OK] Reload berhasil")
            except Exception as e2:
                print(f"[ERROR] Reload juga gagal: {e2}")
                print("[ACTION] Silakan buka halaman login secara manual di browser")
                input("Tekan [ENTER] setelah halaman login terbuka...")
                time.sleep(2)

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
        max_retries = 2
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                # Check if browser is alive before each asset
                if not is_browser_alive(driver):
                    print(f"\n[ERROR] Browser tertutup terdeteksi sebelum asset {aid}")
                    driver = recover_browser(driver, chrome_options, service)
                    
                    if not driver:
                        print("[FATAL] Tidak dapat recovery browser, skip asset ini")
                        break
                    
                    # Re-login after recovery
                    print("[INFO] Re-login setelah recovery...")
                    driver.get(LOGIN_URL)
                    time.sleep(3)
                    attempt_login(driver, USERNAME, PASSWORD)
                    time.sleep(3)
                
                if retry_count > 0:
                    print(f"\n[RETRY {retry_count}/{max_retries}] Mencoba ulang Asset ID: {aid}")
                else:
                    print(f"\n{'='*60}")
                    print(f"[{index}/{len(asset_ids)}] Processing Asset ID: {aid}")
                    print(f"{'='*60}")
                
                # Navigate to asset page
                driver.get(url)
                time.sleep(5)
                
                # CHECK SESSION - Re-login if needed
                login_retry_count = 0
                max_login_retries = 2
                
                while not is_logged_in(driver) and login_retry_count < max_login_retries:
                    login_retry_count += 1
                    print(f"[WARNING] Session expired atau login diperlukan (attempt {login_retry_count}/{max_login_retries})")
                    
                    # Check if we're on login page
                    current_url = driver.current_url.lower()
                    if 'login' not in current_url and 'signin' not in current_url:
                        # May need to navigate to login first
                        print("[INFO] Navigating to login page...")
                        driver.get(LOGIN_URL)
                        time.sleep(3)
                    
                    # Attempt login
                    print(f"[INFO] Mencoba login ulang...")
                    login_success = attempt_login(driver, USERNAME, PASSWORD)
                    
                    if login_success:
                        time.sleep(3)
                        print(f"[OK] Login ulang berhasil, kembali ke asset {aid}...")
                        driver.get(url)
                        time.sleep(5)
                    else:
                        print(f"[ERROR] Login ulang gagal")
                        if login_retry_count >= max_login_retries:
                            print("[ACTION] MANUAL LOGIN DIPERLUKAN!")
                            input('Silakan login manual di browser, lalu tekan [ENTER]...')
                            driver.get(url)
                            time.sleep(5)
                            break
                
                # Verify we're on the correct page
                if not is_logged_in(driver):
                    print(f"[ERROR] Tidak bisa login untuk asset {aid}, skip...")
                    break
                
                print(f"[INFO] URL: {driver.current_url}")
                print(f"[INFO] Title: {driver.title}")
                
                # Wait for page to fully load - check for common elements
                wait = WebDriverWait(driver, 15)
                
                # Try to wait for table or "no data" indicator
                page_loaded = False
                try:
                    # Wait for either table or empty message
                    wait.until(lambda d: 
                        len(d.find_elements(By.CSS_SELECTOR, "table")) > 0 or
                        len(d.find_elements(By.CSS_SELECTOR, "div[class*='no-data'], div[class*='empty'], div.alert")) > 0
                    )
                    page_loaded = True
                    print("[OK] Page content loaded")
                except Exception as e:
                    print(f"[WARNING] Timeout waiting for content: {e}")
                    time.sleep(3)  # Extra wait
                
                # Check if page has "no data" message
                page_source_lower = driver.page_source.lower()
                if any(phrase in page_source_lower for phrase in ['no data', 'no records', 'tidak ada data', 'empty']):
                    # Check if it's truly empty or just loading
                    time.sleep(3)
                    page_source_lower = driver.page_source.lower()  # Recheck
                    
                    if any(phrase in page_source_lower for phrase in ['no data', 'no records', 'tidak ada data']):
                        print(f"[INFO] Asset {aid} tidak memiliki data software")
                        success = True  # Mark as success (empty is valid)
                        break
                
                # Scroll to load all data
                scroll_and_load_table(driver)
                
                # Extra wait after scroll
                time.sleep(2)
                
                # Extract table data
                html_source = driver.page_source
                
                # Debug: Check if HTML contains table
                if '<table' not in html_source.lower():
                    print(f"[WARNING] Tidak ada tag <table> dalam HTML")
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"[INFO] Akan retry setelah 5 detik...")
                        time.sleep(5)
                        continue
                    else:
                        print(f"[ERROR] Gagal setelah {max_retries} retries")
                        break
                
                tables = pd.read_html(io.StringIO(html_source), flavor='html5lib')
                
                if tables:
                    # Filter out small tables (likely navigation/headers)
                    valid_tables = [t for t in tables if len(t) > 1]
                    
                    if valid_tables:
                        df = max(valid_tables, key=lambda x: len(x))
                        
                        if not df.empty:
                            df.insert(0, 'Asset_ID', aid)
                            all_data.append(df)
                            print(f"[OK] Berhasil: {len(df)} baris data")
                            success = True
                        else:
                            print(f"[WARNING] Tabel kosong untuk asset {aid}")
                            if retry_count < max_retries:
                                retry_count += 1
                                time.sleep(3)
                                continue
                            success = True  # Empty table is valid
                    else:
                        print(f"[WARNING] Tidak ada tabel valid (semua tabel terlalu kecil)")
                        if retry_count < max_retries:
                            retry_count += 1
                            time.sleep(3)
                            continue
                        success = True
                else:
                    print(f"[WARNING] Tidak ada tabel ditemukan")
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"[INFO] Retry {retry_count}/{max_retries} setelah 5 detik...")
                        time.sleep(5)
                        continue
                    else:
                        print(f"[ERROR] Tidak ada tabel setelah {max_retries} retries")
                        break
                
            except Exception as e:
                error_msg = str(e).lower()
                print(f"[ERROR] Exception: {e}")
                
                # Check if browser crashed/closed
                if 'no such window' in error_msg or 'target window' in error_msg or 'web view not found' in error_msg:
                    print("[ERROR] Browser window tertutup atau crash!")
                    
                    driver = recover_browser(driver, chrome_options, service)
                    
                    if driver:
                        print("[INFO] Recovery berhasil, re-login...")
                        try:
                            driver.get(LOGIN_URL)
                            time.sleep(3)
                            attempt_login(driver, USERNAME, PASSWORD)
                            time.sleep(3)
                            
                            # Retry this asset
                            if retry_count < max_retries:
                                retry_count += 1
                                continue
                        except Exception as recovery_error:
                            print(f"[ERROR] Re-login gagal: {recovery_error}")
                    else:
                        print("[FATAL] Recovery browser gagal, stop processing")
                        return  # Exit main function
                
                # Check if it's a session issue
                try:
                    if driver and is_browser_alive(driver) and not is_logged_in(driver):
                        print("[INFO] Terdeteksi session timeout")
                except:
                    pass
                
                if retry_count < max_retries:
                    retry_count += 1
                    print(f"[INFO] Retry {retry_count}/{max_retries} setelah error...")
                    time.sleep(5)
                    continue
                else:
                    break
        
        # Autosave every 10 assets (reduced from 20 for safety)
        if index % 10 == 0 and all_data:
            temp_df = pd.concat(all_data, ignore_index=True)
            temp_df.to_excel(excel_filename, index=False)
            print(f"\n{'='*60}")
            print(f"[AUTOSAVE] Progress saved: {len(all_data)} assets")
            print(f"File: {excel_filename}")
            print(f"{'='*60}")
            
            # Refresh session after autosave to prevent timeout
            print(f"[INFO] Refreshing session...")
            try:
                driver.get(LOGIN_URL)
                time.sleep(2)
            except:
                pass

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