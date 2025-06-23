#!/usr/bin/env python3
"""
Patch WebSocket implementation to use proper includes
"""

import os
import sys

def patch_archipelago_client(filepath):
    """Fix the archipelago_client.cpp file includes"""
    
    print(f"Patching {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix the includes section
    replacements = [
        # Fix websocketpp includes
        ('#include <websocketpp/config/asio_no_tls_client.hpp>', 
         '#include "websocketpp/config/asio_no_tls_client.hpp"'),
        ('#include <websocketpp/client.hpp>', 
         '#include "websocketpp/client.hpp"'),
         
        # Fix rapidjson includes  
        ('#include <rapidjson/document.h>',
         '#include "rapidjson/document.h"'),
        ('#include <rapidjson/writer.h>',
         '#include "rapidjson/writer.h"'),
        ('#include <rapidjson/stringbuffer.h>',
         '#include "rapidjson/stringbuffer.h"'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Also ensure we have the proper WebSocket implementation
    if 'websocketpp::lib::error_code' in content and 'using websocketpp::lib::error_code;' not in content:
        # Add the using declaration after includes
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('#include') or line.strip().startswith('//'):
                insert_pos = i + 1
            else:
                break
        
        lines.insert(insert_pos, '')
        lines.insert(insert_pos + 1, '// WebSocketPP namespace imports')
        lines.insert(insert_pos + 2, 'using websocketpp::lib::error_code;')
        lines.insert(insert_pos + 3, 'using websocketpp::lib::placeholders::_1;')
        lines.insert(insert_pos + 4, 'using websocketpp::lib::placeholders::_2;')
        lines.insert(insert_pos + 5, '')
        
        content = '\n'.join(lines)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Patched {filepath} successfully")

def patch_cmake_lists(filepath):
    """Update CMakeLists.txt to properly link WebSocketPP"""
    
    print(f"Checking {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if WebSocketPP is already configured
    if 'websocketpp' not in content.lower():
        print("Adding WebSocketPP configuration to CMakeLists.txt...")
        
        # Find where to insert WebSocketPP configuration
        lines = content.split('\n')
        insert_pos = -1
        
        # Look for the archipelago sources section
        for i, line in enumerate(lines):
            if 'ARCHIPELAGO_SOURCES' in line:
                insert_pos = i - 1
                break
        
        if insert_pos > 0:
            websocketpp_config = [
                '',
                '# WebSocketPP configuration',
                'find_package(Threads REQUIRED)',
                'find_package(Boost COMPONENTS system QUIET)',
                '',
                'if(NOT Boost_FOUND)',
                '    message(STATUS "Boost not found, using standalone ASIO")',
                '    add_definitions(-DASIO_STANDALONE)',
                'endif()',
                '',
                'include_directories(',
                '    ${CMAKE_CURRENT_SOURCE_DIR}/libraries/websocketpp',
                '    ${CMAKE_CURRENT_SOURCE_DIR}/libraries/asio/include',
                ')',
                ''
            ]
            
            for line in reversed(websocketpp_config):
                lines.insert(insert_pos, line)
            
            content = '\n'.join(lines)
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            print("Updated CMakeLists.txt with WebSocketPP configuration")

def main():
    if len(sys.argv) > 1:
        src_dir = sys.argv[1]
    else:
        src_dir = "src"
    
    # Patch archipelago_client.cpp
    archipelago_file = os.path.join(src_dir, "archipelago", "archipelago_client.cpp")
    if os.path.exists(archipelago_file):
        patch_archipelago_client(archipelago_file)
    else:
        print(f"Warning: {archipelago_file} not found")
    
    # Check CMakeLists.txt
    cmake_file = os.path.join(src_dir, "CMakeLists.txt")
    if os.path.exists(cmake_file):
        patch_cmake_lists(cmake_file)
    else:
        print(f"Warning: {cmake_file} not found")
    
    print("\nPatching complete!")
    print("\nNext steps:")
    print("1. Ensure you have the WebSocketPP library in libraries/websocketpp")
    print("2. If using standalone ASIO, place it in libraries/asio")
    print("3. Run cmake to regenerate build files")
    print("4. Rebuild the project")

if __name__ == "__main__":
    main()