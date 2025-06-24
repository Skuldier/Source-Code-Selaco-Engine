#!/usr/bin/env python3
"""
Patch script to fix the WebSocket key generation bug in archipelago_client.cpp
This fixes the incomplete random distribution line that's causing the crash.
"""

import os
import sys
import re

def patch_websocket_key_generation(filepath):
    """Fix the incomplete random distribution line in generate_websocket_key()"""
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find the broken line
    pattern = r'std::uniform_int_distribution<>\s*dis\s*\(\s*0\s*,\s*2\s*$'
    
    # Check if the issue exists
    if re.search(pattern, content, re.MULTILINE):
        print(f"Found incomplete random distribution line in {filepath}")
        
        # Fix the line - should be (0, 255) for byte generation
        fixed_content = re.sub(
            pattern,
            'std::uniform_int_distribution<> dis(0, 255);',
            content,
            flags=re.MULTILINE
        )
        
        # Also ensure the complete function is correct
        # Look for the generate_websocket_key function and fix it completely
        websocket_key_pattern = r'(std::string generate_websocket_key\(\)\s*\{[^}]*?)std::uniform_int_distribution<>\s*dis\s*\(\s*0\s*,\s*2[^;]*'
        
        if re.search(websocket_key_pattern, content, re.DOTALL):
            fixed_content = re.sub(
                websocket_key_pattern,
                r'\1std::uniform_int_distribution<> dis(0, 255)',
                fixed_content,
                flags=re.DOTALL
            )
        
        # Write the fixed content back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"✓ Fixed WebSocket key generation in {filepath}")
        return True
    else:
        print(f"WebSocket key generation appears to be correct in {filepath}")
        
        # Let's also check for the complete function to ensure it's properly implemented
        if 'generate_websocket_key' in content:
            # Extract the function to verify it's complete
            func_match = re.search(
                r'std::string generate_websocket_key\(\)\s*\{([^}]+)\}',
                content,
                re.DOTALL
            )
            if func_match:
                func_body = func_match.group(1)
                if 'base64_encode' in func_body and 'return' in func_body:
                    print("✓ generate_websocket_key function appears complete")
                else:
                    print("⚠ Warning: generate_websocket_key function may be incomplete")
        
        return True

def find_archipelago_files(search_dir):
    """Find all archipelago_client.cpp files in the directory tree"""
    files = []
    for root, dirs, filenames in os.walk(search_dir):
        for filename in filenames:
            if filename == 'archipelago_client.cpp':
                files.append(os.path.join(root, filename))
    return files

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_websocket_key_generation.py <path_to_src_directory>")
        print("Example: python fix_websocket_key_generation.py ./src")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    
    # Find all archipelago_client.cpp files
    cpp_files = find_archipelago_files(src_dir)
    
    if not cpp_files:
        print(f"No archipelago_client.cpp files found in {src_dir}")
        sys.exit(1)
    
    print(f"Found {len(cpp_files)} archipelago_client.cpp file(s):")
    for f in cpp_files:
        print(f"  - {f}")
    
    print("\nPatching files...")
    success_count = 0
    for cpp_file in cpp_files:
        if patch_websocket_key_generation(cpp_file):
            success_count += 1
    
    print(f"\n✓ Successfully processed {success_count}/{len(cpp_files)} files")
    
    # Additional check for the base64_encode function
    print("\nChecking base64_encode implementation...")
    for cpp_file in cpp_files:
        with open(cpp_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'base64_encode' in content:
                # Check if the function looks complete
                base64_match = re.search(
                    r'std::string base64_encode\([^)]+\)\s*\{([^}]+)\}',
                    content,
                    re.DOTALL
                )
                if base64_match:
                    func_body = base64_match.group(1)
                    if func_body.count('result.push_back') >= 4 and 'return result' in func_body:
                        print(f"✓ base64_encode appears complete in {cpp_file}")
                    else:
                        print(f"⚠ Warning: base64_encode may be incomplete in {cpp_file}")

if __name__ == "__main__":
    main()