#!/usr/bin/env python3
"""
Find where AP_* functions are called and add the necessary include
"""

import os
import re
import sys

def find_ap_function_calls(root_dir):
    """Find all files that call AP_Init, AP_Update, or AP_Shutdown"""
    
    print("🔍 Searching for AP_* function calls...")
    
    # Patterns to search for
    patterns = [
        r'\bAP_Init\s*\(',
        r'\bAP_Update\s*\(',
        r'\bAP_Shutdown\s*\('
    ]
    
    results = {}
    
    # Search in src directory
    src_dir = os.path.join(root_dir, "src")
    
    for root, dirs, files in os.walk(src_dir):
        # Skip archipelago directory itself
        if 'archipelago' in root:
            continue
            
        for file in files:
            if file.endswith(('.cpp', '.c', '.h')):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for pattern in patterns:
                        matches = list(re.finditer(pattern, content))
                        if matches:
                            if file_path not in results:
                                results[file_path] = []
                            for match in matches:
                                line_num = content[:match.start()].count('\n') + 1
                                func_name = match.group().replace('(', '').strip()
                                results[file_path].append((line_num, func_name))
                                
                except Exception as e:
                    pass
    
    return results

def add_include_to_file(file_path, include_line='#include "archipelago/archipelago.h"'):
    """Add include to a file if it doesn't already have it"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already included
    if 'archipelago.h' in content or 'archipelago_protocol.h' in content:
        print(f"  ✅ Already includes archipelago headers")
        return False
    
    # Find where to insert (after other includes)
    include_pattern = r'#include\s+[<"].*[>"]'
    includes = list(re.finditer(include_pattern, content))
    
    if includes:
        # Insert after last include
        last_include = includes[-1]
        insert_pos = last_include.end()
        
        # Find the newline after the last include
        newline_pos = content.find('\n', insert_pos)
        if newline_pos != -1:
            insert_pos = newline_pos + 1
        
        new_content = content[:insert_pos] + include_line + '\n' + content[insert_pos:]
    else:
        # No includes found, add at the beginning
        new_content = include_line + '\n\n' + content
    
    # Backup and write
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  ✅ Added include to {file_path}")
    return True

def main():
    if len(sys.argv) < 2:
        root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
        print(f"Using default path: {root_dir}")
    else:
        root_dir = sys.argv[1]
    
    # Find files with AP_* calls
    results = find_ap_function_calls(root_dir)
    
    if not results:
        print("❌ No AP_* function calls found!")
        return
    
    print(f"\n📋 Found AP_* function calls in {len(results)} files:\n")
    
    for file_path, calls in results.items():
        rel_path = os.path.relpath(file_path, root_dir)
        print(f"📄 {rel_path}")
        for line_num, func_name in calls:
            print(f"   Line {line_num}: {func_name}()")
    
    # Ask if user wants to add includes
    print("\n" + "="*50)
    response = input("\nAdd '#include \"archipelago/archipelago.h\"' to these files? (y/n): ")
    
    if response.lower() == 'y':
        # First create archipelago.h if it doesn't exist
        archipelago_h_path = os.path.join(root_dir, "src", "archipelago", "archipelago.h")
        if not os.path.exists(archipelago_h_path):
            print(f"\n📝 Creating {archipelago_h_path}...")
            with open(archipelago_h_path, 'w', encoding='utf-8') as f:
                f.write('''// archipelago.h - Main header for Archipelago integration
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Engine integration functions
void AP_Init(void);
void AP_Shutdown(void);
void AP_Update(void);

#ifdef __cplusplus
}
#endif
''')
            print("✅ Created archipelago.h")
        
        # Add includes to files
        print("\n📝 Adding includes...")
        for file_path in results:
            add_include_to_file(file_path)
        
        print("\n✅ Done! Now rebuild your project:")
        print("  cd build")
        print("  cmake --build . --config Release")
    else:
        print("\n📝 To fix manually, add this line to the files listed above:")
        print('  #include "archipelago/archipelago.h"')

if __name__ == "__main__":
    main()