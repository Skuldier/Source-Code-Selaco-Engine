#!/usr/bin/env python3
"""
Patch to add Net_ProcessArchipelago declaration to d_net.h or create it if missing.
This ensures the function is properly declared for use in other files.
"""

import re
import os
import sys

def patch_d_net_header(src_dir):
    """Add Net_ProcessArchipelago declaration to d_net.h"""
    
    header_path = os.path.join(src_dir, 'd_net.h')
    cpp_path = os.path.join(src_dir, 'd_net.cpp')
    
    # Check if d_net.h exists
    if os.path.exists(header_path):
        print(f"Found {header_path}")
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # Check if declaration already exists
        if 'Net_ProcessArchipelago' not in content:
            # Find a good place to add it - typically with other function declarations
            # Look for other void function declarations
            func_pattern = r'((?:^|\n)void\s+\w+\s*\([^)]*\)\s*;)'
            matches = list(re.finditer(func_pattern, content, re.MULTILINE))
            
            if matches:
                # Add after the last void function declaration
                insert_pos = matches[-1].end()
                content = content[:insert_pos] + '\nvoid Net_ProcessArchipelago();\n' + content[insert_pos:]
                print("✓ Added Net_ProcessArchipelago declaration to d_net.h")
            else:
                # No void functions found, look for any function declarations
                any_func_pattern = r'((?:^|\n)(?:int|bool|void)\s+\w+\s*\([^)]*\)\s*;)'
                matches = list(re.finditer(any_func_pattern, content, re.MULTILINE))
                
                if matches:
                    insert_pos = matches[-1].end()
                    content = content[:insert_pos] + '\nvoid Net_ProcessArchipelago();\n' + content[insert_pos:]
                    print("✓ Added Net_ProcessArchipelago declaration to d_net.h")
                else:
                    # Just add before the last #endif
                    endif_pattern = r'(#endif[^\n]*)\s*$'
                    match = re.search(endif_pattern, content)
                    if match:
                        insert_pos = match.start()
                        content = content[:insert_pos] + '\n// Archipelago integration\nvoid Net_ProcessArchipelago();\n\n' + content[insert_pos:]
                        print("✓ Added Net_ProcessArchipelago declaration before #endif")
            
            # Save the patched header
            if content != original_content:
                backup_path = header_path + '.backup'
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"✓ Created backup at {backup_path}")
                
                with open(header_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ Patched {header_path}")
                return True
        else:
            print("✓ Net_ProcessArchipelago declaration already exists in d_net.h")
            return True
    
    else:
        print(f"⚠ d_net.h not found, adding declaration to d_net.cpp instead")
        
        # If no header file, add declaration at the top of d_net.cpp
        if not os.path.exists(cpp_path):
            print(f"Error: {cpp_path} not found!")
            return False
        
        with open(cpp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # Check if we need to add the forward declaration
        if 'void Net_ProcessArchipelago();' not in content:
            # Add after includes but before first function
            include_end = 0
            include_pattern = r'(#include\s+[<"][^>"]+[>"](?:\s*//[^\n]*)?\s*\n)+'
            match = re.search(include_pattern, content)
            if match:
                include_end = match.end()
            
            # Look for extern declarations or global variables
            extern_pattern = r'((?:extern|static)\s+[^;]+;(?:\s*//[^\n]*)?\s*\n)+'
            match = re.search(extern_pattern, content[include_end:])
            if match:
                insert_pos = include_end + match.end()
            else:
                insert_pos = include_end
            
            # Add the declaration
            declaration = '\n// Forward declaration for Archipelago\nvoid Net_ProcessArchipelago();\n\n'
            content = content[:insert_pos] + declaration + content[insert_pos:]
            print("✓ Added Net_ProcessArchipelago declaration to d_net.cpp")
            
            # Save the file
            backup_path = cpp_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print(f"✓ Created backup at {backup_path}")
            
            with open(cpp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Patched {cpp_path}")
            return True
        else:
            print("✓ Net_ProcessArchipelago declaration already exists")
            return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_d_net_header_patch.py <src_directory>")
        print("Example: python fix_d_net_header_patch.py C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    if patch_d_net_header(src_dir):
        print("\n✅ Header/declaration patched successfully!")
        print("\nWhat this patch did:")
        print("1. Checked for d_net.h and added the function declaration")
        print("2. If no header file, added forward declaration to d_net.cpp")
        print("3. Ensured Net_ProcessArchipelago can be called from other files")
    else:
        print("\n❌ Failed to patch header/declaration")