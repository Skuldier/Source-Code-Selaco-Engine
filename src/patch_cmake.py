#!/usr/bin/env python3
"""
Fix CMakeLists.txt for proper WebSocketPP include paths
Run this from the src directory
"""

import os
import sys
import re

def fix_cmake():
    cmake_file = "CMakeLists.txt"
    
    if not os.path.exists(cmake_file):
        print(f"Error: {cmake_file} not found. Run this script from the src directory.")
        sys.exit(1)
    
    # Read the current CMakeLists.txt
    with open(cmake_file, 'r') as f:
        content = f.read()
    
    # Backup the original file
    backup_file = cmake_file + ".backup_websocketpp"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Check if ARCHIPELAGO_SOURCES is defined
    if "ARCHIPELAGO_SOURCES" not in content:
        print("Error: ARCHIPELAGO_SOURCES not found in CMakeLists.txt")
        print("Make sure archipelago sources are defined first")
        sys.exit(1)
    
    # Remove easywsclient files from ARCHIPELAGO_SOURCES if present
    content = re.sub(r'archipelago/easywsclient\.cpp\s*', '', content)
    content = re.sub(r'archipelago/easywsclient\.hpp\s*', '', content)
    
    # Check if WebSocketPP is already configured
    if "WEBSOCKETPP configuration" in content:
        print("Updating existing WebSocketPP configuration...")
        # Remove old configuration
        pattern = r'# WebSocketPP configuration.*?(?=\n(?:set\(|if\(|#|$))'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Find where to insert WebSocketPP configuration
    # Insert after ARCHIPELAGO_SOURCES block
    archipelago_pattern = r'(set\s*\(\s*ARCHIPELAGO_SOURCES[^)]+\))'
    match = re.search(archipelago_pattern, content, re.DOTALL)
    
    if not match:
        print("Error: Could not find ARCHIPELAGO_SOURCES block")
        sys.exit(1)
    
    insert_pos = match.end()
    
    # WebSocketPP configuration with correct paths
    websocketpp_config = """

# WebSocketPP configuration for Archipelago
# IMPORTANT: The include directory must be the parent of websocketpp folder
# because WebSocketPP uses includes like <websocketpp/config/asio_client.hpp>
set( WEBSOCKETPP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../libraries" )

# Add include directories
include_directories( ${WEBSOCKETPP_ROOT} )

# WebSocketPP requires C++11 features
add_definitions( -D_WEBSOCKETPP_CPP11_STL_ )

# Disable threading for simpler implementation (can be enabled later if needed)
add_definitions( -D_WEBSOCKETPP_NO_THREADING_ )

# Use standalone ASIO (no Boost dependency)
add_definitions( -DASIO_STANDALONE )

# Windows-specific settings
if( WIN32 )
    add_definitions( -D_WIN32_WINNT=0x0601 )  # Windows 7 or later
    add_definitions( -DWIN32_LEAN_AND_MEAN )
    add_definitions( -DNOMINMAX )              # Prevent Windows.h from defining min/max macros
endif()
"""
    
    # Insert the configuration
    new_content = content[:insert_pos] + websocketpp_config + content[insert_pos:]
    
    # Write the updated file
    with open(cmake_file, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully updated {cmake_file}")
    print("\nWebSocketPP include path set to: libraries/")
    print("This allows includes like <websocketpp/config/asio_client.hpp> to work correctly")
    print("\nNext steps:")
    print("1. Delete your build directory: rm -rf ../build")
    print("2. Create a new build directory: mkdir ../build && cd ../build")
    print("3. Run CMake: cmake ..")
    print("4. Build the project: make (or use Visual Studio)")

if __name__ == "__main__":
    fix_cmake()