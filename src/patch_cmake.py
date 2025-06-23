#!/usr/bin/env python3
"""
Patch CMakeLists.txt to properly include WebSocketPP
Run this from the src directory
"""

import os
import sys

def patch_cmake():
    cmake_file = "CMakeLists.txt"
    
    if not os.path.exists(cmake_file):
        print(f"Error: {cmake_file} not found. Run this script from the src directory.")
        sys.exit(1)
    
    # Read the current CMakeLists.txt
    with open(cmake_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "WEBSOCKETPP_INCLUDE_DIR" in content:
        print("CMakeLists.txt appears to already be patched for WebSocketPP")
        return
    
    # Find where to insert WebSocketPP configuration
    # We'll add it after the archipelago sources definition
    archipelago_marker = "set( ARCHIPELAGO_SOURCES"
    
    if archipelago_marker not in content:
        print("Error: Could not find ARCHIPELAGO_SOURCES in CMakeLists.txt")
        sys.exit(1)
    
    # Find the end of ARCHIPELAGO_SOURCES block
    start_idx = content.find(archipelago_marker)
    # Find the closing parenthesis for this set command
    paren_count = 0
    idx = start_idx
    while idx < len(content):
        if content[idx] == '(':
            paren_count += 1
        elif content[idx] == ')':
            paren_count -= 1
            if paren_count == 0:
                break
        idx += 1
    
    if idx >= len(content):
        print("Error: Could not find end of ARCHIPELAGO_SOURCES")
        sys.exit(1)
    
    # Insert WebSocketPP configuration after ARCHIPELAGO_SOURCES
    insert_pos = idx + 1
    
    websocketpp_config = """

# WebSocketPP configuration for Archipelago
set( WEBSOCKETPP_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../libraries/websocketpp" )

# Add WebSocketPP to include directories
include_directories( ${WEBSOCKETPP_INCLUDE_DIR} )

# WebSocketPP requires Boost ASIO or standalone ASIO
# For now, we'll use the standalone ASIO that comes with WebSocketPP
add_definitions( -DASIO_STANDALONE )
add_definitions( -D_WEBSOCKETPP_CPP11_STL_ )

# Remove easywsclient from the build
list(REMOVE_ITEM ARCHIPELAGO_SOURCES archipelago/easywsclient.cpp archipelago/easywsclient.hpp)
"""
    
    # Insert the configuration
    new_content = content[:insert_pos] + websocketpp_config + content[insert_pos:]
    
    # Backup the original file
    backup_file = cmake_file + ".backup"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Write the patched file
    with open(cmake_file, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully patched {cmake_file}")
    print("\nNext steps:")
    print("1. Delete your build directory to ensure a clean rebuild")
    print("2. Re-run CMake to regenerate the project files")
    print("3. Build the project")

if __name__ == "__main__":
    patch_cmake()