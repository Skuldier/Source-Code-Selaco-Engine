#!/usr/bin/env python3
"""
Final fix for Net_ProcessArchipelago placement in d_net.cpp
This script carefully extracts the function from within Net_SkipCommand's switch statement
and places it at the correct file scope location.
"""

import re
import os
import sys
from pathlib import Path

def find_net_process_archipelago_in_switch(content):
    """
    Find Net_ProcessArchipelago function that's mistakenly placed inside a switch statement.
    This is more complex because it's nested within case statements.
    """
    # Look for the function definition with its distinctive comment block
    pattern = r'(//=+\s*\n//\s*\n//\s*Net_ProcessArchipelago\s*\n//\s*\n//[^\n]*\n//\s*\n//=+\s*\n\s*void\s+Net_ProcessArchipelago\s*\(\s*\)\s*\{[^}]+\})'
    
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1), match.start(), match.end()
    
    # Fallback: simpler pattern if comments are different
    pattern2 = r'(void\s+Net_ProcessArchipelago\s*\(\s*\)\s*\{[^}]+\})'
    match = re.search(pattern2, content)
    if match:
        return match.group(1), match.start(), match.end()
    
    return None, None, None

def fix_broken_switch_statement(content, start_pos, end_pos):
    """
    Fix the switch statement that was broken by the misplaced function.
    The function was inserted between related code blocks, breaking the if-else chain.
    """
    # Look backwards from start_pos to find the context
    before_func = content[:start_pos]
    after_func = content[end_pos:]
    
    # Find the last few lines before the function to understand context
    lines_before = before_func.split('\n')[-10:]  # Get last 10 lines
    lines_after = after_func.split('\n')[:10]     # Get first 10 lines
    
    # Check if we're in the middle of a case statement with if-else
    # Looking for pattern like:
    # case CVAR_String:
    #     skip += strlen ((char *)(*stream + skip)) + 1;
    #     break;
    # }
    # [FUNCTION WAS HERE]
    # }
    # else
    # {
    #     skip += 1;
    # }
    
    # The function appears to have been inserted after a closing brace
    # and before the else statement, breaking the if-else structure
    
    # Remove the function and any extra braces
    fixed_content = before_func
    
    # Check if there's a broken else statement after
    else_pattern = r'^\s*\}\s*else\s*\{'
    if re.match(else_pattern, after_func.lstrip()):
        # We need to reconnect the if-else properly
        # Remove any extra closing braces before the function
        fixed_content = fixed_content.rstrip()
        if fixed_content.endswith('}'):
            # Check if this is an extra brace by counting
            brace_count = fixed_content.count('{') - fixed_content.count('}')
            if brace_count < 0:  # More closing than opening
                # Remove the last closing brace
                last_brace = fixed_content.rfind('}')
                fixed_content = fixed_content[:last_brace] + fixed_content[last_brace+1:]
        
        # Add the else part back
        fixed_content += '\n' + after_func.lstrip()
    else:
        # Just append the rest
        fixed_content += after_func
    
    return fixed_content

def find_good_insertion_point(content):
    """
    Find a good place to insert Net_ProcessArchipelago at file scope.
    Look for the end of Net_SkipCommand or before Net_GetLatency.
    """
    # First choice: After Net_SkipCommand
    net_skip_pattern = r'void\s+Net_SkipCommand\s*\([^)]*\)\s*\{.*?\n\}\s*\n'
    match = re.search(net_skip_pattern, content, re.DOTALL)
    if match:
        return match.end()
    
    # Second choice: Before Net_GetLatency
    net_latency_pattern = r'(//[^\n]*\n)*int\s+Net_GetLatency\s*\('
    match = re.search(net_latency_pattern, content)
    if match:
        # Back up to include any comment block
        pos = match.start()
        # Look backwards for the start of the comment block
        while pos > 0 and content[pos-1:pos] == '\n':
            pos -= 1
        return pos
    
    # Third choice: Before the CCMD section
    ccmd_pattern = r'//=+\s*\n//\s*\n//\s*\n//\s*\n//=+\s*\n\s*//[^\n]*"ping"'
    match = re.search(ccmd_pattern, content)
    if match:
        return match.start()
    
    # Last resort: End of file
    return len(content)

