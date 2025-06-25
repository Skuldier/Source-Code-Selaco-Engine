#!/usr/bin/env python3
"""
Simple fix - remove Net_ProcessArchipelago from d_main.cpp
"""

import os

def remove_duplicate():
    dmain_path = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine\src\d_main.cpp"
    
    print("🔧 REMOVING DUPLICATE NET_PROCESSARCHIPELAGO")
    print("=" * 60)
    
    # Read d_main.cpp
    with open(dmain_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find Net_ProcessArchipelago
    found_indices = []
    in_function = False
    brace_count = 0
    func_start = -1
    
    for i, line in enumerate(lines):
        if 'void Net_ProcessArchipelago' in line:
            print(f"Found at line {i+1}: {line.strip()}")
            func_start = i
            in_function = True
            brace_count = 0
            found_indices.append(i)
        
        if in_function:
            if '{' in line:
                brace_count += line.count('{')
            if '}' in line:
                brace_count -= line.count('}')
                if brace_count == 0 and func_start >= 0:
                    # Found end of function
                    for j in range(func_start, i + 1):
                        found_indices.append(j)
                    in_function = False
    
    if found_indices:
        print(f"\nRemoving {len(set(found_indices))} lines...")
        
        # Remove lines (in reverse order to maintain indices)
        for i in sorted(set(found_indices), reverse=True):
            lines[i] = ''  # Just empty the line instead of removing
        
        # Write back
        with open(dmain_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("✅ Removed Net_ProcessArchipelago from d_main.cpp")
    else:
        print("✓ Net_ProcessArchipelago not found in d_main.cpp")
    
    print("\n📋 Net_ProcessArchipelago should only be in d_net.cpp")
    print("\n🔨 Now rebuild:")
    print("  cd build")
    print("  cmake --build . --config Debug")

if __name__ == "__main__":
    remove_duplicate()