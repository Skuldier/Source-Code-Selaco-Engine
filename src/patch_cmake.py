#!/usr/bin/env python3
"""
Fix CMakeLists.txt for proper ASIO and WebSocketPP configuration
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
    backup_file = cmake_file + ".backup_asio"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Remove any existing WebSocketPP configuration
    content = re.sub(r'# WebSocketPP configuration.*?(?=\n(?:set\(|if\(|#[^#]|$))', '', content, flags=re.DOTALL)
    
    # Find where to insert the configuration
    archipelago_pattern = r'(set\s*\(\s*ARCHIPELAGO_SOURCES[^)]+\))'
    match = re.search(archipelago_pattern, content, re.DOTALL)
    
    if not match:
        print("Error: Could not find ARCHIPELAGO_SOURCES block")
        sys.exit(1)
    
    insert_pos = match.end()
    
    # ASIO and WebSocketPP configuration
    config = """

# ASIO and WebSocketPP configuration for Archipelago
# ASIO is required by WebSocketPP for networking
set( ASIO_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../libraries/asio/asio/include" )
set( WEBSOCKETPP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../libraries" )

# Add include directories
include_directories( 
    ${WEBSOCKETPP_ROOT}
    ${ASIO_INCLUDE_DIR}
)

# ASIO and WebSocketPP definitions
add_definitions( 
    -DASIO_STANDALONE                    # Use standalone ASIO (not Boost)
    -D_WEBSOCKETPP_CPP11_STL_            # Use C++11 features
    -D_WEBSOCKETPP_CPP11_FUNCTIONAL_    # Use std::function
)

# Windows-specific settings
if( WIN32 )
    add_definitions( 
        -D_WIN32_WINNT=0x0601           # Windows 7 or later
        -DWIN32_LEAN_AND_MEAN           # Exclude rarely-used Windows headers
        -DNOMINMAX                      # Don't define min/max macros
        -D_WEBSOCKETPP_MINGW_THREAD_    # Use MinGW threads if MinGW
    )
endif()

# Disable SSL/TLS support in WebSocketPP (we don't need it for Archipelago)
add_definitions( -D_WEBSOCKETPP_NO_TLS_ )

# Set C++11 standard if not already set
if(NOT CMAKE_CXX_STANDARD)
    set(CMAKE_CXX_STANDARD 11)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()
"""
    
    # Insert the configuration
    new_content = content[:insert_pos] + config + content[insert_pos:]
    
    # Write the updated file
    with open(cmake_file, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully updated {cmake_file}")
    print("\nConfiguration added:")
    print("- ASIO include path: libraries/asio/asio/include")
    print("- WebSocketPP include path: libraries/")
    print("- Using standalone ASIO (no Boost dependency)")
    print("- C++11 features enabled")
    print("\nNext steps:")
    print("1. Run the download_asio.py script to install ASIO")
    print("2. Delete your build directory: rm -rf ../build")
    print("3. Create a new build directory: mkdir ../build && cd ../build")
    print("4. Run CMake: cmake ..")
    print("5. Build the project")

if __name__ == "__main__":
    fix_cmake()