#!/usr/bin/env python3
"""
Comprehensive fix for Archipelago integration issues
"""

import os
import re
import shutil
from datetime import datetime

def fix_dmain_includes_and_init(src_dir):
    """Fix d_main.cpp to properly include and initialize Archipelago"""
    dmain_path = os.path.join(src_dir, "src", "d_main.cpp")
    
    print("🔧 Fixing d_main.cpp...")
    
    if not os.path.exists(dmain_path):
        print(f"❌ d_main.cpp not found at {dmain_path}")
        return False
    
    # Backup
    backup_path = dmain_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(dmain_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    with open(dmain_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # First, remove any floating AP_Init calls (not inside a function)
    new_lines = []
    i = 0
    removed_floating_init = False
    
    while i < len(lines):
        line = lines[i]
        # Check if this is a floating AP_Init call
        if 'AP_Init()' in line and i > 0:
            # Look back to see if we're inside a function
            # Simple heuristic: check if there's an opening brace before this
            in_function = False
            brace_count = 0
            for j in range(i-1, max(0, i-100), -1):
                if '{' in lines[j]:
                    brace_count += lines[j].count('{')
                if '}' in lines[j]:
                    brace_count -= lines[j].count('}')
                if brace_count > 0:
                    in_function = True
                    break
            
            if not in_function and 'bool D_CheckNetGame' not in line:
                # This looks like a floating call - skip it
                print(f"✅ Removed floating AP_Init call at line {i+1}")
                removed_floating_init = True
                i += 1
                continue
        
        new_lines.append(line)
        i += 1
    
    lines = new_lines
    
    # Now find the right place to add the include
    # Look for the include section
    include_added = False
    include_line = '#include "archipelago/archipelago_protocol.h"\n'
    
    # Check if already included
    for line in lines:
        if 'archipelago/archipelago_protocol.h' in line:
            include_added = True
            print("✅ archipelago_protocol.h already included")
            break
    
    if not include_added:
        # Find a good place to add it - after other local includes
        for i, line in enumerate(lines):
            # Look for local includes section
            if '#include "' in line and i < 200:  # Within first 200 lines
                # Find the end of the include block
                j = i
                while j < len(lines) and ('#include' in lines[j] or lines[j].strip() == ''):
                    j += 1
                # Insert before the blank line or next non-include line
                lines.insert(j, include_line)
                print(f"✅ Added archipelago_protocol.h include at line {j+1}")
                include_added = True
                break
        
        if not include_added:
            # Fallback: add after first include
            for i, line in enumerate(lines):
                if '#include' in line:
                    lines.insert(i+1, include_line)
                    print(f"✅ Added archipelago_protocol.h include at line {i+2}")
                    break
    
    # Now find D_DoomMain and add AP_Init after basic initialization
    init_added = False
    for i, line in enumerate(lines):
        if 'void D_DoomMain' in line:
            # Found D_DoomMain, look for a good place to add init
            # Look for V_Init2() or CT_Init() or similar
            for j in range(i, min(i + 500, len(lines))):
                if 'V_Init2()' in lines[j] or 'CT_Init()' in lines[j]:
                    # Check if AP_Init is already called nearby
                    already_called = False
                    for k in range(j, min(j + 20, len(lines))):
                        if 'AP_Init()' in lines[k]:
                            already_called = True
                            print("✅ AP_Init() already called in D_DoomMain")
                            break
                    
                    if not already_called:
                        # Add AP_Init after this line
                        indent = '\t'
                        if lines[j].startswith('\t\t'):
                            indent = '\t\t'
                        elif lines[j].startswith('    '):
                            indent = '    '
                        
                        init_call = f"{indent}// Initialize Archipelago support\n{indent}Archipelago::AP_Init();\n"
                        lines.insert(j + 1, init_call)
                        print(f"✅ Added AP_Init() call at line {j+2}")
                        init_added = True
                    break
                
                if init_added:
                    break
    
    # Write the fixed content
    with open(dmain_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_cmake_linking(src_dir):
    """Ensure archipelago_websocket is linked to zdoom"""
    cmake_path = os.path.join(src_dir, "src", "CMakeLists.txt")
    
    print("\n🔧 Fixing CMake configuration...")
    
    if not os.path.exists(cmake_path):
        print(f"❌ CMakeLists.txt not found at {cmake_path}")
        return False
    
    # Backup
    backup_path = cmake_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(cmake_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find target_link_libraries for zdoom
    link_pattern = r'(target_link_libraries\s*\(\s*zdoom\s+)(.*?)(\s*\))'
    match = re.search(link_pattern, content, re.DOTALL)
    
    if match:
        link_libs = match.group(2)
        if 'archipelago_websocket' not in link_libs:
            # Add archipelago_websocket
            new_link = match.group(1) + link_libs + ' archipelago_websocket' + match.group(3)
            content = content[:match.start()] + new_link + content[match.end():]
            print("✅ Added archipelago_websocket to zdoom link libraries")
        else:
            print("✅ archipelago_websocket already linked")
    else:
        print("❌ Could not find target_link_libraries for zdoom")
        return False
    
    # Write the fixed content
    with open(cmake_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def verify_files_exist(src_dir):
    """Verify all necessary Archipelago files exist"""
    print("\n🔍 Verifying Archipelago files...")
    
    required_files = [
        "src/archipelago/archipelago_protocol.h",
        "src/archipelago/archipelago_protocol.cpp",
        "src/archipelago/archipelago_commands.cpp",
        "src/archipelago/lws_client.h",
        "src/archipelago/lws_client.cpp"
    ]
    
    all_exist = True
    for file in required_files:
        path = os.path.join(src_dir, file)
        if os.path.exists(path):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} NOT FOUND")
            all_exist = False
    
    return all_exist

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
    
    print(f"🔍 Working on: {root_dir}\n")
    
    # Verify files exist
    if not verify_files_exist(root_dir):
        print("\n❌ Missing required files! Make sure all Archipelago files are in place.")
        return
    
    # Fix d_main.cpp
    if not fix_dmain_includes_and_init(root_dir):
        print("\n❌ Failed to fix d_main.cpp")
        return
    
    # Fix CMake
    if not fix_cmake_linking(root_dir):
        print("\n❌ Failed to fix CMake")
        return
    
    print("\n✅ All fixes applied successfully!")
    print("\n📝 Summary of changes:")
    print("1. Added #include \"archipelago/archipelago_protocol.h\" to d_main.cpp")
    print("2. Removed any floating AP_Init() calls")
    print("3. Added proper AP_Init() call inside D_DoomMain")
    print("4. Ensured archipelago_websocket is linked to zdoom")
    print("\n🔨 Next steps:")
    print("1. Clean rebuild:")
    print("   cd build")
    print("   cmake --build . --target clean")
    print("   cmake --build . --config Debug")
    print("\n2. Test the commands:")
    print("   - ap_test")
    print("   - ap_status")
    print("   - ap_connect localhost")

if __name__ == "__main__":
    main()