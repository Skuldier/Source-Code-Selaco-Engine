#!/usr/bin/env python3
"""
Fix Printf declaration conflicts in archipelago_client.cpp
This script removes incorrect extern declarations and ensures proper includes.
"""

import re
import os
import sys
from pathlib import Path

def fix_archipelago_client_printf(filepath):
    """
    Fix Printf-related issues in archipelago_client.cpp:
    1. Remove any extern Printf declarations
    2. Fix include paths
    3. Ensure proper Printf header is included
    """
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    # Read the file content
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Step 1: Remove any extern Printf declarations
    # This regex matches various forms of extern Printf declarations
    extern_patterns = [
        # Match: extern void Printf(const char* format, ...);
        r'extern\s+void\s+Printf\s*\([^)]*\)\s*;',
        # Match: extern int Printf(const char* format, ...);
        r'extern\s+int\s+Printf\s*\([^)]*\)\s*;',
        # Match multiline declarations with comments
        r'//[^\n]*Console output[^\n]*\n\s*extern\s+\w+\s+Printf\s*\([^)]*\)\s*;',
        # Match any Printf extern declaration
        r'extern\s+\w+\s+Printf\s*\([^;]+;\s*'
    ]
    
    for pattern in extern_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
        for match in matches:
            # Remove the entire match including any preceding comment
            start = match.start()
            end = match.end()
            
            # Check if there's a comment line before the extern
            lines_before = content[:start].split('\n')
            if len(lines_before) >= 2 and lines_before[-2].strip().startswith('//'):
                # Include the comment line in the removal
                start = content.rfind('\n', 0, start - 1) + 1
            
            # Replace with empty string (removing the declaration)
            content = content[:start] + content[end:]
            changes_made.append(f"Removed extern Printf declaration at position {start}")
    
    # Step 2: Fix easywsclient include path if needed
    if '#include "easywsclient/easywsclient.hpp"' in content:
        content = content.replace(
            '#include "easywsclient/easywsclient.hpp"',
            '#include "easywsclient.hpp"'
        )
        changes_made.append("Fixed easywsclient.hpp include path")
    
    # Step 3: Ensure Printf header is included
    # Check if the correct Printf include exists
    printf_includes = [
        '../common/engine/printf.h',
        'common/engine/printf.h',
        'engine/printf.h'
    ]
    
    has_printf_include = any(inc in content for inc in printf_includes)
    
    if not has_printf_include:
        # Find where to add the include - after archipelago_client.h is ideal
        include_pattern = r'#include\s+"archipelago_client\.h"\s*\n'
        match = re.search(include_pattern, content)
        
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + '#include "../common/engine/printf.h"\n' + content[insert_pos:]
            changes_made.append("Added Printf header include after archipelago_client.h")
        else:
            # If archipelago_client.h not found, add after all includes
            # Find the last include statement
            last_include = None
            for match in re.finditer(r'#include\s+[<"][^>"]+[>"]\s*\n', content):
                last_include = match
            
            if last_include:
                insert_pos = last_include.end()
                content = content[:insert_pos] + '#include "../common/engine/printf.h"\n' + content[insert_pos:]
                changes_made.append("Added Printf header include after other includes")
    
    # Step 4: Clean up any duplicate blank lines that might have been created
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # Save the file if changes were made
    if content != original_content:
        # Create a backup
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"Created backup at: {backup_path}")
        
        # Write the fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully patched {filepath}")
        print("\nChanges made:")
        for change in changes_made:
            print(f"  - {change}")
        
        return True
    else:
        print("No changes needed - file appears to be already fixed")
        return False

def analyze_file(filepath):
    """
    Analyze the file to show what will be changed
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print("File Analysis:")
    print("-" * 60)
    
    # Check for extern Printf declarations
    extern_pattern = r'extern\s+\w+\s+Printf\s*\([^)]*\)\s*;'
    extern_matches = list(re.finditer(extern_pattern, content, re.MULTILINE))
    
    if extern_matches:
        print(f"\nFound {len(extern_matches)} extern Printf declaration(s):")
        for i, match in enumerate(extern_matches, 1):
            line_num = content[:match.start()].count('\n') + 1
            print(f"  {i}. Line {line_num}: {match.group().strip()}")
    else:
        print("\nNo extern Printf declarations found")
    
    # Check for Printf includes
    printf_includes = [
        '../common/engine/printf.h',
        'common/engine/printf.h',
        'engine/printf.h'
    ]
    
    found_includes = [inc for inc in printf_includes if inc in content]
    if found_includes:
        print(f"\nFound Printf include: {found_includes[0]}")
    else:
        print("\nNo Printf header include found - will need to add one")
    
    # Check easywsclient include
    if '#include "easywsclient/easywsclient.hpp"' in content:
        print("\nFound incorrect easywsclient include path - will fix")
    
    print("\n" + "-" * 60)

def main():
    if len(sys.argv) < 2:
        print("Archipelago Printf Fix Script")
        print("=" * 60)
        print("\nThis script fixes Printf declaration conflicts in archipelago_client.cpp")
        print("\nUsage:")
        print(f"  {sys.argv[0]} <path_to_archipelago_client.cpp> [--analyze]")
        print("\nExamples:")
        print(f"  {sys.argv[0]} C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/archipelago/archipelago_client.cpp")
        print(f"  {sys.argv[0]} archipelago_client.cpp --analyze")
        print("\nOptions:")
        print("  --analyze    Show what would be changed without modifying the file")
        sys.exit(1)
    
    filepath = sys.argv[1]
    analyze_only = "--analyze" in sys.argv
    
    if analyze_only:
        print(f"\nAnalyzing {filepath}...")
        analyze_file(filepath)
        print("\nTo apply these fixes, run without --analyze flag")
    else:
        print(f"\nProcessing {filepath}...")
        if fix_archipelago_client_printf(filepath):
            print("\n✓ File successfully fixed!")
            print("\nNext steps:")
            print("1. Review the changes by comparing with the .backup file")
            print("2. Rebuild your project")
            print("3. The Printf errors should now be resolved")
        else:
            print("\n✓ File already appears to be correct")

if __name__ == "__main__":
    main()