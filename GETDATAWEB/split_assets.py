import os

def split_file(filename, chunks=5):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found!")
        return

    with open(filename, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    total = len(lines)
    chunk_size = (total + chunks - 1) // chunks

    for i in range(chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, total)
        
        if start >= total:
            break
            
        chunk_lines = lines[start:end]
        out_file = f"id_aset_{i+1}.txt"
        
        with open(out_file, 'w') as f:
            f.write('\n'.join(chunk_lines))
        
        print(f"Created {out_file} with {len(chunk_lines)} IDs")

if __name__ == "__main__":
    split_file("id_aset.txt", 5)
