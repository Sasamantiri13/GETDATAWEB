import pandas as pd
import time
import os
import io
import urllib3
import json
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- KONFIGURASI ---
BASE_PATH = os.getenv('BASE_PATH', r"C:\Users\200248\Documents\GETDATAWEB\GETDATAWEB")
COOKIES_FILE = "cookies.json.encrypted"
LOGIN_URL = os.getenv('LOGIN_URL', "https://dc-bmc-master.bfi.co.id:1611/webconsole/home")

# Credentials from environment (RECOMMENDED)
USERNAME = os.getenv('APP_USERNAME', "")
PASSWORD = os.getenv('APP_PASSWORD', "")

os.chdir(BASE_PATH)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_encryption_key():
    """Get or generate encryption key"""
    key = os.getenv('COOKIE_ENCRYPTION_KEY')
    if not key:
        # Generate new key if not exists
        key = Fernet.generate_key().decode()
        print(f"[INFO] Generated new encryption key")
        print(f"[ACTION] Add this to your .env file:")
        print(f"COOKIE_ENCRYPTION_KEY={key}")
        return key.encode()
    return key.encode()

def encrypt_data(data, key):
    """Encrypt data using Fernet"""
    f = Fernet(key)
    json_str = json.dumps(data)
    encrypted = f.encrypt(json_str.encode())
    return encrypted

def decrypt_data(encrypted_data, key):
    """Decrypt data using Fernet"""
    try:
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    except Exception as e:
        print(f"[ERROR] Decryption failed: {e}")
        return None

def save_cookies_encrypted(cookies, key):
    """Save cookies in encrypted format"""
    try:
        encrypted = encrypt_data(cookies, key)
        with open(COOKIES_FILE, 'wb') as f:
            f.write(encrypted)
        print(f"[OK] Cookies saved securely (encrypted)")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save cookies: {e}")
        return False

def load_cookies_encrypted(key):
    """Load cookies from encrypted file"""
    cookie_path = os.path.join(BASE_PATH, COOKIES_FILE)
    
    # Try encrypted file first
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, 'rb') as f:
                encrypted_data = f.read()
            cookies = decrypt_data(encrypted_data, key)
            if cookies:
                print(f"[OK] Loaded {len(cookies)} cookies from encrypted file")
                return cookies
        except Exception as e:
            print(f"[ERROR] Failed to load encrypted cookies: {e}")
    
    # Fallback: try plain text cookies.json (for migration)
    plain_cookie_path = os.path.join(BASE_PATH, "cookies.json")
    if os.path.exists(plain_cookie_path):
        print(f"[WARNING] Found plain text cookies.json - migrating to encrypted format...")
        try:
            with open(plain_cookie_path, 'r') as f:
                cookies = json.load(f)
            # Save as encrypted
            save_cookies_encrypted(cookies, key)
            # Delete plain text file for security
            os.remove(plain_cookie_path)
            print(f"[OK] Migrated cookies to encrypted format and deleted plain text file")
            return cookies
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
    
    print(f"[WARNING] No cookie file found")
    return None

def inject_cookies(driver, cookies):
    """Inject cookies into browser session"""
    if not cookies:
        return False
    
    try:
        for cookie in cookies:
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
        print(f"[ERROR] Failed to inject cookies: {e}")
        return False

# Browser Setup
edge_options = Options()
edge_options.add_argument('--ignore-certificate-errors')
edge_options.add_argument('--disable-gpu')
edge_options.add_argument('--no-sandbox')
edge_options.add_argument('--start-maximized')
edge_options.add_argument('--disable-blink-features=AutomationControlled')

# Find msedge.exe
possible_bins = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
for p in possible_bins:
    if os.path.exists(p):
        edge_options.binary_location = p
        break

# LAUNCH EDGE
print("\n" + "="*60)
print("STEP 1: LAUNCHING EDGE")
print("="*60)

driver = None

try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)
    driver.implicitly_wait(10)
    print('[OK] ChromeDriver started!')
except Exception as e:
    print(f"[ERROR] Failed to start Chrome: {e}")
    exit(1)

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
        return True
    except:
        return False

def attempt_login(driver, username, password):
    """Attempt login"""
    wait = WebDriverWait(driver, 15)
    try:
        time.sleep(2)
        user_el = None
        for by, sel in [(By.CSS_SELECTOR, "input[name='username']"), (By.CSS_SELECTOR, "input[type='text']")]:
            try:
                user_el = wait.until(EC.presence_of_element_located((by, sel)))
                break
            except: continue
        
        pass_el = None
        for by, sel in [(By.CSS_SELECTOR, "input[name='password']"), (By.CSS_SELECTOR, "input[type='password']")]:
            try:
                pass_el = wait.until(EC.presence_of_element_located((by, sel)))
                break
            except: continue
        
        if not user_el or not pass_el:
            return False
        
        user_el.clear()
        user_el.send_keys(username)
        time.sleep(1)
        pass_el.clear()
        pass_el.send_keys(password)
        time.sleep(1.5)
        
        for by, sel in [(By.CSS_SELECTOR, "button[type='submit']"), (By.CSS_SELECTOR, "input[type='submit']")]:
            try:
                btn = wait.until(EC.element_to_be_clickable((by, sel)))
                btn.click()
                break
            except: continue
        else:
            pass_el.send_keys('\n')
        
        time.sleep(4)
        return True
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return False

