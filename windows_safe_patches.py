#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows-safe versions of all Archipelago integration patches.
This version avoids Unicode characters that cause encoding errors on Windows.
"""

import re
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def safe_print(message):
    """Print message safely on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace unicode characters with ASCII alternatives
        message = message.replace('✓', '[OK]')
        message = message.replace('❌', '[FAIL]')
        message = message.replace('⚠', '[WARN]')
        message = message.replace('✅', '[SUCCESS]')
        message = message.replace('⚠️', '[WARNING]')
        print(message)

# ============== PATCH 1: d_main.cpp ==============

def patch_d_main_cpp(filepath):
    """Fix d_main.cpp by adding includes and fixing AP_Init/AP_Shutdown placement"""
    
    if not os.path.exists(filepath):
        safe_print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    
    # Step 1: Add archipelago include at the top with other includes
    include_pattern = r'(#include\s+"[^"]+"\s*\n)+'
    include_match = re.search(include_pattern, content)
    
    if include_match and '#include "archipelago/archipelago_client.h"' not in content:
        insert_pos = include_match.end()
        content = content[:insert_pos] + '#include "archipelago/archipelago_client.h"\n' + content[insert_pos:]
        safe_print("[OK] Added archipelago_client.h include")
    
    # Step 2: Fix AP_Init placement
    if 'Archipelago::AP_Init()' not in content:
        init_patterns = [
            r'(D_DoomMain[^{]*{[^}]*?Args\s*=\s*new[^;]+;[^}]*?)\n',
            r'(gamestate\s*=\s*GS_STARTUP[^;]*;[^}]*?)\n',
            r'(I_InitGraphics\s*\(\)[^;]*;[^}]*?)\n',
        ]
        
        for pattern in init_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                insert_pos = match.end()
                content = content[:insert_pos] + '\n\t// Initialize Archipelago client\n\tArchipelago::AP_Init();\n' + content[insert_pos:]
                safe_print("[OK] Added AP_Init() call")
                break
    
    # Step 3: Fix AP_Shutdown placement
    if 'Archipelago::AP_Shutdown()' in content:
        content = re.sub(r'Archipelago::AP_Shutdown\(\);\s*}\s*D_Cleanup', 'D_Cleanup', content)
        safe_print("[OK] Fixed misplaced AP_Shutdown()")
    
    shutdown_pattern = r'(catch\s*\([^)]+\)\s*{[^}]+ret\s*=\s*-1;\s*}\s*)\n'
    match = re.search(shutdown_pattern, content, re.DOTALL)
    if match and 'Archipelago::AP_Shutdown()' not in content[match.end():match.end()+100]:
        insert_pos = match.end()
        content = content[:insert_pos] + '\n\t// Shutdown Archipelago before main cleanup\n\tArchipelago::AP_Shutdown();\n' + content[insert_pos:]
        safe_print("[OK] Added AP_Shutdown() in correct location")
    
    # Step 4: Fix syntax errors
    cleanup_pattern = r'(Archipelago::AP_Shutdown\(\);[^D]*)(D_Cleanup\(\);)'
    match = re.search(cleanup_pattern, content)
    if match:
        between = match.group(1)
        if between.count('}') > 0:
            content = re.sub(cleanup_pattern, r'Archipelago::AP_Shutdown();\n\t\n\t\2', content)
            safe_print("[OK] Fixed syntax between AP_Shutdown and D_Cleanup")
    
    # Save the patched file
    if content != original_content:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        safe_print(f"[OK] Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        safe_print(f"[OK] Patched {filepath}")
        return True
    else:
        safe_print("[WARN] No changes needed for d_main.cpp")
        return False

# ============== PATCH 2: d_net.cpp ==============

def patch_d_net_cpp(filepath):
    """Fix d_net.cpp by moving Net_ProcessArchipelago to proper scope"""
    
    if not os.path.exists(filepath):
        safe_print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    
    # Step 1: Add archipelago include if not present
    if '#include "archipelago/archipelago_client.h"' not in content:
        include_pattern = r'(#include\s+"[^"]+"\s*\n)+'
        include_match = re.search(include_pattern, content)
        
        if include_match:
            insert_pos = include_match.end()
            content = content[:insert_pos] + '#include "archipelago/archipelago_client.h"\n' + content[insert_pos:]
            safe_print("[OK] Added archipelago_client.h include")
    
    # Step 2: Find and remove misplaced Net_ProcessArchipelago
    misplaced_pattern = r'(case\s+\w+:[^}]+?)(\n\s*void\s+Net_ProcessArchipelago\s*\(\s*\)\s*{[^}]+})'
    match = re.search(misplaced_pattern, content, re.DOTALL)
    
    if match:
        content = content[:match.start(2)] + content[match.end(2):]
        safe_print("[OK] Removed misplaced Net_ProcessArchipelago from inside switch statement")
    
    # Step 3: Add Net_ProcessArchipelago at file scope
    if 'void Net_ProcessArchipelago()' not in content:
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
        last_func_pattern = r'((?:^|\n)[^\n]*?(?:void|int|bool|CCMD)[^{]+{[^}]+})\s*$'
        match = re.search(last_func_pattern, content, re.MULTILINE | re.DOTALL)
        
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + '\n' + function_code + '\n' + content[insert_pos:]
        else:
            content = content.rstrip() + '\n' + function_code + '\n'
        
        safe_print("[OK] Added Net_ProcessArchipelago at file scope")
    
    # Step 4: Make sure we're calling it somewhere
    if 'Net_ProcessArchipelago()' not in content or content.count('Net_ProcessArchipelago()') < 2:
        call_patterns = [
            r'(NetUpdate\s*\(\s*\)[^;]*;)',
            r'(I_StartTic\s*\(\s*\)[^;]*;)',
            r'(// This was taken out of shared_hud)',
        ]
        
        for pattern in call_patterns:
            match = re.search(pattern, content)
            if match:
                before_match = content[:match.start()]
                brace_count = before_match.count('{') - before_match.count('}')
                
                if brace_count > 0:
                    insert_pos = match.end()
                    if 'Net_ProcessArchipelago();' not in content[insert_pos-100:insert_pos+100]:
                        content = content[:insert_pos] + '\n\t\t// Process Archipelago messages\n\t\tNet_ProcessArchipelago();\n' + content[insert_pos:]
                        safe_print(f"[OK] Added Net_ProcessArchipelago() call after {pattern}")
                        break
    
    # Save the patched file
    if content != original_content:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        safe_print(f"[OK] Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        safe_print(f"[OK] Patched {filepath}")
        return True
    else:
        safe_print("[WARN] No changes needed for d_net.cpp")
        return False

# ============== PATCH 3: d_net.h ==============

def patch_d_net_header(src_dir):
    """Add Net_ProcessArchipelago declaration to d_net.h"""
    
    header_path = os.path.join(src_dir, 'd_net.h')
    cpp_path = os.path.join(src_dir, 'd_net.cpp')
    
    if os.path.exists(header_path):
        safe_print(f"Found {header_path}")
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        if 'Net_ProcessArchipelago' not in content:
            func_pattern = r'((?:^|\n)void\s+\w+\s*\([^)]*\)\s*;)'
            matches = list(re.finditer(func_pattern, content, re.MULTILINE))
            
            if matches:
                insert_pos = matches[-1].end()
                content = content[:insert_pos] + '\nvoid Net_ProcessArchipelago();\n' + content[insert_pos:]
                safe_print("[OK] Added Net_ProcessArchipelago declaration to d_net.h")
            else:
                any_func_pattern = r'((?:^|\n)(?:int|bool|void)\s+\w+\s*\([^)]*\)\s*;)'
                matches = list(re.finditer(any_func_pattern, content, re.MULTILINE))
                
                if matches:
                    insert_pos = matches[-1].end()
                    content = content[:insert_pos] + '\nvoid Net_ProcessArchipelago();\n' + content[insert_pos:]
                    safe_print("[OK] Added Net_ProcessArchipelago declaration to d_net.h")
                else:
                    endif_pattern = r'(#endif[^\n]*)\s*$'
                    match = re.search(endif_pattern, content)
                    if match:
                        insert_pos = match.start()
                        content = content[:insert_pos] + '\n// Archipelago integration\nvoid Net_ProcessArchipelago();\n\n' + content[insert_pos:]
                        safe_print("[OK] Added Net_ProcessArchipelago declaration before #endif")
            
            if content != original_content:
                backup_path = header_path + '.backup'
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                safe_print(f"[OK] Created backup at {backup_path}")
                
                with open(header_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                safe_print(f"[OK] Patched {header_path}")
                return True
        else:
            safe_print("[OK] Net_ProcessArchipelago declaration already exists in d_net.h")
            return True
    
    else:
        safe_print(f"[WARN] d_net.h not found, adding declaration to d_net.cpp instead")
        
        if not os.path.exists(cpp_path):
            safe_print(f"Error: {cpp_path} not found!")
            return False
        
        with open(cpp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        if 'void Net_ProcessArchipelago();' not in content:
            include_end = 0
            include_pattern = r'(#include\s+[<"][^>"]+[>"](?:\s*//[^\n]*)?\s*\n)+'
            match = re.search(include_pattern, content)
            if match:
                include_end = match.end()
            
            extern_pattern = r'((?:extern|static)\s+[^;]+;(?:\s*//[^\n]*)?\s*\n)+'
            match = re.search(extern_pattern, content[include_end:])
            if match:
                insert_pos = include_end + match.end()
            else:
                insert_pos = include_end
            
            declaration = '\n// Forward declaration for Archipelago\nvoid Net_ProcessArchipelago();\n\n'
            content = content[:insert_pos] + declaration + content[insert_pos:]
            safe_print("[OK] Added Net_ProcessArchipelago declaration to d_net.cpp")
            
            backup_path = cpp_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            safe_print(f"[OK] Created backup at {backup_path}")
            
            with open(cpp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            safe_print(f"[OK] Patched {cpp_path}")
            return True
        else:
            safe_print("[OK] Net_ProcessArchipelago declaration already exists")
            return True

# ============== PATCH 4: CMakeLists.txt ==============

def patch_cmake_lists(filepath):
    """Fix CMakeLists.txt to properly include Archipelago sources"""
    
    if not os.path.exists(filepath):
        safe_print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    archipelago_sources_pattern = r'set\s*\(\s*ARCHIPELAGO_SOURCES[^)]+\)'
    match = re.search(archipelago_sources_pattern, content, re.DOTALL)
    
    if not match:
        safe_print("[WARN] ARCHIPELAGO_SOURCES not found, adding it...")
        
        source_set_pattern = r'(set\s*\(\s*\w+_SOURCES[^)]+\))'
        matches = list(re.finditer(source_set_pattern, content, re.DOTALL))
        
        if matches:
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
            safe_print("[OK] Added ARCHIPELAGO_SOURCES definition")
            changes_made = True
    else:
        safe_print("[OK] ARCHIPELAGO_SOURCES already defined")
        
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
                safe_print(f"[WARN] Missing {file} in ARCHIPELAGO_SOURCES")
                content = content[:match.end()-1] + f'\n\t{file}' + content[match.end()-1:]
                safe_print(f"[OK] Added {file}")
                changes_made = True
    
    exe_pattern = r'add_executable\s*\(\s*(\w+)([^)]+)\)'
    exe_match = re.search(exe_pattern, content, re.DOTALL)
    
    if exe_match:
        exe_name = exe_match.group(1)
        exe_sources = exe_match.group(2)
        
        if '${ARCHIPELAGO_SOURCES}' not in exe_sources and 'ARCHIPELAGO_SOURCES' not in exe_sources:
            safe_print(f"[WARN] ARCHIPELAGO_SOURCES not included in {exe_name} executable")
            
            if '${GAME_SOURCES}' in exe_sources:
                content = content.replace(
                    '${GAME_SOURCES}',
                    '${GAME_SOURCES}\n\t${ARCHIPELAGO_SOURCES}'
                )
                safe_print(f"[OK] Added ARCHIPELAGO_SOURCES to {exe_name} executable")
                changes_made = True
            else:
                insert_pos = exe_match.end() - 1
                content = content[:insert_pos] + '\n\t${ARCHIPELAGO_SOURCES}' + content[insert_pos:]
                safe_print(f"[OK] Added ARCHIPELAGO_SOURCES to {exe_name} executable")
                changes_made = True
        else:
            safe_print(f"[OK] ARCHIPELAGO_SOURCES already included in {exe_name} executable")
    
    if 'rapidjson' not in content.lower() and 'RAPIDJSON' not in content:
        safe_print("\n[WARN] Note: You may need to add RapidJSON to your project dependencies")
        safe_print("  Consider adding: find_package(RapidJSON REQUIRED)")
    
    include_dir_pattern = r'target_include_directories\s*\([^)]+\)'
    if re.search(include_dir_pattern, content):
        if 'archipelago' not in content:
            safe_print("\n[WARN] Note: You may need to add archipelago to include directories")
            safe_print("  Consider adding: target_include_directories(zdoom PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/archipelago)")
    
    if changes_made:
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        safe_print(f"\n[OK] Created backup at {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        safe_print(f"[OK] Patched {filepath}")
        return True
    else:
        safe_print("\n[OK] CMakeLists.txt appears to be correctly configured")
        return True

# ============== MAIN SCRIPT ==============

def main():
    if len(sys.argv) != 2:
        safe_print("Usage: python windows_safe_patches.py <path_to_source_code_root>")
        safe_print("Example: python windows_safe_patches.py C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine")
        sys.exit(1)
    
    root_path = Path(sys.argv[1])
    src_path = root_path / "src"
    
    if not src_path.exists():
        safe_print(f"Error: src directory not found at {src_path}")
        sys.exit(1)
    
    safe_print(f"Selaco source root: {root_path}")
    safe_print(f"Source directory: {src_path}")
    
    backup_dir = root_path / "archipelago_backup"
    if not backup_dir.exists():
        backup_dir.mkdir()
        safe_print(f"\n[OK] Created backup directory: {backup_dir}")
    
    success = True
    
    safe_print(f"\n{'='*60}")
    safe_print("PATCHING d_main.cpp")
    safe_print(f"{'='*60}")
    
    d_main_path = src_path / "d_main.cpp"
    if d_main_path.exists():
        success &= patch_d_main_cpp(str(d_main_path))
    else:
        safe_print(f"\n[WARN] d_main.cpp not found at {d_main_path}")
        success = False
    
    safe_print(f"\n{'='*60}")
    safe_print("PATCHING d_net.cpp")
    safe_print(f"{'='*60}")
    
    d_net_path = src_path / "d_net.cpp"
    if d_net_path.exists():
        success &= patch_d_net_cpp(str(d_net_path))
    else:
        safe_print(f"\n[WARN] d_net.cpp not found at {d_net_path}")
        success = False
    
    safe_print(f"\n{'='*60}")
    safe_print("PATCHING d_net.h or adding declaration")
    safe_print(f"{'='*60}")
    
    success &= patch_d_net_header(str(src_path))
    
    safe_print(f"\n{'='*60}")
    safe_print("PATCHING CMakeLists.txt")
    safe_print(f"{'='*60}")
    
    cmake_path = src_path / "CMakeLists.txt"
    if cmake_path.exists():
        success &= patch_cmake_lists(str(cmake_path))
    else:
        safe_print(f"\n[WARN] CMakeLists.txt not found at {cmake_path}")
        success = False
    
    safe_print(f"\n{'='*60}")
    safe_print("PATCH SUMMARY")
    safe_print(f"{'='*60}")
    
    if success:
        safe_print("\n[SUCCESS] All patches applied successfully!")
        safe_print("\nNext steps:")
        safe_print("1. Review the changes made by the patches")
        safe_print("2. Rebuild the project using CMake")
        safe_print("3. If compilation still fails, share the new error messages")
        safe_print("\nBackup files have been created with .backup extension")
        safe_print("\nTo restore original files:")
        safe_print("  - Windows: copy *.backup files back to original names")
        safe_print("  - Linux/Mac: cp *.backup files back to original names")
    else:
        safe_print("\n[FAIL] Some patches failed!")
        safe_print("\nPlease check the error messages above and:")
        safe_print("1. Verify the file paths are correct")
        safe_print("2. Ensure you have write permissions")
        safe_print("3. Check if the files have already been modified")
    
    safe_print(f"\n{'='*60}")
    safe_print("ADDITIONAL NOTES")
    safe_print(f"{'='*60}")
    safe_print("\n1. Make sure the archipelago directory exists in src/")
    safe_print("2. Ensure all Archipelago source files are present:")
    safe_print("   - archipelago_client.cpp/h")
    safe_print("   - easywsclient.cpp/hpp") 
    safe_print("   - archipelago_ccmds.cpp")
    safe_print("3. You may need to install RapidJSON if not already present")
    safe_print("4. After successful compilation, test with:")
    safe_print("   - ap_connect <host> <port>")
    safe_print("   - ap_auth <slot_name>")
    safe_print("   - ap_status")

if __name__ == "__main__":
    main()