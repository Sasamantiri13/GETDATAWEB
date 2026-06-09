import pandas as pd
import time
import os
import io
import urllib3
import subprocess
import shutil
import tempfile
import argparse
import random
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

# --- KONFIGURASI ---
BASE_PATH = r"C:\Users\200248\Documents\GETDATAWEB\GETDATAWEB"
CHROME_USER_DATA = r"C:\Users\200248\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME = "Profile 6"  # Using Profile 6 as seen in backup files

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Verifikasi profil ada
profile_path = os.path.join(CHROME_USER_DATA, PROFILE_NAME)

def main(input_file, script_id, aggressive_cleanup=False):
    if not os.path.exists(input_file):
        print(f"[ERROR] {input_file} tidak ditemukan!")
        return

    with open(input_file, "r") as f:
        asset_ids = [line.strip() for line in f if line.strip()]
    
    print(f"\n[INFO] SCRIPT INSTANCE {script_id} STARTING")
    print(f"[INFO] Input file: {input_file}, Assets: {len(asset_ids)}")
    
    # Create Temp Profile
    temp_dir = tempfile.mkdtemp(prefix=f"chrome_p{script_id}_")
    source_profile = os.path.join(CHROME_USER_DATA, PROFILE_NAME)
    dest_profile = os.path.join(temp_dir, PROFILE_NAME)
    os.makedirs(dest_profile, exist_ok=True)
    
    # Copy necessary parts of profile
    local_state_src = os.path.join(CHROME_USER_DATA, "Local State")
    if os.path.exists(local_state_src):
        shutil.copy(local_state_src, os.path.join(temp_dir, "Local State"))
    shutil.copytree(source_profile, dest_profile, dirs_exist_ok=True, 
                    ignore=shutil.ignore_patterns('Cache*', 'Code Cache', 'GPUCache', 'Service Worker', 'blob_storage'))

    # Browser Setup
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    chrome_options.add_argument(f"--profile-directory={PROFILE_NAME}")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    
    possible_bins = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
    for p in possible_bins:
        if os.path.exists(p):
            chrome_options.binary_location = p
            break

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
    except Exception as e:
        print(f"[ERROR] Gagal membuka Google Chrome: {e}")
        return

    all_data = []
    inactive_assets = []  # List to store IDs of assets with no data

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Save to absolute path to avoid confusion
    csv_filename = os.path.join(BASE_PATH, f"result_p{script_id}_{timestamp}.csv")
    print(f"[INFO] Target CSV: {csv_filename}")
    
    LOGIN_URL = "https://dc-bmc-master.bfi.co.id:1611/webconsole/home"
    DEVICE_URL_TEMPLATE = "https://dc-bmc-master.bfi.co.id:1611/webconsole/device/{aid}/inventories?invindex=2&sortasc=true&standalone=false&sortparam=&cat=1"

    print("\n[INFO] Validating Session...")
    driver.get(LOGIN_URL)
    
    if "login" in driver.current_url.lower():
        print(f"[ACTION] SCRIPT {script_id}: Perlu login manual. Silakan login...")
        input(">>> TEKAN ENTER SETELAH LOGIN BERHASIL <<<")

    for i, aid in enumerate(asset_ids, 1):
        delay = random.uniform(2, 4)
        print(f"\n[{i}/{len(asset_ids)}] Asset {aid} (Delay {delay:.1f}s)...")
        time.sleep(delay)

        url = DEVICE_URL_TEMPLATE.format(aid=aid)
        try:
            driver.get(url)
            time.sleep(5)

            if "login" in driver.current_url.lower():
                print(f"[RE-LOGIN] Script {script_id} expired at {aid}")
                driver.get(LOGIN_URL)
                input(">>> SESSION EXPIRED. LOGIN ULANG DAN TEKAN ENTER <<<")
                driver.get(url)
                time.sleep(5)

            # --- ENHANCED SCROLLING FOR ui-table-tbody ---
            print(f"  [PROCESS] Scrolling table for {aid}...")
            
            def do_scroll():
                js_scroll = """
                var tbody = document.querySelector('tbody.ui-table-tbody');
                if (tbody) {
                    var container = tbody.closest('.ui-table-scrollable-body') || tbody.parentElement;
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                        return true;
                    }
                }
                window.scrollTo(0, document.body.scrollHeight);
                return false;
                """
                return driver.execute_script(js_scroll)

            def get_rows_count():
                return len(driver.find_elements(By.CSS_SELECTOR, "tbody.ui-table-tbody tr"))

            # Attempt scrolling up to 2 times to load table rows
            scroll_attempts = 0
            max_attempts = 2
            while scroll_attempts < max_attempts:
                do_scroll()
                time.sleep(2)
                current_count = get_rows_count()
                print(f"    [DEBUG] Attempt {scroll_attempts+1}: {current_count} rows found")
                if current_count > 0:
                    # Rows loaded, break out of scrolling loop
                    break
                scroll_attempts += 1
                        # After attempts, check if any rows were loaded
            if current_count == 0:
                print(f"[SKIP] Asset {aid} is non‑active (no table rows after {max_attempts} attempts). Skipping.")
                inactive_assets.append(aid)
                # Autosave current data before moving to next asset
                try:
                    if all_data:
                        final_df = pd.concat(all_data, ignore_index=True)
                        final_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                        print(f"[AUTOSAVE] Current total rows saved to {csv_filename} before skipping asset {aid}")
                    else:
                        print(f"[AUTOSAVE] No data yet to save before skipping asset {aid}.")
                except Exception as e:
                    print(f"[WARNING] Autosave failed before skipping asset {aid}: {e}")
                continue

            # --- EXTRACTION ---
            html = driver.page_source
            tables = pd.read_html(io.StringIO(html), flavor='html5lib')
            print(f"  [DEBUG] Tables detected by pandas: {len(tables)}")
            
            df = None
            valid = [t for t in tables if len(t) > 1]
            if valid:
                df = max(valid, key=lambda x: len(x))
                print(f"  [INFO] Pandas extracted {len(df)} rows.")
            else:
                print("  [WARN] Pandas missed the table structure. Trying Fallback...")
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, "tbody.ui-table-tbody tr")
                    if rows:
                        data_rows = []
                        for r in rows:
                            cells = r.find_elements(By.TAG_NAME, "td")
                            data_rows.append([c.text for c in cells])
                        
                        if data_rows:
                            df = pd.DataFrame(data_rows)
                            print(f"  [OK] Fallback extracted {len(df)} rows.")
                except Exception as ex:
                    print(f"  [ERROR] Fallback failed: {ex}")

            if df is not None:
                df.insert(0, 'Asset_ID', aid)
                all_data.append(df)
                print(f"  [OK] Total collected so far: {len(all_data)}")
            else:
                print("  [CRITICAL] No data was extracted for this asset.")

        except Exception as e:
            print(f"  [ERROR] Asset {aid}: {e}")
        
        # After each asset (including skipped ones) autosave current data
        try:
            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)
                final_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                print(f"[AUTOSAVE] Current total rows saved to {csv_filename}")
            else:
                print(f"[AUTOSAVE] No data yet to save for asset {aid}.")
        
        except Exception as e:
            print(f"[WARNING] Autosave failed after asset {aid}: {e}")
        # No skip_asset variable used; continue will happen automatically if needed

        

    if all_data:
        try:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n[DONE] Finished. Output: {csv_filename} ({len(final_df)} rows)")
        except Exception as e:
            print(f"\n[CRITICAL] Final save failed: {e}")
    else:
        print("\n[INFO] No data collected, CSV not created.")
    
    # After processing, write any inactive asset IDs to a file for reference
    if inactive_assets:
        inactive_path = os.path.join(BASE_PATH, "inactive_assets.txt")
        try:
            with open(inactive_path, "w") as f:
                for aid in inactive_assets:
                    f.write(str(aid) + "\n")
            print(f"[INFO] Inactive asset list saved to {inactive_path}")
        except Exception as e:
            print(f"[WARNING] Failed to write inactive asset file: {e}")
    driver.quit()
    try: shutil.rmtree(temp_dir)
    except: pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="id_aset.txt")
    parser.add_argument("--id", default="0")
    args = parser.parse_args()
    os.chdir(BASE_PATH)
    main(args.input, args.id)