import json
import hashlib
import multiprocessing as mp
from collections import defaultdict
import os
import pdb
from typing import Dict, List, Tuple

def hash_text(text: str) -> str:
    """Create SHA-256 hash of text for efficient comparison."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def extract_first_segment(text: str) -> str:
    """Extract the first segment before 'And the following is the action sequence if any actions have happened'."""
    break_phrase = "And the following is the action sequence if any actions have happened"
    if break_phrase in text:
        return text.split(break_phrase)[0].strip()
    return text

def process_file(file_path: str) -> List[Tuple[str, str, int]]:
    """Process a single JSON file and return (hash, text, index) tuples."""
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for idx, entry in enumerate(data):
            if isinstance(entry, dict) and 'text' in entry:
                full_text = entry['text']
                # Extract only the first segment for comparison
                # first_segment = extract_first_segment(full_text)
                first_segment = full_text
                text_hash = hash_text(first_segment)
                results.append((text_hash, first_segment, idx))
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return results

def find_duplicates_across_files(file_paths: List[str]) -> Dict[str, List[Tuple[str, int]]]:
    """Find duplicate texts across multiple JSON files using multiprocessing."""
    print(f"Processing {len(file_paths)} files...")
    
    # Process files in parallel
    with mp.Pool() as pool:
        results = pool.map(process_file, file_paths)
    
    # Build hash index with file sources
    hash_to_sources = defaultdict(list)
    
    for file_idx, file_results in enumerate(results):
        file_path = file_paths[file_idx]
        for text_hash, text, entry_idx in file_results:
            hash_to_sources[text_hash].append((file_path, entry_idx, text))
    
    # Find duplicates (hashes that appear in multiple sources)
    duplicates = {}
    for text_hash, sources in hash_to_sources.items():
        if len(sources) > 1:
            # Verify actual text matches (handle potential hash collisions)
            text_groups = defaultdict(list)
            for file_path, entry_idx, text in sources:
                text_groups[text].append((file_path, entry_idx))
            
            # Only keep groups with actual duplicates
            for text, locations in text_groups.items():
                if len(locations) > 1:
                    if text_hash not in duplicates:
                        duplicates[text_hash] = {}
                    duplicates[text_hash][text] = locations
    
    return duplicates

def analyze_test_train_overlap(duplicates: Dict[str, Dict[str, List[Tuple[str, int]]]], file_paths: List[str]):
    """Analyze how many test entries appear in train files."""
    # Count total entries in each file
    file_counts = {}
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                file_counts[file_path] = len(data)
        except Exception as e:
            print(f"Error counting entries in {file_path}: {e}")
            file_counts[file_path] = 0
    
    # Track overlaps between test and train files
    test_in_train_count = 0
    train_in_test_count = 0
    
    for hash_key, text_groups in duplicates.items():
        for text, locations in text_groups.items():
            # Check if this duplicate spans test and train files
            test_files = [loc for loc in locations if 'test' in os.path.basename(loc[0])]
            train_files = [loc for loc in locations if 'train' in os.path.basename(loc[0])]
            
            if test_files and train_files:
                test_in_train_count += len(test_files)
                train_in_test_count += len(train_files)
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("OVERLAP ANALYSIS SUMMARY")
    print("=" * 80)
    
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        count = file_counts[file_path]
        print(f"{filename}: {count:,} total entries")
    
    print(f"\nTest entries found in train files: {test_in_train_count}")
    print(f"Train entries found in test files: {train_in_test_count}")
    
    # Calculate percentages
    total_test_entries = sum(file_counts[f] for f in file_paths if 'test' in os.path.basename(f))
    total_train_entries = sum(file_counts[f] for f in file_paths if 'train' in os.path.basename(f))
    
    if total_test_entries > 0:
        test_overlap_pct = (test_in_train_count / total_test_entries) * 100
        print(f"Percentage of test entries in train: {test_overlap_pct:.2f}%")
    
    if total_train_entries > 0:
        train_overlap_pct = (train_in_test_count / total_train_entries) * 100
        print(f"Percentage of train entries in test: {train_overlap_pct:.2f}%")

def print_duplicates(duplicates: Dict[str, Dict[str, List[Tuple[str, int]]]], file_paths: List[str]):
    """Print found duplicates in a readable format."""
    if not duplicates:
        print("No duplicates found!")
        return
    
    # First show the overlap analysis
    analyze_test_train_overlap(duplicates, file_paths)
    
    print(f"\nFound {len(duplicates)} duplicate text groups:")
    print("=" * 80)
    
    for hash_key, text_groups in duplicates.items():
        for text, locations in text_groups.items():
            print(f"\nDuplicate text found in {len(locations)} locations:")
            print(f"Hash: {hash_key[:16]}...")
            print(f"Text preview: {text[:100]}...")
            
            for file_path, entry_idx in locations:
                filename = os.path.basename(file_path)
                print(f"  - {filename}: entry {entry_idx}")
            
            # Trigger debugger when duplicates are found
            pdb.set_trace()
            print("-" * 40)

if __name__ == "__main__":
    # Define all JSON files to check
    json_files = [
        "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_pretrain_test.json",
        "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_pretrain_train.json",
    ]
    
    # Filter to only existing files
    existing_files = [f for f in json_files if os.path.exists(f)]
    
    if not existing_files:
        print("No JSON files found!")
        exit(1)
    
    print(f"Checking for duplicates across {len(existing_files)} files:")
    for f in existing_files:
        print(f"  - {os.path.basename(f)}")
    
    # Find duplicates
    duplicates = find_duplicates_across_files(existing_files)
    
    # Print results
    print_duplicates(duplicates, existing_files)