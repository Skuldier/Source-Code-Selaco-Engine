#!/usr/bin/env python3
"""
Show exact locations where to add AP_Init()
"""

import os

def show_init_locations(src_dir):
    """Show exact line numbers and content for adding AP_Init"""
    dmain_path = os.path.join(src_dir, "src", "d_main.cpp")
    
    print(f"📄 Analyzing {dmain_path}")
    
    if not os.path.exists(dmain_path):
        print(f"❌ File not found!")
        return
    
    with open(dmain_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📊 Total lines: {len(lines)}")
    
    # Look for specific initialization calls
    init_calls = [
        ('V_Init2()', 'V_Init2'),
        ('CT_Init()', 'CT_Init'),
        ('I_InitSound', 'I_InitSound'),
        ('I_Init:', 'I_Init:'),
        ('atterm', 'atterm'),
        ('G_ParseMapInfo', 'G_ParseMapInfo'),
    ]
    
    found_locations = []
    
    print("\n🎯 Found initialization points:")
    print("="*70)
    
    for search_text, name in init_calls:
        for i, line in enumerate(lines):
            if search_text in line:
                found_locations.append((i, name, line.strip()))
                print(f"\n✅ {name} at line {i+1}:")
                print(f"   {line.strip()}")
                
                # Show context
                if i+1 < len(lines):
                    print(f"   Next line: {lines[i+1].strip()}")
                print(f"\n   👉 Add AP_Init() after line {i+1}")
    
    if found_locations:
        # Pick the best location
        best = found_locations[0]
        print("\n" + "="*70)
        print("💡 RECOMMENDED: Add after line", best[0]+1)
        print("="*70)
        print(f"\nEdit d_main.cpp and go to line {best[0]+1}:")
        print(f"Current line {best[0]+1}: {best[2]}")
        print("\nAdd these lines AFTER it:")
        print("    // Initialize Archipelago support")
        print("    Archipelago::AP_Init();")
        
        # Also check if include exists
        has_include = False
        for line in lines[:200]:  # Check first 200 lines
            if 'archipelago/archipelago_protocol.h' in line:
                has_include = True
                break
        
        if not has_include:
            print("\n⚠️  Also add at the top of the file:")
            print('#include "archipelago/archipelago_protocol.h"')
    else:
        print("\n❌ Could not find standard initialization points")
        print("Search manually for where other systems are initialized")

def main():
    import sys
    
    if len(sys.argv) < 2:
        root_dir = input("Enter the path to Selaco source directory: ").strip()
        if not root_dir:
            root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
    else:
        root_dir = sys.argv[1]
    
    if not os.path.exists(root_dir):
        print(f"❌ Directory not found: {root_dir}")
        return
    
    show_init_locations(root_dir)
    
    print("\n📝 After making the change:")
    print("1. Save the file")
    print("2. cd build")
    print("3. cmake --build . --config Debug")
    print("4. Test with ap_status command")

if __name__ == "__main__":
    main()