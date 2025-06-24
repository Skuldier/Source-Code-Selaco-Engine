#!/usr/bin/env python3
"""
Verify and fix Archipelago initialization in Selaco engine
Ensures AP_Init() is called at the right time during engine startup
"""

import os
import sys
import re

def find_main_init_files(src_dir):
    """Find main engine initialization files"""
    init_files = []
    patterns = [
        'd_main.cpp',
        'g_game.cpp',
        'main.cpp',
        'engine.cpp',
        'startup.cpp'
    ]
    
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if any(file.endswith(pattern) for pattern in patterns):
                init_files.append(os.path.join(root, file))
    
    return init_files

def check_archipelago_init(filepath):
    """Check if AP_Init is called in the file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for AP_Init call
    if 'AP_Init' in content or 'Archipelago::AP_Init' in content:
        print(f"✓ Found AP_Init call in {filepath}")
        
        # Find context around the call
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'AP_Init' in line:
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                print("  Context:")
                for j in range(start, end):
                    marker = ">>>" if j == i else "   "
                    print(f"  {marker} {lines[j]}")
                print()
        return True
    
    return False

def add_archipelago_init(filepath, init_location="after_network"):
    """Add AP_Init call to appropriate location in file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # First check if we need to add the include
    if 'archipelago' not in content.lower():
        # Find where includes are
        include_match = re.search(r'(#include\s+[<"][^>"]+[>"][^\n]*\n)+', content)
        if include_match:
            include_end = include_match.end()
            # Add archipelago include
            new_include = '#include "archipelago/archipelago_client.h"\n'
            content = content[:include_end] + new_include + content[include_end:]
            print(f"  Added include: {new_include.strip()}")
    
    # Now find where to add AP_Init
    init_added = False
    
    # Look for network initialization as a good place to init archipelago
    network_patterns = [
        r'D_CheckNetGame\s*\(\s*\)',
        r'Net_Init\s*\(\s*\)',
        r'InitNetworking\s*\(\s*\)',
        r'I_InitNetwork\s*\(\s*\)'
    ]
    
    for pattern in network_patterns:
        match = re.search(pattern + r'[^;]*;', content)
        if match:
            insert_pos = match.end()
            # Add archipelago init after network init
            init_code = '\n\n\t// Initialize Archipelago client\n\tArchipelago::AP_Init();\n'
            content = content[:insert_pos] + init_code + content[insert_pos:]
            init_added = True
            print(f"  Added AP_Init after {pattern}")
            break
    
    if not init_added:
        # Try to find a general initialization section
        init_patterns = [
            r'// Initialize.*\n',
            r'Printf\s*\(\s*".*[Ii]nitializ.*"\s*\)',
            r'V_Init2?\s*\(\s*\)',
            r'S_Init\s*\(\s*\)'
        ]
        
        for pattern in init_patterns:
            match = re.search(pattern, content)
            if match:
                insert_pos = match.end()
                while insert_pos < len(content) and content[insert_pos] in '\n\r':
                    insert_pos += 1
                
                init_code = '\n\t// Initialize Archipelago client\n\tArchipelago::AP_Init();\n'
                content = content[:insert_pos] + init_code + content[insert_pos:]
                init_added = True
                print(f"  Added AP_Init after {pattern}")
                break
    
    if init_added:
        return content
    else:
        print(f"  ⚠ Could not find suitable location for AP_Init in {filepath}")
        return None

def create_init_patch(src_dir):
    """Create a patch file for initialization"""
    patch_content = """// Add this to d_main.cpp or your main initialization file
// Place it after network initialization but before game loop starts

#include "archipelago/archipelago_client.h"

// In your initialization function (like D_DoomMain or similar):
void InitializeEngine() {
    // ... existing initialization code ...
    
    // After network initialization:
    D_CheckNetGame();
    
    // Initialize Archipelago client
    Printf("Initializing Archipelago support...\\n");
    Archipelago::AP_Init();
    
    // ... rest of initialization ...
}

// Also ensure cleanup in shutdown:
void ShutdownEngine() {
    // ... existing shutdown code ...
    
    // Shutdown Archipelago
    Archipelago::AP_Shutdown();
    
    // ... rest of shutdown ...
}
"""
    
    patch_file = os.path.join(src_dir, "archipelago_init_patch.txt")
    with open(patch_file, 'w') as f:
        f.write(patch_content)
    
    print(f"\n✓ Created initialization patch template: {patch_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_archipelago_init.py <path_to_src_directory>")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    
    print(f"Searching for initialization files in {src_dir}...")
    init_files = find_main_init_files(src_dir)
    
    if not init_files:
        print("No initialization files found!")
        sys.exit(1)
    
    print(f"\nFound {len(init_files)} potential initialization files:")
    for f in init_files:
        print(f"  - {f}")
    
    print("\nChecking for Archipelago initialization...")
    found_init = False
    
    for init_file in init_files:
        if check_archipelago_init(init_file):
            found_init = True
    
    if not found_init:
        print("\n⚠ AP_Init not found in any initialization files!")
        print("\nWould you like to see where it should be added? (y/n): ", end='')
        
        # For automated script, we'll analyze d_main.cpp
        d_main = next((f for f in init_files if 'd_main.cpp' in f), None)
        if d_main:
            print(f"\nAnalyzing {d_main} for suitable init location...")
            with open(d_main, 'r') as f:
                content = f.read()
                
            # Show where network init happens
            if 'D_CheckNetGame' in content:
                print("✓ Found D_CheckNetGame - AP_Init should be called after this")
            
            # Create a patch file
            create_init_patch(os.path.dirname(d_main))
    
    print("\n=== Initialization Order Summary ===")
    print("1. Engine starts up")
    print("2. Basic systems initialized (video, sound, etc.)")
    print("3. Network initialized (D_CheckNetGame)")
    print("4. >>> Archipelago::AP_Init() should be called here <<<")
    print("5. Game loop starts")
    print("\nMake sure AP_Init is called AFTER network init but BEFORE the game loop!")

if __name__ == "__main__":
    main()