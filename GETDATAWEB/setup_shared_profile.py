import os
import shutil
import psutil

# --- CONFIG ---
SYSTEM_EDGE_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
PROJECT_EDGE_USER_DATA = r"C:\Users\200248\Documents\GETDATAWEB\GETDATAWEB\Edge User Data"
PROFILE_NAME = "Default"

def kill_edge():
    print("[INFO] Closing Microsoft Edge to copy profile...")
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'msedge.exe':
            try: proc.kill()
            except: pass

def setup():
    if not os.path.exists(SYSTEM_EDGE_USER_DATA):
        print(f"[ERROR] Edge system path not found: {SYSTEM_EDGE_USER_DATA}")
        return

    src = os.path.join(SYSTEM_EDGE_USER_DATA, PROFILE_NAME)
    dst = os.path.join(PROJECT_EDGE_USER_DATA, PROFILE_NAME)

    if not os.path.exists(src):
        print(f"[ERROR] Profile {PROFILE_NAME} not found in system Edge.")
        return

    print(f"[INFO] Copying {PROFILE_NAME} from Edge to project directory...")
    kill_edge()
    
    # Copy Local State (Important for profiles)
    os.makedirs(PROJECT_EDGE_USER_DATA, exist_ok=True)
    shutil.copy2(os.path.join(SYSTEM_EDGE_USER_DATA, "Local State"), 
                 os.path.join(PROJECT_EDGE_USER_DATA, "Local State"))

    # Copy Profile folder
    if os.path.exists(dst):
        print("[INFO] Deleting existing project profile...")
        shutil.rmtree(dst)
    
    # We only need essential files for login session to keep it small
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('Cache*', 'Code Cache', 'GPUCache'))
    
    print("\n" + "="*40)
    print("SETUP COMPLETE!")
    print(f"Source of Truth Profile: {dst}")
    print("Sekarang Anda bisa menjalankan run_parallel.bat")
    print("="*40)

if __name__ == "__main__":
    setup()
