#!/usr/bin/env python3
"""
Patch for d_main.cpp to fix Archipelago integration errors.
This adds the necessary includes and fixes the initialization/shutdown placement.
"""

import re
import os
import sys

def patch_d_main_cpp(filepath):
    """Fix d_main.cpp by adding includes and fixing AP_Init/AP_Shutdown placement"""
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    
    # Step 1: Add archipelago include at the top with other includes
    # Look for a group of #include statements and add ours
    include_pattern = r'(#include\s+"[^"]+"\s*\n)+'
    include_match = re.search(include_pattern, content)
    
    if include_match and '#include "archipelago/archipelago_client.h"' not in content:
        insert_pos = include_match.end()
        content = content[:insert_pos] + '#include "archipelago/archipelago_client.h"\n' + content[insert_pos:]
        print("✓ Added archipelago_client.h include")
    
    # Step 2: Fix AP_Init placement - add it in D_DoomMain after basic initialization
    # Look for where we might want to initialize (after Args processing, before game loop)
    if 'Archipelago::AP_Init()' not in content:
        # Look for a good spot after command line processing
        init_patterns = [
            r'(D_DoomMain[^{]*{[^}]*?Args\s*=\s*new[^;]+;[^}]*?)\n',  # After Args initialization
            r'(gamestate\s*=\s*GS_STARTUP[^;]*;[^}]*?)\n',           # After gamestate set
            r'(I_InitGraphics\s*\(\)[^;]*;[^}]*?)\n',                # After graphics init
        ]
        
        for pattern in init_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                insert_pos = match.end()
                content = content[:insert_pos] + '\n\t// Initialize Archipelago client\n\tArchipelago::AP_Init();\n' + content[insert_pos:]
                print("✓ Added AP_Init() call")
                break
    
    # Step 3: Fix AP_Shutdown placement
    # First, remove any misplaced AP_Shutdown calls
    if 'Archipelago::AP_Shutdown()' in content:
        # Find the bad placement and remove it
        bad_pattern = r'Archipelago::AP_Shutdown\(\);.*?D_Cleanup\(\);.*?CloseNetwork\(\);.*?GC::FinalGC'
        match = re.search(bad_pattern, content, re.DOTALL)
        if match:
            # Extract just the part we want to keep
            content = re.sub(r'Archipelago::AP_Shutdown\(\);\s*}\s*D_Cleanup', 'D_Cleanup', content)
            print("✓ Fixed misplaced AP_Shutdown()")
    
    # Now add it in the correct place
    shutdown_pattern = r'(catch\s*\([^)]+\)\s*{[^}]+ret\s*=\s*-1;\s*}\s*)\n'
    match = re.search(shutdown_pattern, content, re.DOTALL)
    if match and 'Archipelago::AP_Shutdown()' not in content[match.end():match.end()+100]:
        insert_pos = match.end()
        content = content[:insert_pos] + '\n\t// Shutdown Archipelago before main cleanup\n\tArchipelago::AP_Shutdown();\n' + content[insert_pos:]
        print("✓ Added AP_Shutdown() in correct location")
    
    # Step 4: Fix any syntax errors around the cleanup section
    # The errors suggest there might be extra braces or missing semicolons
    # Clean up the section between AP_Shutdown and D_Cleanup
    cleanup_pattern = r'(Archipelago::AP_Shutdown\(\);[^D]*)(D_Cleanup\(\);)'
    match = re.search(cleanup_pattern, content)
    if match:
        between = match.group(1)
        if between.count('}') > 0:
            # Remove extra closing braces
            content = re.sub(cleanup_pattern, r'Archipelago::AP_Shutdown();\n\t\n\t\2', content)
            print("✓ Fixed syntax between AP_Shutdown and D_Cleanup")
    
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
        print("⚠ No changes needed for d_main.cpp")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_d_main_patch.py <path_to_d_main.cpp>")
        print("Example: python fix_d_main_patch.py C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/d_main.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    if patch_d_main_cpp(filepath):
        print("\n✅ d_main.cpp patched successfully!")
        print("\nWhat this patch did:")
        print("1. Added the archipelago_client.h include")
        print("2. Added AP_Init() call in the initialization sequence")
        print("3. Fixed AP_Shutdown() placement before D_Cleanup()")
        print("4. Fixed any syntax errors in the cleanup section")
    else:
        print("\n❌ Failed to patch d_main.cpp")