def scroll_and_load_table(driver, max_attempts=20):
    """Scroll table to load all data"""
    print("[INFO] Scrolling table...")
    try:
        time.sleep(2)
        table_container = None
        for selector in ["div.dataTables_scrollBody", "div[class*='table-scroll']", "div[style*='overflow']"]:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    sh = driver.execute_script("return arguments[0].scrollHeight;", elem)
                    ch = driver.execute_script("return arguments[0].clientHeight;", elem)
                    if sh > ch:
                        table_container = elem
                        print(f"[OK] Found scrollable table")
                        break
                if table_container: break
            except: continue
        
        if not table_container:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            return True
        
        last_scroll = 0
        no_change = 0
        for attempt in range(max_attempts):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", table_container)
            time.sleep(1.0)
            new_scroll = driver.execute_script("return arguments[0].scrollTop;", table_container)
            
            if new_scroll == last_scroll:
                no_change += 1
                if no_change >= 3:
                    break
            else:
                no_change = 0
            last_scroll = new_scroll
        
        driver.execute_script("arguments[0].scrollTop = 0;", table_container)
        time.sleep(1)
        print("[OK] Table loaded")
        return True
    except Exception as e:
        print(f"[ERROR] Scroll error: {e}")
        return False

def main():
    global driver
    
    if not os.path.exists("id_aset.txt"):
        print("[ERROR] id_aset.txt not found!")
        if driver: driver.quit()
        return

    with open("id_aset.txt", "r") as f:
        asset_ids = [line.strip() for line in f if line.strip()]

    all_data = []
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    excel_filename = f"Inventory_Master_Software_{timestamp}.xlsx"

    print("\n" + "="*60)
    print("STEP 2: SECURE AUTHENTICATION")
    print("="*60)
    
    # Get encryption key
    encryption_key = get_encryption_key()
    
    # Load encrypted cookies
    cookies = load_cookies_encrypted(encryption_key)
    
    # Navigate to domain
    print("\n[INFO] Navigating to domain...")
    try:
        driver.get(LOGIN_URL)
        time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Navigation failed: {e}")
    
    # Inject cookies if available
    if cookies:
        print("[INFO] Injecting encrypted cookies...")
        if inject_cookies(driver, cookies):
            driver.refresh()
            time.sleep(3)
            if is_logged_in(driver):
                print("[OK] Authenticated via encrypted cookies!")
            else:
                cookies = None
    
    # Fallback to credentials
    if not cookies or not is_logged_in(driver):
        if USERNAME and PASSWORD:
            print('[INFO] Using credentials from environment...')
            attempt_login(driver, USERNAME, PASSWORD)
        
        if not is_logged_in(driver):
            print('[ACTION] MANUAL LOGIN required, then press [ENTER]')
            input('Press [ENTER] after login...')
    
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
                    print(f"\n[RETRY {retry_count}/{max_retries}] Asset: {aid}")
                else:
                    print(f"\n[{index}/{len(asset_ids)}] Processing: {aid}")
                
                driver.get(url)
                time.sleep(5)
                
                if not is_logged_in(driver):
                    print("[INFO] Session expired...")
                    if USERNAME and PASSWORD: 
                        attempt_login(driver, USERNAME, PASSWORD)
                    else: 
                        input("Login manually then press Enter...")
                    driver.get(url)
                    time.sleep(5)
                
                page_source_lower = driver.page_source.lower()
                if any(k in page_source_lower for k in ['no data', 'no records', 'empty']):
                     print(f"[INFO] Asset {aid} is empty")
                     success = True
                     break

                has_table = len(driver.find_elements(By.TAG_NAME, "table")) > 0
                if not has_table:
                    if retry_count >= max_retries:
                        print(f"[WARNING] Skipping {aid}")
                        success = True 
                        break
                    retry_count += 1
                    time.sleep(5)
                    continue

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
                        print(f"[OK] {len(df)} rows")
                        success = True
                    else:
                        success = True
                else:
                    retry_count += 1

            except Exception as e:
                print(f"[ERROR] {aid}: {e}")
                retry_count += 1
                time.sleep(5)
        
        if index % 10 == 0 and all_data:
            temp_df = pd.concat(all_data, ignore_index=True)
            temp_df.to_excel(excel_filename, index=False)
            print(f"[AUTOSAVE] {excel_filename}")

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_excel(excel_filename, index=False)
        print(f"\n{'='*60}")
        print(f"[SUCCESS] COMPLETE!")
        print(f"Assets: {len(asset_ids)} | Rows: {len(final_df)}")
        print(f"File: {excel_filename}")
        print(f"{'='*60}")
    else:
        print("\n[WARNING] No data extracted")
    
    print("\n[INFO] Closing browser...")
    if driver: driver.quit()
    print("[OK] Done!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user")
        try: driver.quit()
        except: pass
    except Exception as e:
        print(f"\n[ERROR] {e}")
        try: driver.quit()
        except: pass
