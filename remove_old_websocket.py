#!/usr/bin/env python3
"""
Script to safely backup and remove the old WebSocket implementation
"""

import os
import shutil
import datetime

def backup_and_remove_old_implementation(src_dir):
    """Backup old files and prepare for new implementation"""
    
    # Create backup directory with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_websocket_{timestamp}"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Files to backup and remove
    old_files = [
        "src/archipelago/archipelago_client.cpp",
        "src/archipelago/archipelago_client.h",
        "src/archipelago/archipelago_ccmds.cpp"
    ]
    
    backed_up = []
    for file_path in old_files:
        if os.path.exists(file_path):
            # Create subdirectory structure in backup
            backup_path = os.path.join(backup_dir, file_path)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Copy file to backup
            shutil.copy2(file_path, backup_path)
            backed_up.append(file_path)
            
            # Remove original
            os.remove(file_path)
            print(f"✓ Backed up and removed: {file_path}")
    
    # Create backup info file
    with open(os.path.join(backup_dir, "backup_info.txt"), 'w') as f:
        f.write(f"WebSocket Implementation Backup\n")
        f.write(f"Created: {timestamp}\n")
        f.write(f"Files backed up:\n")
        for file in backed_up:
            f.write(f"  - {file}\n")
    
    print(f"\n✓ Backup created in: {backup_dir}")
    print(f"✓ Backed up {len(backed_up)} files")
    return backup_dir

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python remove_old_websocket.py <path_to_selaco_src>")
        sys.exit(1)
    
    src_path = sys.argv[1]
    if not os.path.exists(src_path):
        print(f"Error: Source path '{src_path}' does not exist")
        sys.exit(1)
    
    os.chdir(src_path)
    backup_and_remove_old_implementation(".")
    
    print("\n✓ Old implementation removed. Ready for new libwebsockets implementation!")