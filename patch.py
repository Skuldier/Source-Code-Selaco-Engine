#!/usr/bin/env python3
"""
Remove the error at line 4305
"""

import os

def remove_error():
    dmain_path = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine\src\d_main.cpp"
    
    print("🔧 REMOVING ERROR AT LINE 4305")
    print("=" * 60)
    
    # Read the file
    with open(dmain_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines in file: {len(lines)}")
    
    # Show what's around line 4305
    if len(lines) > 4304:
        print("\nContent around line 4305:")
        for i in range(max(0, 4300), min(len(lines), 4310)):
            print(f"  {i+1}: {lines[i].rstrip()}")
        
        # Find and remove the CCMD block
        if 'CCMD' in lines[4304]:  # Line 4305 is index 4304
            print("\nFound CCMD at line 4305, removing it...")
            
            # Find the end of the CCMD block
            start_line = 4304
            end_line = start_line
            brace_count = 0
            
            for i in range(start_line, min(len(lines), start_line + 100)):
                if '{' in lines[i]:
                    brace_count += lines[i].count('{')
                if '}' in lines[i]:
                    brace_count -= lines[i].count('}')
                    if brace_count == 0 and i > start_line:
                        end_line = i
                        break
            
            # Remove the lines
            print(f"Removing lines {start_line+1} to {end_line+1}")
            for i in range(end_line, start_line - 1, -1):
                lines.pop(i)
            
            # Save the file
            with open(dmain_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print("✅ Removed problematic CCMD!")
    else:
        print("❌ File doesn't have that many lines!")
    
    print("\n🔨 Now rebuild:")
    print("  cd build")
    print("  cmake --build . --config Debug")
    
    print("\n💡 The original ap_connect commands should work if")
    print("   archipelago_commands.cpp is being compiled.")
    print("   If not, use the test commands file approach.")

if __name__ == "__main__":
    remove_error()