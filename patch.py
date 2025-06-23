#!/usr/bin/env python3
"""
Windows-friendly patch application script for Selaco Archipelago integration
This script manually applies the patches without requiring Unix tools
"""

import os
import re
import shutil
from datetime import datetime

class PatchApplier:
    def __init__(self):
        self.patches = [
            ("CMakeLists_archipelago.patch", "src/CMakeLists.txt"),
            ("d_main_archipelago.patch", "src/d_main.cpp"),
            ("d_net_archipelago.patch", "src/d_net.cpp"),
            ("d_main_loop_archipelago.patch", "src/d_main.cpp"),
            ("d_net_h_archipelago.patch", "src/d_net.h"),
        ]
        
    def backup_file(self, filepath):
        """Create a backup of the file before modifying"""
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_path)
        print(f"Created backup: {backup_path}")
        return backup_path
        
    def find_line_number(self, lines, search_text, start_line=0):
        """Find the line number containing the search text"""
        for i in range(start_line, len(lines)):
            if search_text in lines[i]:
                return i
        return -1
        
    def apply_patch(self, patch_file, target_file):
        """Apply a patch file to the target file"""
        print(f"\nApplying {patch_file} to {target_file}...")
        
        if not os.path.exists(target_file):
            print(f"ERROR: Target file {target_file} not found!")
            return False
            
        if not os.path.exists(patch_file):
            print(f"ERROR: Patch file {patch_file} not found!")
            return False
            
        # Read the patch file
        with open(patch_file, 'r') as f:
            patch_content = f.read()
            
        # Read the target file
        with open(target_file, 'r') as f:
            target_lines = f.readlines()
            
        # Create backup
        self.backup_file(target_file)
        
        # Parse patch hunks
        hunks = re.findall(r'@@ -\d+,?\d* \+(\d+),?\d* @@.*?\n(.*?)(?=@@|$)', patch_content, re.DOTALL)
        
        modified = False
        offset = 0  # Track line number changes as we modify the file
        
        for hunk in hunks:
            start_line = int(hunk[0]) - 1 + offset
            hunk_content = hunk[1]
            
            # Split hunk into lines
            hunk_lines = hunk_content.split('\n')
            
            # Process each line in the hunk
            insert_position = start_line
            for line in hunk_lines:
                if not line:
                    continue
                    
                if line.startswith('+'):
                    # Add new line
                    new_line = line[1:] + '\n'
                    target_lines.insert(insert_position, new_line)
                    insert_position += 1
                    offset += 1
                    modified = True
                    print(f"  Added line at {insert_position}: {line[1:].strip()}")
                elif line.startswith('-'):
                    # Remove line (our patches don't have these)
                    if insert_position < len(target_lines):
                        removed = target_lines.pop(insert_position)
                        offset -= 1
                        modified = True
                        print(f"  Removed line at {insert_position}: {removed.strip()}")
                else:
                    # Context line - just move to next position
                    insert_position += 1
        
        if modified:
            # Write the modified file
            with open(target_file, 'w') as f:
                f.writelines(target_lines)
            print(f"Successfully applied patch to {target_file}")
            return True
        else:
            print(f"No changes made to {target_file}")
            return False
            
    def apply_all_patches(self):
        """Apply all patches"""
        print("=== Selaco Archipelago Patch Applicator ===\n")
        
        success_count = 0
        for patch_file, target_file in self.patches:
            if self.apply_patch(patch_file, target_file):
                success_count += 1
                
        print(f"\n=== Summary ===")
        print(f"Successfully applied {success_count}/{len(self.patches)} patches")
        
        if success_count == len(self.patches):
            print("\nAll patches applied successfully!")
            print("You can now build Selaco with Archipelago support.")
        else:
            print("\nSome patches failed to apply.")
            print("Check the error messages above and consider applying them manually.")

# Special handling for patches that modify the same file
def apply_patches_smart():
    """Apply patches with special handling for multiple patches to the same file"""
    
    # Check if we're in the right directory
    if not os.path.exists("src") or not os.path.exists("CMakeLists.txt"):
        print("ERROR: This script must be run from the Selaco source root directory!")
        print("Current directory:", os.getcwd())
        return
        
    applier = PatchApplier()
    
    # Apply CMakeLists patch
    applier.apply_patch("CMakeLists_archipelago.patch", "src/CMakeLists.txt")
    
    # Apply d_main patches (there are two for this file)
    # First backup d_main.cpp
    applier.backup_file("src/d_main.cpp")
    
    # Read d_main.cpp
    with open("src/d_main.cpp", 'r') as f:
        content = f.read()
    
    # Apply first patch (add include)
    if '#include "archipelago/archipelago_client.h"' not in content:
        # Find the includes section
        include_pos = content.find('#include "r_videoscale.h"')
        if include_pos != -1:
            include_pos = content.find('\n', include_pos) + 1
            content = content[:include_pos] + '#include "archipelago/archipelago_client.h"\n' + content[include_pos:]
            print("Added archipelago include to d_main.cpp")
    
    # Apply second patch (add init call)
    if 'Archipelago::AP_Init();' not in content:
        init_pos = content.find('D_DoomInit();')
        if init_pos != -1:
            init_pos = content.find('\n', init_pos) + 1
            content = content[:init_pos] + '\t\n\t// Initialize Archipelago client\n\tArchipelago::AP_Init();\n' + content[init_pos:]
            print("Added AP_Init call to d_main.cpp")
    
    # Apply third patch (add shutdown call)
    if 'Archipelago::AP_Shutdown();' not in content:
        shutdown_pos = content.find('ret = -1;')
        if shutdown_pos != -1:
            shutdown_pos = content.find('\n', shutdown_pos) + 1
            content = content[:shutdown_pos] + '\t}\n\t\n\tArchipelago::AP_Shutdown();\n' + content[shutdown_pos:]
            print("Added AP_Shutdown call to d_main.cpp")
    
    # Apply fourth patch (add process call in game loop)
    if 'Net_ProcessArchipelago();' not in content:
        loop_pos = content.find('// [RH] Use the consoleplayer\'s camera to update sounds')
        if loop_pos != -1:
            # Find the previous closing brace
            brace_pos = content.rfind('}', 0, loop_pos)
            if brace_pos != -1:
                brace_pos = content.find('\n', brace_pos) + 1
                content = content[:brace_pos] + '\t\t\n\t\t// Process Archipelago messages\n\t\tNet_ProcessArchipelago();\n' + content[brace_pos:]
                print("Added Net_ProcessArchipelago call to game loop")
    
    # Write back d_main.cpp
    with open("src/d_main.cpp", 'w') as f:
        f.write(content)
    
    # Apply remaining patches
    applier.apply_patch("d_net_archipelago.patch", "src/d_net.cpp")
    applier.apply_patch("d_net_h_archipelago.patch", "src/d_net.h")
    
    print("\n=== Patch application complete ===")
    print("Backups have been created for all modified files.")
    print("You can now build Selaco with Archipelago support!")

if __name__ == "__main__":
    apply_patches_smart()