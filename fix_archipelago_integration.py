#!/usr/bin/env python3
"""
Fix Archipelago integration in Selaco - Link library and initialize properly
"""

import os
import re
import shutil
from datetime import datetime

def fix_cmake_linking(src_dir):
    """Fix CMakeLists.txt to link archipelago_websocket to zdoom"""
    cmake_path = os.path.join(src_dir, "src", "CMakeLists.txt")
    
    print("🔧 Fixing CMake linking...")
    
    if not os.path.exists(cmake_path):
        print(f"❌ CMakeLists.txt not found at {cmake_path}")
        return False
    
    # Backup
    backup_path = cmake_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(cmake_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Read content
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the target_link_libraries line for zdoom
    pattern = r'(target_link_libraries\s*\(\s*zdoom\s+.*?)(\s*\))'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("❌ Could not find target_link_libraries for zdoom")
        return False
    
    # Check if archipelago_websocket is already linked
    if 'archipelago_websocket' in match.group(0):
        print("✅ archipelago_websocket already linked")
    else:
        # Add archipelago_websocket to the link libraries
        new_link = match.group(1) + ' archipelago_websocket' + match.group(2)
        content = content[:match.start()] + new_link + content[match.end():]
        print("✅ Added archipelago_websocket to zdoom link libraries")
    
    # Write the fixed content
    with open(cmake_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def fix_ap_init_call(src_dir):
    """Fix AP_Init() call in d_main.cpp"""
    dmain_path = os.path.join(src_dir, "src", "d_main.cpp")
    
    print("\n🔧 Fixing AP_Init() call...")
    
    if not os.path.exists(dmain_path):
        print(f"❌ d_main.cpp not found at {dmain_path}")
        return False
    
    # Backup
    backup_path = dmain_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(dmain_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Read content
    with open(dmain_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove the floating AP_Init() call
    content = re.sub(r'\n// Initialize Archipelago support\nArchipelago::AP_Init\(\);\n', '\n', content)
    
    # Find where to properly call AP_Init() - after V_Init2() or similar initialization
    # Look for the startup sequence where other systems are initialized
    init_pattern = r'(V_Init2\s*\(\s*\);)'
    match = re.search(init_pattern, content)
    
    if match:
        # Check if AP_Init is already called properly
        check_area = content[match.end():match.end() + 500]
        if 'Archipelago::AP_Init()' not in check_area:
            # Add AP_Init after V_Init2
            insert_pos = match.end()
            init_call = '\n\n\t// Initialize Archipelago support\n\tArchipelago::AP_Init();'
            content = content[:insert_pos] + init_call + content[insert_pos:]
            print("✅ Added AP_Init() call after V_Init2()")
        else:
            print("✅ AP_Init() already called properly")
    else:
        # Alternative: Look for CT_Init() as another initialization point
        alt_pattern = r'(CT_Init\s*\(\s*\);)'
        alt_match = re.search(alt_pattern, content)
        if alt_match:
            check_area = content[alt_match.end():alt_match.end() + 500]
            if 'Archipelago::AP_Init()' not in check_area:
                insert_pos = alt_match.end()
                init_call = '\n\n\t// Initialize Archipelago support\n\tArchipelago::AP_Init();'
                content = content[:insert_pos] + init_call + content[insert_pos:]
                print("✅ Added AP_Init() call after CT_Init()")
    
    # Also need to add AP_Update() to the game loop
    # Look for D_DoomLoop or similar
    loop_pattern = r'(void\s+D_DoomLoop\s*\(\s*\)[^{]*{[^}]*while[^{]*{)'
    loop_match = re.search(loop_pattern, content, re.DOTALL)
    
    if loop_match:
        # Check if AP_Update is already called
        loop_end = content.find('}', loop_match.end())
        loop_area = content[loop_match.end():loop_end]
        if 'Archipelago::AP_Update()' not in loop_area:
            # Find a good place to add AP_Update - after D_ProcessEvents or similar
            event_pattern = r'(D_ProcessEvents\s*\(\s*\);)'
            event_match = re.search(event_pattern, loop_area)
            if event_match:
                insert_offset = loop_match.end() + event_match.end()
                update_call = '\n\t\t\t// Update Archipelago\n\t\t\tArchipelago::AP_Update();'
                content = content[:insert_offset] + update_call + content[insert_offset:]
                print("✅ Added AP_Update() call in game loop")
    
    # Write the fixed content
    with open(dmain_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    import sys
    
    if len(sys.argv) < 2:
        # Use default path or prompt
        root_dir = input("Enter the path to Selaco source directory: ").strip()
        if not root_dir:
            root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
    else:
        root_dir = sys.argv[1]
    
    if not os.path.exists(root_dir):
        print(f"❌ Directory not found: {root_dir}")
        return
    
    print(f"🔍 Working on: {root_dir}")
    
    # Fix CMake linking
    if not fix_cmake_linking(root_dir):
        print("❌ Failed to fix CMake linking")
        return
    
    # Fix AP_Init call
    if not fix_ap_init_call(root_dir):
        print("❌ Failed to fix AP_Init call")
        return
    
    print("\n✅ All fixes applied successfully!")
    print("\n📝 Next steps:")
    print("1. Rebuild the project:")
    print("   cd build")
    print("   cmake --build . --config Debug")
    print("\n2. Run Selaco and test the commands:")
    print("   - ap_test")
    print("   - ap_connect localhost")
    print("   - ap_status")

if __name__ == "__main__":
    main()