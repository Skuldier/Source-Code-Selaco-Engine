#!/usr/bin/env python3
"""
Fix CMake version compatibility issue with libwebsockets
"""

import os
import re
import shutil
from datetime import datetime

def fix_cmake_version(root_dir):
    cmake_path = os.path.join(root_dir, "CMakeLists.txt")
    
    print("🔧 Fixing CMake version compatibility issue...")
    
    if not os.path.exists(cmake_path):
        print(f"❌ CMakeLists.txt not found at {cmake_path}")
        return False
    
    # Backup
    backup_path = cmake_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(cmake_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Read current content
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the FetchContent section for libwebsockets
    fetch_pattern = r'(FetchContent_Declare\s*\(\s*libwebsockets[^)]+\))'
    match = re.search(fetch_pattern, content, re.DOTALL)
    
    if not match:
        print("❌ Could not find FetchContent_Declare for libwebsockets")
        return False
    
    # Replace the entire Archipelago section with the fixed version
    archipelago_start = content.find("# ===================================================================\n# ARCHIPELAGO WEBSOCKET SUPPORT")
    archipelago_end = content.find("# END ARCHIPELAGO WEBSOCKET SUPPORT\n# ===================================================================")
    
    if archipelago_start == -1 or archipelago_end == -1:
        print("❌ Could not find Archipelago section markers")
        return False
    
    # Include the end marker
    archipelago_end = content.find("\n", archipelago_end + len("# END ARCHIPELAGO WEBSOCKET SUPPORT\n# ===================================================================")) + 1
    
    new_archipelago_section = '''# ===================================================================
# ARCHIPELAGO WEBSOCKET SUPPORT
# ===================================================================

# Set minimum CMake version for compatibility
if(POLICY CMP0048)
    cmake_policy(SET CMP0048 NEW)
endif()

# Fetch libwebsockets
include(FetchContent)

message(STATUS "Configuring libwebsockets for Archipelago support...")

# Set CMake policies for FetchContent
set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)
set(CMAKE_POLICY_DEFAULT_CMP0048 NEW)

FetchContent_Declare(
    libwebsockets
    GIT_REPOSITORY https://github.com/warmcat/libwebsockets.git
    GIT_TAG        v4.3.3
    GIT_SHALLOW    TRUE
    # Override the minimum CMake version
    CMAKE_ARGS     -DCMAKE_MINIMUM_REQUIRED_VERSION=3.5
)

# Configure libwebsockets options BEFORE FetchContent_MakeAvailable
set(LWS_WITH_SSL ON CACHE BOOL "" FORCE)
set(LWS_WITH_SHARED OFF CACHE BOOL "" FORCE)  # Static library
set(LWS_WITHOUT_TESTAPPS ON CACHE BOOL "" FORCE)
set(LWS_WITHOUT_TEST_SERVER ON CACHE BOOL "" FORCE)
set(LWS_WITHOUT_TEST_CLIENT ON CACHE BOOL "" FORCE)
set(LWS_WITH_MINIMAL_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LWS_WITH_BUNDLED_ZLIB ON CACHE BOOL "" FORCE)  # Use bundled zlib on Windows
set(LWS_WITH_HTTP2 OFF CACHE BOOL "" FORCE)
set(LWS_WITH_SOCKS5 OFF CACHE BOOL "" FORCE)
set(LWS_IPV6 ON CACHE BOOL "" FORCE)

# Disable unused features for smaller binary
set(LWS_WITHOUT_EXTENSIONS OFF CACHE BOOL "" FORCE)
set(LWS_WITHOUT_BUILTIN_GETIFADDRS OFF CACHE BOOL "" FORCE)
set(LWS_WITHOUT_BUILTIN_SHA1 OFF CACHE BOOL "" FORCE)
set(LWS_WITH_CUSTOM_HEADERS ON CACHE BOOL "" FORCE)

# Windows-specific settings
if(WIN32)
    set(LWS_WITH_SYS_ASYNC_DNS OFF CACHE BOOL "" FORCE)
    set(LWS_WITH_LIBUV OFF CACHE BOOL "" FORCE)
    set(LWS_WITH_LIBEV OFF CACHE BOOL "" FORCE)
endif()

# Save and restore CMAKE_MINIMUM_REQUIRED_VERSION
set(SAVED_CMAKE_MINIMUM_REQUIRED_VERSION ${CMAKE_MINIMUM_REQUIRED_VERSION})
set(CMAKE_MINIMUM_REQUIRED_VERSION 3.5)

# Make libwebsockets available
FetchContent_MakeAvailable(libwebsockets)

# Restore CMAKE_MINIMUM_REQUIRED_VERSION
set(CMAKE_MINIMUM_REQUIRED_VERSION ${SAVED_CMAKE_MINIMUM_REQUIRED_VERSION})

# JSON library for Archipelago protocol
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

# Create Archipelago WebSocket library
add_library(archipelago_websocket STATIC
    src/archipelago/lws_client.cpp
    src/archipelago/archipelago_protocol.cpp
    src/archipelago/archipelago_commands.cpp
)

# Set include directories
target_include_directories(archipelago_websocket 
    PUBLIC 
        ${CMAKE_CURRENT_SOURCE_DIR}/src/archipelago
    PRIVATE
        ${libwebsockets_SOURCE_DIR}/include
        ${libwebsockets_BINARY_DIR}/include
)

# Link dependencies
target_link_libraries(archipelago_websocket
    PUBLIC
        websockets
        nlohmann_json::nlohmann_json
)

# Windows-specific libraries
if(WIN32)
    target_link_libraries(archipelago_websocket PUBLIC
        ws2_32
        iphlpapi
        psapi
        userenv
        crypt32  # For SSL certificate handling
    )
endif()

# Visual Studio specific settings
if(MSVC)
    # Ensure consistent runtime library usage
    set_property(TARGET archipelago_websocket PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
    
    # Disable specific warnings
    target_compile_options(archipelago_websocket PRIVATE /wd4996)
endif()

# ===================================================================
# END ARCHIPELAGO WEBSOCKET SUPPORT
# ===================================================================
'''
    
    # Replace the section
    new_content = content[:archipelago_start] + new_archipelago_section + content[archipelago_end:]
    
    # Write the fixed content
    with open(cmake_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Fixed CMake configuration!")
    print("\n📝 Changes made:")
    print("  - Added CMAKE policy settings")
    print("  - Set CMAKE_MINIMUM_REQUIRED_VERSION handling")
    print("  - Added compatibility fixes for older CMake in libwebsockets")
    
    return True

def main():
    import sys
    
    if len(sys.argv) < 2:
        root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
        print(f"Using default path: {root_dir}")
    else:
        root_dir = sys.argv[1]
    
    if fix_cmake_version(root_dir):
        print("\n✅ Fix applied successfully!")
        print("\n🔨 Try building again:")
        print("  cd build")
        print("  cmake -G \"Visual Studio 17 2022\" -A x64 ..")
        print("\nIf it still fails, try:")
        print("  1. Delete the build directory completely")
        print("  2. Create a fresh build directory")
        print("  3. Run cmake again")
    else:
        print("\n❌ Failed to apply fix")

if __name__ == "__main__":
    main()