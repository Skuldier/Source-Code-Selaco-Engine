#!/usr/bin/env python3
"""
Add Archipelago integration to d_net.cpp
This script adds the necessary includes, function declarations, and implementations
for Archipelago support in Selaco's networking code.
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

def add_archipelago_include(content):
    """Add the Archipelago client include after other includes"""
    # Find the last include statement
    include_pattern = r'(#include\s+[<"][^>"]+[>"].*\n)+'
    match = re.search(include_pattern, content)
    
    if match:
        last_include_pos = match.end()
        # Check if archipelago include already exists
        if 'archipelago/archipelago_client.h' in content[:last_include_pos]:
            print("✓ Archipelago include already present")
            return content
        
        # Add the include after the last include
        before = content[:last_include_pos]
        after = content[last_include_pos:]
        new_content = before + '\n#include "archipelago/archipelago_client.h"\n' + after
        print("✓ Added Archipelago client include")
        return new_content
    else:
        print("Warning: Could not find include statements")
        return content

def add_function_declaration(content):
    """Add Net_ProcessArchipelago declaration to d_net.h if needed"""
    # This would be in d_net.h, but since we're patching d_net.cpp,
    # we'll note this for the user
    return content

def find_best_location_for_function(content):
    """Find the best location to add Net_ProcessArchipelago function"""
    # Look for Net_GetLatency function as a good reference point
    # We'll add our function just before it
    pattern = r'(//.*\n)*int\s+Net_GetLatency\s*\('
    match = re.search(pattern, content)
    
    if match:
        return match.start()
    
    # Alternative: look for the Net_SkipCommand function end
    # First find where Net_SkipCommand starts
    skip_start = content.find('void Net_SkipCommand')
    if skip_start != -1:
        # Find the closing brace of this function
        brace_count = 0
        in_function = False
        i = skip_start
        
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
                    # Found the closing brace
                    # Skip past any whitespace and newlines
                    i += 1
                    while i < len(content) and content[i] in ' \t\n':
                        i += 1
                    return i
            i += 1
    
    # If we can't find a good spot, put it before the CCMDs at the end
    ccmd_pos = content.find('CCMD (pings)')
    if ccmd_pos != -1:
        # Back up to find a good spot before the comment
        i = ccmd_pos - 1
        while i > 0 and content[i] in ' \t\n':
            i -= 1
        while i > 0 and content[i] == '/':
            # Skip back over comment lines
            while i > 0 and content[i] != '\n':
                i -= 1
            i -= 1
            while i > 0 and content[i] in ' \t\n':
                i -= 1
        return i + 1
    
    # Last resort: end of file
    return len(content)

def add_archipelago_function(content):
    """Add the Net_ProcessArchipelago function definition"""
    # Check if function already exists
    if 'Net_ProcessArchipelago' in content:
        print("✓ Net_ProcessArchipelago function already exists")
        return content
    
    # Find the best location
    insert_pos = find_best_location_for_function(content)
    
    # Function implementation
    archipelago_function = '''
//==========================================================================
//
// Net_ProcessArchipelago
//
// Process Archipelago messages in the main game loop
//
//==========================================================================

void Net_ProcessArchipelago()
{
	if (Archipelago::g_archipelago && Archipelago::g_archipelago->IsConnected()) {
		Archipelago::g_archipelago->ProcessMessages();
	}
}
'''
    
    # Insert the function
    before = content[:insert_pos]
    after = content[insert_pos:]
    
    # Make sure we have proper spacing
    if insert_pos > 0 and before[-1] != '\n':
        archipelago_function = '\n' + archipelago_function
    if insert_pos < len(content) and after[0] != '\n':
        archipelago_function = archipelago_function + '\n'
    
    new_content = before + archipelago_function + after
    print(f"✓ Added Net_ProcessArchipelago function at position {insert_pos}")
    return new_content

def add_archipelago_call_in_tryruntics(content):
    """Add the call to Net_ProcessArchipelago in TryRunTics"""
    # Find TryRunTics function
    tryruntics_pattern = r'void\s+TryRunTics\s*\([^)]*\)\s*\{'
    match = re.search(tryruntics_pattern, content)
    
    if not match:
        print("Error: Could not find TryRunTics function")
        return content
    
    # Look for the NetUpdate call within TryRunTics
    # We want to add our call after NetUpdate
    start_pos = match.end()
    
    # Find "NetUpdate ();" after the function start
    netupdate_pattern = r'NetUpdate\s*\(\s*\)\s*;'
    netupdate_match = re.search(netupdate_pattern, content[start_pos:])
    
    if not netupdate_match:
        print("Error: Could not find NetUpdate call in TryRunTics")
        return content
    
    # Calculate absolute position
    netupdate_pos = start_pos + netupdate_match.end()
    
    # Check if the call already exists nearby
    check_area = content[netupdate_pos:netupdate_pos + 200]
    if 'Net_ProcessArchipelago' in check_area:
        print("✓ Net_ProcessArchipelago call already exists in TryRunTics")
        return content
    
    # Find the next line after NetUpdate
    next_line_pos = content.find('\n', netupdate_pos) + 1
    
    # Determine indentation by looking at the NetUpdate line
    line_start = content.rfind('\n', 0, start_pos + netupdate_match.start()) + 1
    line_end = netupdate_pos
    netupdate_line = content[line_start:line_end]
    indent_match = re.match(r'^(\s*)', netupdate_line)
    indent = indent_match.group(1) if indent_match else '\t'
    
    # Add the archipelago call with proper indentation and comment
    archipelago_call = f'{indent}// Process Archipelago messages\n{indent}Net_ProcessArchipelago();\n'
    
    # Insert the call
    new_content = content[:next_line_pos] + archipelago_call + content[next_line_pos:]
    print("✓ Added Net_ProcessArchipelago call in TryRunTics")
    return new_content

def update_net_h_instructions():
    """Print instructions for updating d_net.h"""
    print("\n" + "="*60)
    print("IMPORTANT: Manual step required for d_net.h")
    print("="*60)
    print("\nYou also need to add the following line to d_net.h:")
    print("\n// Process Archipelago messages")
    print("void Net_ProcessArchipelago(void);")
    print("\nAdd this declaration near the other function declarations,")
    print("for example, after the line:")
    print("extern\tint \t\t\tticdup;")
    print("\nThis is typically around line 95 in d_net.h")
    print("="*60 + "\n")

def add_archipelago_integration(filepath):
    """Main function to add Archipelago integration"""
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return False
    
    print(f"Processing file: {filepath}")
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply modifications in order
    print("\nApplying Archipelago integration patches...")
    
    # 1. Add include
    content = add_archipelago_include(content)
    
    # 2. Add function definition
    content = add_archipelago_function(content)
    
    # 3. Add function call in TryRunTics
    content = add_archipelago_call_in_tryruntics(content)
    
    # Create backup before writing
    backup_path = create_backup(filepath)
    
    # Write the modified content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✓ Successfully added Archipelago integration to d_net.cpp")
    
    # Print additional instructions
    update_net_h_instructions()
    
    print("\nNext steps:")
    print("1. Update d_net.h with the function declaration (see above)")
    print("2. Rebuild your project")
    print("3. Test the Archipelago integration with 'ap_connect' command")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python add_archipelago_integration_patch.py <path_to_d_net.cpp>")
        print("Example: python add_archipelago_integration_patch.py C:\\Users\\Skuldier\\Documents\\Source-Code-Selaco-Engine\\src\\d_net.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Confirm with user before proceeding
    print(f"This script will add Archipelago integration to:")
    print(f"  {filepath}")
    print("\nThis will add:")
    print("  - Include for archipelago/archipelago_client.h")
    print("  - Net_ProcessArchipelago() function definition")
    print("  - Call to Net_ProcessArchipelago() in TryRunTics")
    print("\nA backup will be created before any changes are made.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    success = add_archipelago_integration(filepath)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()