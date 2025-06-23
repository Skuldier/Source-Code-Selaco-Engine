#!/usr/bin/env python3
"""
Fix Net_ProcessArchipelago function scope error in d_net.cpp
This script moves the function definition from inside another function to file scope.
"""

import re
import os
import sys
from pathlib import Path

def find_function_context(content, line_number):
    """
    Find which function contains the given line number.
    Returns the function name and its boundaries.
    """
    lines = content.split('\n')
    
    # Track brace depth to find function boundaries
    brace_depth = 0
    current_function = None
    function_start = None
    
    # Pattern to match function definitions
    func_pattern = r'^\s*(?:static\s+)?(?:void|int|bool)\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?$'
    
    for i, line in enumerate(lines):
        # Check if this is a function definition
        match = re.match(func_pattern, line.strip())
        if match and i < len(lines) - 1 and '{' in lines[i + 1]:
            if brace_depth == 0:
                current_function = match.group(1)
                function_start = i
        
        # Track braces
        brace_depth += line.count('{') - line.count('}')
        
        # Check if we've reached the target line
        if i + 1 == line_number:
            return current_function, function_start, i
        
        # Reset if we exit a function
        if brace_depth == 0 and current_function:
            current_function = None
            function_start = None
    
    return None, None, None

def extract_net_process_archipelago(content):
    """
    Find and extract the Net_ProcessArchipelago function definition.
    Returns the function code and its location.
    """
    # Pattern to find the function definition
    pattern = r'(void\s+Net_ProcessArchipelago\s*\(\s*\)\s*\{[^}]+\})'
    
    # Search for the function
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1), match.start(), match.end()
    
    # Try a more complex pattern for multi-line functions
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'void Net_ProcessArchipelago()' in line or 'void Net_ProcessArchipelago(void)' in line:
            # Found the function start, now find its end
            brace_count = 0
            start_line = i
            start_pos = content.find(line)
            
            for j in range(i, len(lines)):
                brace_count += lines[j].count('{') - lines[j].count('}')
                if brace_count == 0 and j > i:
                    # Found the end
                    end_line = j
                    func_lines = lines[start_line:end_line + 1]
                    func_text = '\n'.join(func_lines)
                    end_pos = start_pos + len('\n'.join(lines[start_line:end_line + 1]))
                    return func_text, start_pos, end_pos
    
    return None, None, None

