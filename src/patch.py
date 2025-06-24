#!/usr/bin/env python3
"""
Clean up CMakeLists.txt for Archipelago integration.
Removes WebSocketPP configuration and simplifies for simple socket implementation.
"""

import re
import sys
from datetime import datetime

def clean_cmake_file(filepath):
    """Clean up the CMakeLists.txt file."""
    print(f"Cleaning {filepath}...")
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup the original
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Backup saved to: {backup_path}")
    
    # List of patterns to remove (WebSocketPP related)
    patterns_to_remove = [
        # Remove all the duplicate WebSocketPP configurations
        r'# ASIO and WebSocketPP configuration for Archipelago.*?endif\(\)',
        r'# IMPORTANT: The include directory must be.*?endif\(\)',
        r'set\( WEBSOCKETPP_INCLUDE_DIR.*?\)',
        r'# Add WebSocketPP to include directories.*?list\(REMOVE_ITEM ARCHIPELAGO_SOURCES \)',
        # Remove duplicate include_directories for WebSocketPP
        r'include_directories\(\s*\$\{CMAKE_CURRENT_SOURCE_DIR\}/libraries/websocketpp.*?\)',
        r'include_directories\(\s*\$\{CMAKE_CURRENT_SOURCE_DIR\}/libraries/asio/include.*?\)',
        # Remove standalone ASIO/WebSocketPP definitions that are duplicated
        r'if\(NOT Boost_FOUND\).*?endif\(\)',
        # Remove any remaining WebSocketPP specific defines
        r'add_definitions\(\s*-DASIO_STANDALONE\s*\)',
        r'add_definitions\(\s*-D_WEBSOCKETPP_CPP11_STL_\s*\)',
        r'add_definitions\(\s*-D_WEBSOCKETPP_CPP11_FUNCTIONAL_\s*\)',
        r'add_definitions\(\s*-D_WEBSOCKETPP_NO_TLS_\s*\)',
        r'add_definitions\(\s*-D_WEBSOCKETPP_NO_THREADING_\s*\)',
        r'add_definitions\(\s*-D_WEBSOCKETPP_MINGW_THREAD_\s*\)',
    ]
    
    # Apply removals
    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.MULTILINE)
    
    # Clean up excessive newlines
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    # Find the Archipelago sources section and ensure it's clean
    archipelago_pattern = r'# Archipelago integration\s*set\(\s*ARCHIPELAGO_SOURCES[^)]+\)'
    archipelago_match = re.search(archipelago_pattern, content, re.DOTALL)
    
    if archipelago_match:
        # Replace with clean version
        clean_archipelago = """# Archipelago integration
set( ARCHIPELAGO_SOURCES
\tarchipelago/archipelago_client.cpp
\tarchipelago/archipelago_ccmds.cpp 
\tarchipelago/archipelago_client.h)"""
        
        content = re.sub(archipelago_pattern, clean_archipelago, content, flags=re.DOTALL)
    
    # Remove the archipelago directory from include_directories if it's duplicated
    # Find the main include_directories block
    include_pattern = r'include_directories\(\s*BEFORE\s*\.[^)]+\)'
    include_match = re.search(include_pattern, content, re.DOTALL)
    
    if include_match:
        include_block = include_match.group(0)
        # Ensure archipelago is only listed once
        if include_block.count('archipelago') > 1:
            # Remove duplicates
            lines = include_block.split('\n')
            seen_archipelago = False
            new_lines = []
            for line in lines:
                if 'archipelago' in line:
                    if not seen_archipelago:
                        new_lines.append(line)
                        seen_archipelago = True
                else:
                    new_lines.append(line)
            new_include_block = '\n'.join(new_lines)
            content = content.replace(include_block, new_include_block)
    
    # Add a clean section for any network libraries needed by simple socket implementation
    # Find where to insert (after ARCHIPELAGO_SOURCES definition)
    archipelago_end = content.find('set( ARCHIPELAGO_SOURCES')
    if archipelago_end != -1:
        # Find the end of the ARCHIPELAGO_SOURCES block
        end_paren = content.find(')', archipelago_end)
        if end_paren != -1:
            insert_pos = end_paren + 1
            
            # Add simple socket dependencies (already handled by PROJECT_LIBRARIES on Windows)
            network_config = """

# Network configuration for Archipelago simple socket client
# Windows sockets are already linked via ws2_32 in PROJECT_LIBRARIES
# No additional configuration needed for the simple implementation
"""
            content = content[:insert_pos] + network_config + content[insert_pos:]
    
    # Write the cleaned content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Successfully cleaned {filepath}")
    print("\nRemoved:")
    print("- All WebSocketPP configurations")
    print("- Duplicate ASIO definitions")
    print("- Conflicting include directories")
    print("\nThe CMakeLists.txt is now configured for the simple socket implementation.")

def main():
    """Main function."""
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "CMakeLists.txt"
    
    try:
        clean_cmake_file(filepath)
    except FileNotFoundError:
        print(f"Error: {filepath} not found!")
        print("Usage: python clean_cmake_archipelago.py [path/to/CMakeLists.txt]")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()