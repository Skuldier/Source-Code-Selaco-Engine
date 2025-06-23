#!/usr/bin/env python3
"""
Fix the misplaced Net_ProcessArchipelago function in d_net.cpp
This script moves the function from inside Net_SkipCommand's switch statement
to the proper location at file scope.
"""

import sys
import os
import re
import shutil
from datetime import datetime

def create_backup(filepath):
    """Create a timestamped backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✓ Created backup: {backup_path}")
    return backup_path

def find_misplaced_function(content):
    """Find the misplaced Net_ProcessArchipelago function and its location"""
    
    # Pattern to find the function inside the switch statement
    # This looks for the pattern where the function appears between break; and case DEM_ADDSLOT:
    pattern = r'(break;\s*\n+)(// Called from the main game loop\s*\nvoid Net_ProcessArchipelago\(\)\s*\n\{\s*\n\s*if \(Archipelago::g_archipelago && Archipelago::g_archipelago->IsConnected\(\)\) \{\s*\n\s*Archipelago::g_archipelago->ProcessMessages\(\);\s*\n\s*\}\s*\n\}\s*\n)(\s*case DEM_ADDSLOT:)'
    
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match
    
    # Try alternative pattern with more flexible whitespace
    pattern2 = r'(break;\s*\n*)(//\s*Called from the main game loop\s*\nvoid\s+Net_ProcessArchipelago\s*\(\s*\)\s*\n\{[^}]+\}\s*\n*)(\s*case\s+DEM_ADDSLOT:)'
    
    match = re.search(pattern2, content, re.MULTILINE | re.DOTALL)
    return match

def find_insertion_point(content):
    """Find the best location to insert the function (after Net_SkipCommand ends)"""
    
    # Look for the end of Net_SkipCommand function
    # First, find where Net_SkipCommand starts
    skip_cmd_start = content.find("void Net_SkipCommand")
    if skip_cmd_start == -1:
        return None
    
    # Now find the closing brace of this function
    # We need to count braces to find the matching closing brace
    brace_count = 0
    in_function = False
    i = skip_cmd_start
    
    while i < len(content):
        if content[i] == '{':
            if not in_function:
                in_function = True
                brace_count = 1
            else:
                brace_count += 1
        elif content[i] == '}' and in_function:
            brace_count -= 1
            if brace_count == 0:
                # Found the closing brace of Net_SkipCommand
                # Move past the brace
                i += 1
                # Skip any whitespace
                while i < len(content) and content[i] in ' \t':
                    i += 1
                # Add a newline if there isn't one
                if i < len(content) and content[i] != '\n':
                    return i, '\n'
                else:
                    # Skip to after the newline
                    while i < len(content) and content[i] == '\n':
                        i += 1
                    return i, ''
        i += 1
    
    return None

def fix_net_processarchipelago(filepath):
    """Fix the incorrectly placed Net_ProcessArchipelago function"""
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return False
    
    print(f"Processing file: {filepath}")
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the misplaced function
    match = find_misplaced_function(content)
    if not match:
        print("Error: Could not find the misplaced Net_ProcessArchipelago function.")
        print("The function may have already been fixed or is in an unexpected format.")
        return False
    
    print("✓ Found misplaced Net_ProcessArchipelago function")
    
    # Extract the parts
    before_break = match.group(1)
    function_code = match.group(2).strip()
    after_case = match.group(3)
    
    # Remove the misplaced function from the switch statement
    # We want to keep the break; and the case DEM_ADDSLOT: but remove the function in between
    fixed_switch = before_break + after_case
    
    # Replace in content
    content_fixed = content[:match.start()] + fixed_switch + content[match.end():]
    
    print("✓ Removed function from inside switch statement")
    
    # Find where to insert the function
    insertion_result = find_insertion_point(content_fixed)
    if not insertion_result:
        print("Error: Could not find a suitable insertion point for the function.")
        return False
    
    insertion_point, extra_newline = insertion_result
    
    # Prepare the function with proper formatting and comments
    formatted_function = f"""
//==========================================================================
//
// Net_ProcessArchipelago
//
// Process Archipelago messages in the main game loop
//
//==========================================================================

{function_code}
"""
    
    # Insert the function at the proper location
    final_content = (
        content_fixed[:insertion_point] + 
        extra_newline + 
        formatted_function + 
        content_fixed[insertion_point:]
    )
    
    print(f"✓ Function will be inserted at position {insertion_point}")
    
    # Create backup before writing
    backup_path = create_backup(filepath)
    
    # Write the fixed content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("✓ File successfully fixed!")
    print("\nWhat was done:")
    print("1. Created a backup of your original file")
    print("2. Removed Net_ProcessArchipelago from inside Net_SkipCommand's switch statement")
    print("3. Moved the function to file scope (after Net_SkipCommand)")
    print("4. Fixed the switch statement flow")
    print("\nNext steps:")
    print("1. Rebuild your project")
    print("2. The compilation errors should now be resolved")
    print("3. Test your Archipelago integration")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_archipelago_function_patch.py <path_to_d_net.cpp>")
        print("Example: python fix_archipelago_function_patch.py C:\\Users\\Skuldier\\Documents\\Source-Code-Selaco-Engine\\src\\d_net.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Confirm with user before proceeding
    print(f"This script will fix the misplaced Net_ProcessArchipelago function in:")
    print(f"  {filepath}")
    print("\nA backup will be created before any changes are made.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    success = fix_net_processarchipelago(filepath)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()