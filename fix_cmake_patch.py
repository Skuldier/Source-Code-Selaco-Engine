#!/usr/bin/env python3
"""
Patch for CMakeLists.txt to ensure Archipelago sources are properly included in the build.
This verifies the ARCHIPELAGO_SOURCES are defined and added to the main executable.
"""

import re
import os
import sys

def patch_cmake_lists(filepath):
    """Fix CMakeLists.txt to properly include Archipelago sources"""
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    # Step 1: Check if ARCHIPELAGO_SOURCES is defined
    archipelago_sources_pattern = r'set\s*\(\s*ARCHIPELAGO_SOURCES[^)]+\)'
    match = re.search(archipelago_sources_pattern, content, re.DOTALL)
    
    if not match:
        print("⚠ ARCHIPELAGO_SOURCES not found, adding it...")
        
        # Find where other source sets are defined (like GAME_SOURCES)
        source_set_pattern = r'(set\s*\(\s*\w+_SOURCES[^)]+\))'
        matches = list(re.finditer(source_set_pattern, content, re.DOTALL))
        
        if matches:
            # Add after the last source set definition
            insert_pos = matches[-1].end()
            archipelago_sources = '''

# Archipelago integration
set( ARCHIPELAGO_SOURCES
	archipelago/archipelago_client.cpp
	archipelago/archipelago_client.h
	archipelago/easywsclient.cpp
	archipelago/easywsclient.hpp
	archipelago/archipelago_ccmds.cpp )
'''
            content = content[:insert_pos] + archipelago_sources + content[insert_pos:]
            print("✓ Added ARCHIPELAGO_SOURCES definition")
            changes_made = True
    else:
        print("✓ ARCHIPELAGO_SOURCES already defined")
        
        # Verify all required files are listed
        required_files = [
            'archipelago/archipelago_client.cpp',
            'archipelago/archipelago_client.h',
            'archipelago/easywsclient.cpp',
            'archipelago/easywsclient.hpp',
            'archipelago/archipelago_ccmds.cpp'
        ]
        
        sources_block = match.group(0)
        for file in required_files:
            if file not in sources_block:
                print(f"⚠ Missing {file} in ARCHIPELAGO_SOURCES")
                # Add it
                content = content[:match.end()-1] + f'\n\t{file}' + content[match.end()-1:]
                print(f"✓ Added {file}")
                changes_made = True
    
    # Step 2: Ensure ARCHIPELAGO_SOURCES is included in the executable
    # Look for add_executable
    exe_pattern = r'add_executable\s*\(\s*(\w+)([^)]+)\)'
    exe_match = re.search(exe_pattern, content, re.DOTALL)
    
    if exe_match:
        exe_name = exe_match.group(1)
        exe_sources = exe_match.group(2)
        
        if '${ARCHIPELAGO_SOURCES}' not in exe_sources and 'ARCHIPELAGO_SOURCES' not in exe_sources:
            print(f"⚠ ARCHIPELAGO_SOURCES not included in {exe_name} executable")
            
            # Add it after other source variables
            if '${GAME_SOURCES}' in exe_sources:
                content = content.replace(
                    '${GAME_SOURCES}',
                    '${GAME_SOURCES}\n\t${ARCHIPELAGO_SOURCES}'
                )
                print(f"✓ Added ARCHIPELAGO_SOURCES to {exe_name} executable")
                changes_made = True
            else:
                # Just add it at the end of the sources list
                insert_pos = exe_match.end() - 1
                content = content[:insert_pos] + '\n\t${ARCHIPELAGO_SOURCES}' + content[insert_pos:]
                print(f"✓ Added ARCHIPELAGO_SOURCES to {exe_name} executable")
                changes_made = True
        else:
            print(f"✓ ARCHIPELAGO_SOURCES already included in {exe_name} executable")
    
    # Step 3: Check for required dependencies
    # Archipelago might need additional libraries like websockets, json parsing, etc.
    if 'rapidjson' not in content.lower() and 'RAPIDJSON' not in content:
        print("\n⚠ Note: You may need to add RapidJSON to your project dependencies")
        print("  Consider adding: find_package(RapidJSON REQUIRED)")
    
    # Step 4: Check if we need to add include directories
    include_dir_pattern = r'target_include_directories\s*\([^)]+\)'
    if re.search(include_dir_pattern, content):
        # Check if archipelago directory is included
        if 'archipelago' not in content:
            print("\n⚠ Note: You may need to add archipelago to include directories")
            print("  Consider adding: target_include_directories(zdoom PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/archipelago)")
    
    # Save the patched file
    if changes_made:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"\n✓ Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Patched {filepath}")
        return True
    else:
        print("\n✓ CMakeLists.txt appears to be correctly configured")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_cmake_patch.py <path_to_CMakeLists.txt>")
        print("Example: python fix_cmake_patch.py C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/CMakeLists.txt")
        sys.exit(1)
    
    filepath = sys.argv[1]
    if patch_cmake_lists(filepath):
        print("\n✅ CMakeLists.txt verified/patched successfully!")
        print("\nWhat this patch did:")
        print("1. Ensured ARCHIPELAGO_SOURCES is properly defined")
        print("2. Verified all Archipelago source files are listed")
        print("3. Added ARCHIPELAGO_SOURCES to the main executable")
        print("4. Checked for potential dependency issues")
    else:
        print("\n❌ Failed to patch CMakeLists.txt")