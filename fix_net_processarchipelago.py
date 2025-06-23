#!/usr/bin/env python3
"""
Fix the misplaced Net_ProcessArchipelago function in d_net.cpp
"""

import sys
import os
import re

def fix_net_processarchipelago(filepath):
    """Fix the incorrectly placed Net_ProcessArchipelago function"""
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return False
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find the misplaced function
    # It should be between DEM_SETSLOT case and DEM_ADDSLOT case
    pattern = r'(case DEM_SETSLOT:.*?break;\s*)\n\n// Called from the main game loop\nvoid Net_ProcessArchipelago\(\)\n\{\n\tif \(Archipelago::g_archipelago && Archipelago::g_archipelago->IsConnected\(\)\) \{\n\t\tArchipelago::g_archipelago->ProcessMessages\(\);\n\t}\n\}\n(\s*case DEM_ADDSLOT:)'
    
    # Check if the misplaced function exists
    if not re.search(pattern, content, re.DOTALL):
        print("Warning: Could not find the misplaced Net_ProcessArchipelago function.")
        print("Attempting alternative pattern...")
        
        # Try a more flexible pattern
        pattern = r'(break;\s*)\n+//\s*Called from the main game loop\s*\nvoid\s+Net_ProcessArchipelago\s*\(\s*\)\s*\n\{[^}]+\}\s*\n+(case\s+DEM_ADDSLOT:)'
        
        if not re.search(pattern, content, re.DOTALL):
            print("Error: Could not find the Net_ProcessArchipelago function to fix.")
            return False
    
    # Extract the function
    function_code = """
// Called from the main game loop
void Net_ProcessArchipelago()
{
	if (Archipelago::g_archipelago && Archipelago::g_archipelago->IsConnected()) {
		Archipelago::g_archipelago->ProcessMessages();
	}
}"""
    
    # Remove the misplaced function from within Net_SkipCommand
    content = re.sub(pattern, r'\1\n\2', content, flags=re.DOTALL)
    
    # Find a good place to insert the function - after all the includes and before Net_SkipCommand
    # Look for the Net_SkipCommand function
    skip_command_pattern = r'(#include.*?\n+)(.*?)(void Net_SkipCommand\s*\()'
    
    match = re.search(skip_command_pattern, content, re.DOTALL)
    if match:
        # Insert the function before Net_SkipCommand
        before_skip = match.group(1) + match.group(2)
        skip_command_start = match.group(3)
        
        # Find the last include or empty line before Net_SkipCommand
        lines = before_skip.split('\n')
        insert_pos = len(lines) - 1
        
        # Go backwards to find a good insertion point
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line == '' or line.startswith('//') and i < len(lines) - 5:
                insert_pos = i + 1
                break
        
        # Reconstruct with the function in the right place
        new_lines = lines[:insert_pos] + [function_code, ''] + lines[insert_pos:]
        new_before_skip = '\n'.join(new_lines)
        
        # Find where skip_command_start begins in the original content
        skip_pos = content.find(skip_command_start)
        content = new_before_skip + content[skip_pos:]
    else:
        print("Warning: Could not find Net_SkipCommand function. Appending at end of file.")
        # As a fallback, append at the end of the file
        content = content.rstrip() + '\n\n' + function_code + '\n'
    
    # Save the fixed file
    backup_path = filepath + '.backup'
    print(f"Creating backup at {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Writing fixed content to {filepath}")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fix applied successfully!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_net_processarchipelago.py <path_to_d_net.cpp>")
        print("Example: python fix_net_processarchipelago.py C:\\Users\\Skuldier\\Documents\\Source-Code-Selaco-Engine\\src\\d_net.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    success = fix_net_processarchipelago(filepath)
    sys.exit(0 if success else 1)