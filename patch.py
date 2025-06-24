#!/usr/bin/env python3
"""
Quick fix for the AP_Tick namespace error
This is the simplest possible fix
"""

import os

def quick_fix():
    filepath = "src/d_main.cpp"
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    # Read the file
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Find and fix the problematic line
    fixed = False
    for i, line in enumerate(lines):
        if "Archipelago::AP_Tick();" in line:
            # Replace with simple call
            lines[i] = line.replace("Archipelago::AP_Tick();", "AP_Tick();")
            fixed = True
            print(f"Fixed line {i+1}: Changed 'Archipelago::AP_Tick();' to 'AP_Tick();'")
            break
    
    if not fixed:
        print("Error: Could not find 'Archipelago::AP_Tick();' in the file")
        return False
    
    # Add forward declaration if not present
    declaration = "extern void AP_Tick();\n"
    declaration_exists = any(declaration.strip() in line for line in lines)
    
    if not declaration_exists:
        # Find a good place to add it (after includes)
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith("#include") and i > insert_pos:
                insert_pos = i + 1
            elif insert_pos > 0 and not line.startswith("#include") and line.strip():
                # We've passed all includes
                break
        
        # Insert the declaration
        lines.insert(insert_pos, f"\n// Forward declaration for Archipelago tick function\n{declaration}")
        print(f"Added forward declaration at line {insert_pos}")
    
    # Write the file back
    with open(filepath, 'w') as f:
        f.writelines(lines)
    
    print(f"Successfully fixed {filepath}")
    return True

if __name__ == "__main__":
    print("Quick Fix for AP_Tick Namespace Error")
    print("=====================================\n")
    
    if quick_fix():
        print("\n✓ Fix applied successfully!")
        print("The error should now be resolved. Please rebuild the project.")
    else:
        print("\n✗ Fix failed. Please apply the fix manually:")
        print("1. In src/d_main.cpp, change 'Archipelago::AP_Tick();' to 'AP_Tick();'")
        print("2. Add 'extern void AP_Tick();' after the includes")