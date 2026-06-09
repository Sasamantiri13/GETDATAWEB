import pandas as pd
import glob
import os
from datetime import datetime

def merge_csvs():
    # Cari semua file result_p*.csv
    files = glob.glob("result_p*.csv")
    
    if not files:
        print("No result files found (result_p*.csv)")
        return

    print(f"Found {len(files)} files to merge: {files}")
    
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if not df.empty:
                dfs.append(df)
                print(f"Loaded {len(df)} rows from {f}")
        except Exception as e:
            print(f"Error loading {f}: {e}")

    if not dfs:
        print("No data found in files.")
        return

    final_df = pd.concat(dfs, ignore_index=True)
    # Remove duplicates if any
    initial_len = len(final_df)
    final_df = final_df.drop_duplicates()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"FINAL_DATA_1000_{timestamp}.csv"
    
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print("\n" + "="*40)
    print(f"MERGE COMPLETE!")
    print(f"Total Rows: {initial_len}")
    print(f"After Clean: {len(final_df)}")
    print(f"Result file: {output_file}")
    print("="*40)

if __name__ == "__main__":
    merge_csvs()
