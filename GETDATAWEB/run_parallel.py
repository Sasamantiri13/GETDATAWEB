import subprocess
import os
import time
import sys

# Configuration
INPUT_FILE = "id_aset.txt"
NUM_WORKERS = 6
SCRIPT_NAME = "tarik_data.py"

def split_workload():
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] {INPUT_FILE} not found!")
        return []

    with open(INPUT_FILE, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_items = len(lines)
    chunk_size = total_items // NUM_WORKERS + (1 if total_items % NUM_WORKERS > 0 else 0)
    
    chunks = []
    for i in range(NUM_WORKERS):
        start = i * chunk_size
        end = start + chunk_size
        chunk = lines[start:end]
        
        if not chunk:
            continue
            
        filename = f"id_aset_part_{i+1}.txt"
        with open(filename, "w") as f:
            f.write("\n".join(chunk))
        
        chunks.append(filename)
        print(f"[INFO] Created {filename} with {len(chunk)} items")
        
    return chunks

def main():
    print("="*60)
    print(f"STARTING PARALLEL EXTRACTION ({NUM_WORKERS} WORKERS)")
    print("="*60)

    # 1. Split workload
    chunk_files = split_workload()
    if not chunk_files:
        print("[ERROR] No chunks created.")
        return

    # 2. Launch workers
    processes = []
    for i, chunk_file in enumerate(chunk_files):
        worker_id = str(i + 1)
        # Using sys.executable to ensure the same Python environment is used
        cmd = [sys.executable, SCRIPT_NAME, "--input", chunk_file, "--id", worker_id]
        
        print(f"\n[LAUNCH] Worker {worker_id} processing {chunk_file}...")
        # Open separate console for each worker
        proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        processes.append(proc)
        
        if i < len(chunk_files) - 1:
             print(f"[WAIT] Waiting 5 seconds before launching next worker...")
             time.sleep(5)

    print("\n[INFO] All workers launched. Please perform login in each window.")
    print("[INFO] Waiting for all workers to complete activities...")
    
    # 3. Wait for all to finish
    for p in processes:
        p.wait()

    print("\n" + "="*60)
    print("ALL WORKERS FINISHED")
    print("="*60)

if __name__ == "__main__":
    main()
