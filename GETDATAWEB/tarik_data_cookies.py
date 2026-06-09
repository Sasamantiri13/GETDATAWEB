import pandas as pd
import time
import os
import io
import urllib3
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- KONFIGURASI ---
BASE_PATH = r"C:\Users\200248\Documents\GETDATAWEB\GETDATAWEB"
COOKIES_FILE = "cookies.json"

# Credentials (optional, jika cookie gagal)
USERNAME = ""
PASSWORD = ""

os.chdir(BASE_PATH)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_cookies():
    """Load cookies from JSON file"""
    cookie_path = os.path.join(BASE_PATH, COOKIES_FILE)
    if not os.path.exists(cookie_path):
        print(f"[WARNING] File {COOKIES_FILE} tidak ditemukan!")
        print(f"[INFO] Silakan buat file cookies.json atau gunakan login manual")
        return None
    
    try:
        with open(cookie_path, 'r') as f:
            cookies = json.load(f)
        print(f"[OK] Loaded {len(cookies)} cookies from {COOKIES_FILE}")
        return cookies
    except Exception as e:
        print(f"[ERROR] Gagal membaca cookies: {e}")
        return None

def inject_cookies(driver, cookies):
    """Inject cookies into browser session"""
    if not cookies:
        return False
    
    try:
        for cookie in cookies:
            # Selenium requires specific cookie format
            cookie_dict = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie.get('domain', 'dc-bmc-master.bfi.co.id'),
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', True)
            }
            driver.add_cookie(cookie_dict)
            print(f"[OK] Injected cookie: {cookie['name']}")
        return True
    except Exception as e:
        print(f"[ERROR] Gagal inject cookies: {e}")
        return False

# Browser Setup
edge_options = Options()
edge_options.add_argument('--ignore-certificate-errors')
edge_options.add_argument('--disable-gpu')
edge_options.add_argument('--no-sandbox')
edge_options.add_argument('--start-maximized')
edge_options.add_argument('--disable-blink-features=AutomationControlled')
edge_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
edge_options.add_experimental_option('useAutomationExtension', False)

# Preferences
prefs = {
    "profile.default_content_setting_values.notifications": 2,
}
edge_options.add_experimental_option("prefs", prefs)

# Find msedge.exe
possible_bins = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
]
CHROME_BINARY = None
for p in possible_bins:
    if os.path.exists(p):
        CHROME_BINARY = p
        break

if CHROME_BINARY:
    chrome_options.binary_location = CHROME_BINARY
    print(f"[OK] Using Chrome binary: {CHROME_BINARY}")

# LAUNCH CHROME
print("\n" + "="*60)
print("STEP 1: LAUNCHING CHROME")
print("="*60)

driver = None
service = Service(ChromeDriverManager().install())
service.log_path = 'NUL'

try:
    print("[INFO] Starting ChromeDriver...")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)
    driver.implicitly_wait(10)
    print('[OK] ChromeDriver started successfully!')
except Exception as e:
    print(f"[ERROR] Failed to start Chrome: {e}")
    exit(1)

# --- LOGIN / NAVIGATION CONFIG ---
LOGIN_URL = "https://dc-bmc-master.bfi.co.id:1611/webconsole/home"
DEVICE_URL_TEMPLATE = "https://dc-bmc-master.bfi.co.id:1611/webconsole/device/{aid}/inventories?invindex=2&sortasc=true&standalone=false&sortparam=&cat=1"

