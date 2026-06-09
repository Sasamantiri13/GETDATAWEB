import os
import glob
import time
import pandas as pd
from datetime import datetime

def check_health():
    # Placeholder for health check logic
    pass

def monitor():
    print("MONITORING PROGRESS (Press Ctrl+C to stop)")
    print("="*50)
    
    target_count = 1000 # Estimasi total
    
    while True:
        try:
            files = glob.glob("result_p*.csv")
            total_rows = 0
            details = []
            
            for f in sorted(files):
                try:
                    # Count rows without loading full file for speed
                    with open(f, 'r', encoding='utf-8') as file:
                        count = sum(1 for line in file) - 1 # Subtract header
                        total_rows += max(0, count)
                        details.append(f"{os.path.basename(f)}: {max(0, count)} rows")
                except: pass
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"TIME: {datetime.now().strftime('%H:%M:%S')}")
            print(f"TOTAL PROGRESS: {total_rows} / {target_count} ({ (total_rows/target_count)*100:.1f}%)")
            print("-" * 30)
            for d in details:
                print(d)
            
            print("\n[INFO] Jika progress berhenti lama, cek jendela script-nya.")
            time.sleep(10)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    monitor()