def fix_net_process_archipelago_final(filepath):
    """
    Final fix for Net_ProcessArchipelago placement.
    This version handles the complex switch statement structure.
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    
    # Find the misplaced function
    func_text, start_pos, end_pos = find_net_process_archipelago_in_switch(content)
    
    if not func_text:
        print("Net_ProcessArchipelago function not found in the expected location.")
        print("It may have already been fixed or is in a different location.")
        return False
    
    print(f"Found Net_ProcessArchipelago at position {start_pos}-{end_pos}")
    print("Function appears to be inside Net_SkipCommand's switch statement")
    
    # Step 1: Remove the function and fix the broken switch statement
    fixed_content = fix_broken_switch_statement(content, start_pos, end_pos)
    
    # Step 2: Find a good place to insert the function
    insertion_point = find_good_insertion_point(fixed_content)
    
    # Step 3: Insert the function at the correct location
    # Format it nicely with proper spacing
    formatted_func = f"\n{func_text}\n\n"
    
    final_content = (
        fixed_content[:insertion_point] + 
        formatted_func + 
        fixed_content[insertion_point:]
    )
    
    # Step 4: Verify and clean up
    # Remove any double blank lines
    final_content = re.sub(r'\n\n\n+', '\n\n', final_content)
    
    # Save the file
    if final_content != original_content:
        # Create backup
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"\nCreated backup at: {backup_path}")
        
        # Write the fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"Successfully patched {filepath}")
        print(f"\nFunction moved from position {start_pos} to position {insertion_point}")
        return True
    else:
        print("No changes were needed")
        return False

def analyze_switch_structure(filepath, around_line=2898):
    """
    Analyze the structure around the problematic line to understand the issue.
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Show context around the target line
    start = max(0, around_line - 50)
    end = min(len(lines), around_line + 50)
    
    print("Analysis of file structure:")
    print("-" * 80)
    
    # Track brace depth and switch/case structure
    brace_depth = 0
    in_switch = False
    case_count = 0
    
    for i in range(start):
        brace_depth += lines[i].count('{') - lines[i].count('}')
        if 'switch' in lines[i]:
            in_switch = True
    
    print(f"Brace depth at line {start}: {brace_depth}")
    print(f"Inside switch: {in_switch}")
    print("\nContext around line {}:\n".format(around_line))
    
    for i in range(start, end):
        line_num = i + 1
        line = lines[i].rstrip()
        
        # Update tracking
        if '{' in line:
            brace_depth += line.count('{')
        if '}' in line:
            brace_depth -= line.count('}')
        if 'case ' in line:
            case_count += 1
        
        # Highlight important lines
        prefix = ""
        if line_num == around_line:
            prefix = ">>> "
        elif 'Net_ProcessArchipelago' in line:
            prefix = "!!! "
        elif 'case ' in line or 'switch' in line:
            prefix = "SW  "
        elif 'else' in line:
            prefix = "ELS "
        
        print(f"{line_num:4d} {prefix}[{brace_depth:2d}] {line}")

def main():
    if len(sys.argv) < 2:
        print("Net_ProcessArchipelago Final Fix Script")
        print("=" * 80)
        print("\nThis script fixes the specific issue where Net_ProcessArchipelago")
        print("was placed inside the Net_SkipCommand switch statement.")
        print("\nUsage:")
        print(f"  {sys.argv[0]} <path_to_d_net.cpp> [--analyze]")
        print("\nExamples:")
        print(f"  {sys.argv[0]} C:/Users/Skuldier/Documents/Source-Code-Selaco-Engine/src/d_net.cpp")
        print(f"  {sys.argv[0]} d_net.cpp --analyze")
        print("\nOptions:")
        print("  --analyze    Analyze the file structure without making changes")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if "--analyze" in sys.argv:
        print(f"\nAnalyzing {filepath}...")
        analyze_switch_structure(filepath, 2898)
        print("\nRun without --analyze to apply the fix")
    else:
        print(f"\nProcessing {filepath}...")
        print("This will fix the Net_ProcessArchipelago placement issue")
        
        if fix_net_process_archipelago_final(filepath):
            print("\n✓ File successfully fixed!")
            print("\nThe function has been moved to file scope.")
            print("The switch statement in Net_SkipCommand has been repaired.")
            print("\nNext steps:")
            print("1. Rebuild your project")
            print("2. Make sure Net_ProcessArchipelago is called from TryRunTics")
            print("3. Test your Archipelago integration")
        else:
            print("\n! Could not complete the fix")
            print("You may need to manually edit the file")
            print("\nManual fix instructions:")
            print("1. Find 'void Net_ProcessArchipelago()' around line 2898")
            print("2. Cut the entire function (including comments)")
            print("3. Find the end of Net_SkipCommand function")
            print("4. Paste Net_ProcessArchipelago after Net_SkipCommand")
            print("5. Fix the broken switch statement by removing extra braces")

if __name__ == "__main__":
    main()