def fix_net_process_archipelago(filepath):
    """
    Fix the Net_ProcessArchipelago scope issue by moving it to file scope.
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    
    # Find the misplaced function
    func_text, start_pos, end_pos = extract_net_process_archipelago(content)
    
    if not func_text:
        print("Error: Could not find Net_ProcessArchipelago function definition")
        return False
    
    print(f"Found Net_ProcessArchipelago function ({len(func_text)} characters)")
    
    # Determine where it's currently located
    line_number = content[:start_pos].count('\n') + 1
    print(f"Function is currently at line {line_number}")
    
    # Check if it's inside another function
    lines_before = content[:start_pos].split('\n')
    brace_depth = 0
    inside_function = False
    
    for line in lines_before:
        brace_depth += line.count('{') - line.count('}')
    
    if brace_depth > 0:
        inside_function = True
        print("Function is inside another function (brace depth: {})".format(brace_depth))
    
    if inside_function:
        # Remove the function from its current location
        content = content[:start_pos] + content[end_pos:]
        
        # Clean up any extra blank lines left behind
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        # Find a good place to insert it at file scope
        # Look for the last function definition in the file
        function_pattern = r'^\s*(?:static\s+)?(?:void|int|bool)\s+\w+\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?\s*\{[^}]+\}'
        
        # Find all complete functions
        last_function_end = 0
        for match in re.finditer(function_pattern, content, re.MULTILINE | re.DOTALL):
            # Verify this is at file scope (brace depth 0)
            depth = content[:match.start()].count('{') - content[:match.start()].count('}')
            if depth == 0:
                last_function_end = match.end()
        
        # Insert after the last file-scope function
        if last_function_end > 0:
            # Add some spacing and the function
            insert_pos = last_function_end
            
            # Properly format the function with nice spacing
            formatted_func = f"\n\n//==========================================================================\n//\n// Net_ProcessArchipelago\n//\n// Process Archipelago messages in the main game loop\n//\n//==========================================================================\n\n{func_text.strip()}\n"
            
            content = content[:insert_pos] + formatted_func + content[insert_pos:]
            print(f"Moved function to file scope after position {insert_pos}")
        else:
            # If no functions found, add at the end of the file
            content = content.rstrip() + formatted_func + "\n"
            print("Added function at the end of the file")
        
        # Now ensure the function is being called somewhere
        # Check if there's already a call to it
        if 'Net_ProcessArchipelago();' not in content:
            print("\nWarning: No call to Net_ProcessArchipelago() found in the file.")
            print("You may need to add a call to this function in your main network processing loop.")
            print("Look for functions like NetUpdate() or D_CheckNetGame() and add the call there.")
    else:
        print("Function is already at file scope - no changes needed")
        return False
    
    # Save the file
    if content != original_content:
        # Create backup
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"\nCreated backup at: {backup_path}")
        
        # Write the fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully patched {filepath}")
        return True
    else:
        print("No changes were needed")
        return False

def analyze_file(filepath, target_line=None):
    """
    Analyze the file structure around the problematic line.
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    print("File Analysis:")
    print("-" * 60)
    
    if target_line and target_line <= len(lines):
        # Show context around the target line
        start = max(0, target_line - 10)
        end = min(len(lines), target_line + 10)
        
        print(f"\nContext around line {target_line}:")
        print("-" * 40)
        
        for i in range(start, end):
            prefix = ">>> " if i + 1 == target_line else "    "
            print(f"{i+1:4d} {prefix}{lines[i]}")
        
        # Analyze brace depth at this point
        brace_depth = 0
        for i in range(target_line):
            brace_depth += lines[i].count('{') - lines[i].count('}')
        
        print(f"\nBrace depth at line {target_line}: {brace_depth}")
        
        if brace_depth > 0:
            print("This line is inside a function or block!")
            
            # Try to find which function
            func_name, func_start, _ = find_function_context(content, target_line)
            if func_name:
                print(f"Inside function: {func_name} (starting at line {func_start + 1})")

def main():
    if len(sys.argv) < 2:
        print("Net_ProcessArchipelago Scope Fix Script")
        print("=" * 60)
        print("\nThis script fixes the function scope error in d_net.cpp")
        print("\nUsage:")
        print(f"  {sys.argv[0]} <path_to_d_net.cpp> [--analyze [line_number]]")
        print("\nExamples:")
        print(f"  {sys.argv[0]} C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/d_net.cpp")
        print(f"  {sys.argv[0]} d_net.cpp --analyze 2935")
        print("\nOptions:")
        print("  --analyze [line]    Show file structure (optionally around specific line)")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if "--analyze" in sys.argv:
        line_num = None
        idx = sys.argv.index("--analyze")
        if idx + 1 < len(sys.argv):
            try:
                line_num = int(sys.argv[idx + 1])
            except ValueError:
                pass
        
        print(f"\nAnalyzing {filepath}...")
        analyze_file(filepath, line_num)
    else:
        print(f"\nProcessing {filepath}...")
        if fix_net_process_archipelago(filepath):
            print("\n✓ File successfully fixed!")
            print("\nNext steps:")
            print("1. Rebuild your project")
            print("2. If you get linker errors about Net_ProcessArchipelago not being called,")
            print("   you'll need to add a call to it in your main network loop")
            print("3. Look for functions like NetUpdate() or I_StartTic() to add the call")
        else:
            print("\n! Could not fix the issue automatically")
            print("You may need to manually move the function to file scope")

if __name__ == "__main__":
    main()