def is_logged_in(driver):
    """Check if user is logged in"""
    try:
        cur = driver.current_url.lower()
        if 'login' in cur or 'signin' in cur or 'auth' in cur:
            return False
        if '/webconsole/home' in cur or '/webconsole/device' in cur:
            return True
        page_source = driver.page_source.lower()
        if 'password' in page_source and 'sign in' in page_source:
            return False
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
        user_el = None
        user_selectors = [
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.CSS_SELECTOR, "input[name='user']"),
            (By.CSS_SELECTOR, "input[id='username']"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]
        for by, selector in user_selectors:
            try:
                user_el = wait.until(EC.presence_of_element_located((by, selector)))
                break
            except Exception: continue
        
        pass_el = None
        pass_selectors = [
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[id='password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]
        for by, selector in pass_selectors:
            try:
                pass_el = wait.until(EC.presence_of_element_located((by, selector)))
                break
            except Exception: continue
        
        if not user_el or not pass_el:
            print("[ERROR] Tidak dapat menemukan form login")
            return False
        
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
            (By.CSS_SELECTOR, "input[type='submit']"),
        ]
        submitted = False
        for by, selector in submit_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((by, selector)))
                btn.click()
                submitted = True
                break
            except Exception: continue
        
        if not submitted:
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
        time.sleep(2)
        table_container = None
        container_selectors = [
            "div.dataTables_scrollBody",
            "div[class*='table-scroll']",
            "div[class*='scroll-body']",
            "div[style*='overflow']",
            "div.table-responsive",
        ]
        for selector in container_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    scroll_height = driver.execute_script("return arguments[0].scrollHeight;", elem)
                    client_height = driver.execute_script("return arguments[0].clientHeight;", elem)
                    if scroll_height > client_height:
                        table_container = elem
                        print(f"[OK] Found scrollable table container: {selector}")
                        print(f"     Scroll height: {scroll_height}px, Visible: {client_height}px")
                        break
                if table_container: break
            except Exception: continue
        
        if not table_container:
            print("[WARNING] Tidak menemukan table container dengan scroll, mencoba scroll halaman...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            return True
        
        print("[INFO] Scrolling di dalam tabel...")
        last_scroll_top = 0
        scroll_pause = 1.0
        no_change_count = 0
        
        for attempt in range(max_attempts):
            try: driver.execute_script("document.body.style.cursor = 'pointer';")
            except: pass
            
            scroll_height = driver.execute_script("return arguments[0].scrollHeight;", table_container)
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", table_container)
            time.sleep(scroll_pause)
            
            new_scroll = driver.execute_script("return arguments[0].scrollTop;", table_container)
            new_scroll_height = driver.execute_script("return arguments[0].scrollHeight;", table_container)
            
            print(f"[INFO] Scroll #{attempt + 1} - Position: {new_scroll}/{new_scroll_height}px")
            
            if new_scroll == last_scroll_top:
                no_change_count += 1
                if no_change_count >= 3:
                    print(f"[INFO] Tidak ada perubahan setelah {no_change_count} attempts - scroll selesai")
                    break
            else:
                no_change_count = 0
            
            if new_scroll_height > scroll_height:
                print(f"[INFO] Data baru dimuat: {scroll_height}px -> {new_scroll_height}px")
            
            last_scroll_top = new_scroll
        
        driver.execute_script("arguments[0].scrollTop = 0;", table_container)
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        print("[OK] Semua data tabel sudah dimuat")
        return True
    except Exception as e:
        print(f"[ERROR] Error saat scrolling tabel: {e}")
        return False

def main():
    global driver
    
    if not os.path.exists("id_aset.txt"):
        print("[ERROR] id_aset.txt tidak ditemukan!")
        if driver: driver.quit()
        return

    with open("id_aset.txt", "r") as f:
        asset_ids = [line.strip() for line in f if line.strip()]

    all_data = []
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    excel_filename = f"Inventory_Master_Software_{timestamp}.xlsx"

    print("\n" + "="*60)
    print("STEP 2: AUTHENTICATION")
    print("="*60)
    
    # Load cookies
    cookies = load_cookies()
    
    # Navigate to domain first (required before adding cookies)
    print("\n[INFO] Navigating to domain...")
    try:
        driver.get(LOGIN_URL)
        time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Failed to navigate: {e}")
    
    # Inject cookies if available
    if cookies:
        print("[INFO] Injecting cookies...")
        if inject_cookies(driver, cookies):
            # Refresh to apply cookies
            driver.refresh()
            time.sleep(3)
            
            if is_logged_in(driver):
                print("[OK] Authentication successful via cookies!")
            else:
                print("[WARNING] Cookies injected but not logged in")
                cookies = None  # Fall back to manual login
    
    # Fallback to manual/auto login if cookies failed
    if not cookies or not is_logged_in(driver):
        print("\n[INFO] Cookie authentication failed or unavailable")
        
        if USERNAME and PASSWORD:
            print('[INFO] Attempting automatic login...')
            attempt_login(driver, USERNAME, PASSWORD)
        
        if not is_logged_in(driver):
            print('[ACTION] MANUAL LOGIN required in Chrome, then press [ENTER]')
            input('Press [ENTER] after successful login...')
    
    print('[OK] Login successful!')
    time.sleep(3)
    
    # --- PROCESS ASSETS ---
    print("\n" + "="*60)
    print("STEP 3: DATA EXTRACTION")
    print("="*60)
    
    for index, aid in enumerate(asset_ids, 1):
        url = DEVICE_URL_TEMPLATE.format(aid=aid)
        max_retries = 2
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                if retry_count > 0:
                    print(f"\n[RETRY {retry_count}/{max_retries}] Mencoba ulang Asset ID: {aid}")
                else:
                    print(f"\n{'='*60}")
                    print(f"[{index}/{len(asset_ids)}] Processing Asset ID: {aid}")
                    print(f"{'='*60}")
                
                # Navigate
                driver.get(url)
                time.sleep(5)
                
                # Check login
                if not is_logged_in(driver):
                    print("[INFO] Session expired, login ulang...")
                    if USERNAME and PASSWORD: 
                        attempt_login(driver, USERNAME, PASSWORD)
                    else: 
                        print("[ACTION] Session expired. Manual login then press Enter.")
                        input("Press Enter...")
                    driver.get(url)
                    time.sleep(5)
                
                print(f"[INFO] Title: {driver.title}")

                # Check for empty data
                page_source_lower = driver.page_source.lower()
                no_data_keywords = ['no data', 'no records', 'tidak ada data', 'empty', '0 items', 'no result', 'no information available']
                
                if any(k in page_source_lower for k in no_data_keywords):
                     print(f"[INFO] Asset {aid} detected as empty (Keyword found).")
                     success = True
                     break

                # Check for table
                has_table = len(driver.find_elements(By.TAG_NAME, "table")) > 0
                
                if not has_table:
                    print(f"[WARNING] No table found for Asset {aid}")
                    if retry_count >= max_retries:
                        print(f"[WARNING] Skipping asset {aid} (assumed 0 data/error after retries)")
                        success = True 
                        break
                    retry_count += 1
                    time.sleep(5)
                    continue

                # Scroll & Extract
                scroll_and_load_table(driver)
                time.sleep(2)
                
                html_source = driver.page_source
                tables = pd.read_html(io.StringIO(html_source), flavor='html5lib')
                
                valid_tables = [t for t in tables if len(t) > 1]
                if valid_tables:
                    df = max(valid_tables, key=lambda x: len(x))
                    if not df.empty:
                        df.insert(0, 'Asset_ID', aid)
                        all_data.append(df)
                        print(f"[OK] Success: {len(df)} rows")
                        success = True
                    else:
                        print("[INFO] Table found but empty")
                        success = True
                else:
                    print("[WARNING] Table found but invalid structure")
                    retry_count += 1

            except Exception as e:
                print(f"[ERROR] Exception on asset {aid}: {e}")
                retry_count += 1
                time.sleep(5)
        
        # Autosave
        if index % 10 == 0 and all_data:
            temp_df = pd.concat(all_data, ignore_index=True)
            temp_df.to_excel(excel_filename, index=False)
            print(f"[AUTOSAVE] Saved {len(all_data)} assets to {excel_filename}")

    # Final save
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_excel(excel_filename, index=False)
        print(f"\n{'='*60}")
        print(f"[SUCCESS] COMPLETE!")
        print(f"Total Assets: {len(asset_ids)}")
        print(f"Successful: {len(all_data)}")
        print(f"Total Rows: {len(final_df)}")
        print(f"File: {excel_filename}")
        print(f"{'='*60}")
    else:
        print("\n[WARNING] No data extracted.")
    
    print("\n[INFO] Closing browser...")
    if driver: driver.quit()
    print("[OK] Done!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Program stopped by user")
        try: driver.quit()
        except: pass
    except Exception as e:
        print(f"\n[ERROR] Unexpected: {e}")
        try: driver.quit()
        except: pass
