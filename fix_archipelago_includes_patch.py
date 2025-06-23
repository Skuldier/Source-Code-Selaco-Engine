#!/usr/bin/env python3
"""
Fix include paths and Printf errors in Archipelago source files.
This patch addresses:
1. Printf identifier not found errors
2. easywsclient include path issues
"""

import re
import os
import sys
from pathlib import Path

def safe_print(message):
    """Print message safely on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace unicode characters with ASCII alternatives
        message = message.replace('✓', '[OK]')
        message = message.replace('❌', '[FAIL]')
        message = message.replace('⚠', '[WARN]')
        print(message)

def fix_archipelago_ccmds(filepath):
    """Fix Printf errors in archipelago_ccmds.cpp by adding the correct include"""
    
    if not os.path.exists(filepath):
        safe_print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    # Check if we need to add the c_console.h include for Printf
    if 'Printf' in content and '#include "c_console.h"' not in content:
        # Find where other includes are
        include_pattern = r'(#include\s+"c_dispatch\.h"\s*\n)'
        match = re.search(include_pattern, content)
        
        if match:
            # Add c_console.h after c_dispatch.h
            insert_pos = match.end()
            # Also check if we're missing other includes
            if '#include "c_console.h"' not in content:
                content = content[:insert_pos] + '#include "c_console.h"\n' + content[insert_pos:]
                safe_print("[OK] Added c_console.h include for Printf function")
                changes_made = True
        else:
            # If no c_dispatch.h found, add at the beginning with other includes
            include_end_pattern = r'((?:#include\s*[<"][^>"]+[>"]\s*\n)+)'
            match = re.search(include_end_pattern, content)
            if match:
                insert_pos = match.end()
                content = content[:insert_pos] + '#include "c_console.h"\n' + content[insert_pos:]
                safe_print("[OK] Added c_console.h include at the end of includes")
                changes_made = True
    
    # Save the file if changes were made
    if changes_made:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        safe_print(f"[OK] Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        safe_print(f"[OK] Patched {filepath}")
        return True
    else:
        safe_print("[WARN] No changes needed for archipelago_ccmds.cpp")
        return False

def fix_archipelago_client(filepath):
    """Fix easywsclient include path in archipelago_client.cpp"""
    
    if not os.path.exists(filepath):
        safe_print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    # Fix the easywsclient include path
    if '#include "easywsclient/easywsclient.hpp"' in content:
        # The file is actually in the same directory, not in a subdirectory
        content = content.replace(
            '#include "easywsclient/easywsclient.hpp"',
            '#include "easywsclient.hpp"'
        )
        safe_print("[OK] Fixed easywsclient.hpp include path")
        changes_made = True
    
    # Also check if Printf is used and needs c_console.h
    if 'Printf' in content and '#include "c_console.h"' not in content:
        # Find a good place to add the include
        include_pattern = r'(#include\s+"archipelago_client\.h"\s*\n)'
        match = re.search(include_pattern, content)
        
        if match:
            insert_pos = match.end()
            # Add the necessary includes
            includes_to_add = []
            
            if '#include "c_console.h"' not in content:
                includes_to_add.append('#include "c_console.h"  // For Printf')
            
            if includes_to_add:
                content = content[:insert_pos] + '\n'.join(includes_to_add) + '\n' + content[insert_pos:]
                safe_print("[OK] Added missing includes for Printf")
                changes_made = True
    
    # Check if we need the extern declaration for Printf
    # In some Doom engine versions, Printf might need an extern declaration
    if 'Printf' in content and 'extern' not in content and '#include "c_console.h"' not in content:
        # Add extern declaration after includes
        include_end_pattern = r'((?:#include\s*[<"][^>"]+[>"]\s*\n)+)'
        match = re.search(include_end_pattern, content)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + '\n// Console output function from the engine\nextern void Printf(const char* format, ...);\n\n' + content[insert_pos:]
            safe_print("[OK] Added extern declaration for Printf")
            changes_made = True
    
    # Save the file if changes were made
    if changes_made:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        safe_print(f"[OK] Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        safe_print(f"[OK] Patched {filepath}")
        return True
    else:
        safe_print("[WARN] No changes needed for archipelago_client.cpp")
        return False

def check_easywsclient_location(archipelago_dir):
    """Check if easywsclient files are in the correct location"""
    
    # Expected files
    expected_files = [
        'easywsclient.hpp',
        'easywsclient.cpp'
    ]
    
    missing_files = []
    for filename in expected_files:
        filepath = os.path.join(archipelago_dir, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)
    
    if missing_files:
        safe_print("\n[WARN] Missing easywsclient files in archipelago directory:")
        for filename in missing_files:
            safe_print(f"  - {filename}")
        
        # Check if they're in a subdirectory
        easywsclient_subdir = os.path.join(archipelago_dir, 'easywsclient')
        if os.path.exists(easywsclient_subdir):
            safe_print("\n[INFO] Found easywsclient subdirectory. Files may need to be moved.")
            safe_print("  The files should be directly in the archipelago directory, not in a subdirectory.")
            return False
    else:
        safe_print("[OK] All easywsclient files found in correct location")
    
    return len(missing_files) == 0

def main():
    if len(sys.argv) != 2:
        safe_print("Usage: python fix_archipelago_includes_patch.py <archipelago_directory>")
        safe_print("Example: python fix_archipelago_includes_patch.py C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/archipelago")
        sys.exit(1)
    
    archipelago_dir = Path(sys.argv[1])
    
    if not archipelago_dir.exists():
        safe_print(f"Error: Archipelago directory not found at {archipelago_dir}")
        sys.exit(1)
    
    safe_print(f"Archipelago directory: {archipelago_dir}")
    
    success = True
    
    # Fix archipelago_ccmds.cpp
    safe_print(f"\n{'='*60}")
    safe_print("FIXING archipelago_ccmds.cpp")
    safe_print(f"{'='*60}")
    
    ccmds_path = archipelago_dir / "archipelago_ccmds.cpp"
    if ccmds_path.exists():
        success &= fix_archipelago_ccmds(str(ccmds_path))
    else:
        safe_print(f"[WARN] archipelago_ccmds.cpp not found at {ccmds_path}")
        success = False
    
    # Fix archipelago_client.cpp
    safe_print(f"\n{'='*60}")
    safe_print("FIXING archipelago_client.cpp")
    safe_print(f"{'='*60}")
    
    client_path = archipelago_dir / "archipelago_client.cpp"
    if client_path.exists():
        success &= fix_archipelago_client(str(client_path))
    else:
        safe_print(f"[WARN] archipelago_client.cpp not found at {client_path}")
        success = False
    
    # Check easywsclient file locations
    safe_print(f"\n{'='*60}")
    safe_print("CHECKING easywsclient file locations")
    safe_print(f"{'='*60}")
    
    success &= check_easywsclient_location(str(archipelago_dir))
    
    # Summary
    safe_print(f"\n{'='*60}")
    safe_print("SUMMARY")
    safe_print(f"{'='*60}")
    
    if success:
        safe_print("\n[OK] All fixes applied successfully!")
        safe_print("\nNext steps:")
        safe_print("1. If easywsclient files are in a subdirectory, move them to the archipelago directory")
        safe_print("2. Rebuild the project")
        safe_print("3. If you still get Printf errors, the engine might use a different header")
    else:
        safe_print("\n[WARN] Some issues remain!")
        safe_print("\nCommon solutions:")
        safe_print("1. Ensure easywsclient.hpp and easywsclient.cpp are in src/archipelago/")
        safe_print("2. NOT in src/archipelago/easywsclient/")
        safe_print("3. Check if the engine uses DPrintf instead of Printf")
        safe_print("4. Look for other console output functions in the engine source")
    
    # Additional help for Printf issues
    safe_print(f"\n{'='*60}")
    safe_print("ADDITIONAL HELP FOR Printf ERRORS")
    safe_print(f"{'='*60}")
    safe_print("\nIf Printf errors persist, try these approaches:")
    safe_print("1. Search for 'Printf' usage in other engine source files")
    safe_print("2. Common alternatives in Doom engines:")
    safe_print("   - DPrintf (debug printf)")
    safe_print("   - I_Printf (system printf)")  
    safe_print("   - Con_Printf (console printf)")
    safe_print("3. Check these header files:")
    safe_print("   - c_console.h")
    safe_print("   - doomtype.h")
    safe_print("   - i_system.h")
    safe_print("4. As a last resort, replace Printf with printf (lowercase)")

if __name__ == "__main__":
    main()