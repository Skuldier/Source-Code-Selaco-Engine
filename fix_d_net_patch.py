#!/usr/bin/env python3
"""
Patch for d_net.cpp to fix Net_ProcessArchipelago function placement.
This moves the function to file scope and adds necessary includes.
"""

import re
import os
import sys

def patch_d_net_cpp(filepath):
    """Fix d_net.cpp by moving Net_ProcessArchipelago to proper scope"""
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    
    # Step 1: Add archipelago include if not present
    if '#include "archipelago/archipelago_client.h"' not in content:
        # Find where includes are and add ours
        include_pattern = r'(#include\s+"[^"]+"\s*\n)+'
        include_match = re.search(include_pattern, content)
        
        if include_match:
            insert_pos = include_match.end()
            content = content[:insert_pos] + '#include "archipelago/archipelago_client.h"\n' + content[insert_pos:]
            print("✓ Added archipelago_client.h include")
    
    # Step 2: Find and remove the misplaced Net_ProcessArchipelago function
    # Based on the error, it seems to be inside another function
    misplaced_pattern = r'(case\s+\w+:[^}]+?)(\n\s*void\s+Net_ProcessArchipelago\s*\(\s*\)\s*{[^}]+})'
    match = re.search(misplaced_pattern, content, re.DOTALL)
    
    if match:
        # Remove the misplaced function
        content = content[:match.start(2)] + content[match.end(2):]
        print("✓ Removed misplaced Net_ProcessArchipelago from inside switch statement")
    
    # Step 3: Add Net_ProcessArchipelago at file scope (end of file)
    if 'void Net_ProcessArchipelago()' not in content:
        # Add the function at the end of the file, before any closing braces
        function_code = '''
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
        # Find a good place to insert - typically before the last closing brace or at end
        # Look for the last function in the file
        last_func_pattern = r'((?:^|\n)[^\n]*?(?:void|int|bool|CCMD)[^{]+{[^}]+})\s*$'
        match = re.search(last_func_pattern, content, re.MULTILINE | re.DOTALL)
        
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + '\n' + function_code + '\n' + content[insert_pos:]
        else:
            # Just add at the end
            content = content.rstrip() + '\n' + function_code + '\n'
        
        print("✓ Added Net_ProcessArchipelago at file scope")
    
    # Step 4: Make sure we're calling it somewhere
    # Look for a good place in the network update loop
    if 'Net_ProcessArchipelago()' not in content or content.count('Net_ProcessArchipelago()') < 2:
        # Find where we might want to call it - look for NetUpdate or similar
        call_patterns = [
            r'(NetUpdate\s*\(\s*\)[^;]*;)',  # After NetUpdate
            r'(I_StartTic\s*\(\s*\)[^;]*;)',  # After I_StartTic
            r'(// This was taken out of shared_hud)',  # Before the comment block we see in the code
        ]
        
        for pattern in call_patterns:
            match = re.search(pattern, content)
            if match:
                # Make sure we're not in the middle of a function definition
                # Check if we're inside a function by counting braces
                before_match = content[:match.start()]
                brace_count = before_match.count('{') - before_match.count('}')
                
                if brace_count > 0:  # We're inside a function
                    insert_pos = match.end()
                    # Add the call
                    if 'Net_ProcessArchipelago();' not in content[insert_pos-100:insert_pos+100]:
                        content = content[:insert_pos] + '\n\t\t// Process Archipelago messages\n\t\tNet_ProcessArchipelago();\n' + content[insert_pos:]
                        print(f"✓ Added Net_ProcessArchipelago() call after {pattern}")
                        break
    
    # Save the patched file
    if content != original_content:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"✓ Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Patched {filepath}")
        return True
    else:
        print("⚠ No changes needed for d_net.cpp")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_d_net_patch.py <path_to_d_net.cpp>")
        print("Example: python fix_d_net_patch.py C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/d_net.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    if patch_d_net_cpp(filepath):
        print("\n✅ d_net.cpp patched successfully!")
        print("\nWhat this patch did:")
        print("1. Added the archipelago_client.h include")
        print("2. Moved Net_ProcessArchipelago to file scope (outside any function)")
        print("3. Added a call to Net_ProcessArchipelago in the network update loop")
    else:
        print("\n❌ Failed to patch d_net.cpp")