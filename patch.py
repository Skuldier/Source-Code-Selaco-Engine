#!/usr/bin/env python3
"""
Fix runtime library mismatch in CMakeLists.txt
"""

import os
import re
import shutil
from datetime import datetime

def fix_cmake_runtime_library(root_dir):
    cmake_path = os.path.join(root_dir, "CMakeLists.txt")
    
    print("🔧 Fixing runtime library mismatch...")
    
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
    
    # Find the Archipelago section
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

# Fetch libwebsockets
include(FetchContent)

message(STATUS "Configuring libwebsockets for Archipelago support...")

# Determine the runtime library setting from the main project
if(MSVC)
    # Get the current runtime library setting
    set(CMAKE_MSVC_RUNTIME_LIBRARY_DEFAULT "")
    if(NOT CMAKE_MSVC_RUNTIME_LIBRARY)
        # Infer from existing flags or default to static for release builds
        string(FIND "${CMAKE_CXX_FLAGS_RELEASE}" "/MT" MT_POS)
        string(FIND "${CMAKE_CXX_FLAGS_RELEASE}" "/MD" MD_POS)
        if(MT_POS GREATER -1)
            set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
        elseif(MD_POS GREATER -1)
            set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
        else
            # Default to static runtime to match zdoom
            set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
        endif()
    endif()
    message(STATUS "Using MSVC runtime library: ${CMAKE_MSVC_RUNTIME_LIBRARY}")
endif()

FetchContent_Declare(
    libwebsockets
    GIT_REPOSITORY https://github.com/warmcat/libwebsockets.git
    GIT_TAG v4.3.3  # Latest stable - CMake 3.5+
    GIT_SHALLOW TRUE
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

# Make libwebsockets available
FetchContent_MakeAvailable(libwebsockets)

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
    # Ensure consistent runtime library usage with the main project
    set_property(TARGET archipelago_websocket PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    
    # Also set it for libwebsockets if possible
    if(TARGET websockets)
        set_property(TARGET websockets PROPERTY
            MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    endif()
    
    # Disable specific warnings
    target_compile_options(archipelago_websocket PRIVATE /wd4996)
    
    # Ensure proper C++ standard
    target_compile_features(archipelago_websocket PUBLIC cxx_std_17)
endif()

# Add to the main target
# Find where zdoom target links its libraries and add archipelago_websocket
# (This assumes the main target is called 'zdoom' - adjust if different)
if(TARGET zdoom)
    target_link_libraries(zdoom PRIVATE archipelago_websocket)
endif()

# ===================================================================
# END ARCHIPELAGO WEBSOCKET SUPPORT
# ==================================================================='''
    
    # Replace the section
    new_content = content[:archipelago_start] + new_archipelago_section + content[archipelago_end:]
    
    # Write the fixed content
    with open(cmake_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Fixed CMake configuration!")
    print("\n📝 Changes made:")
    print("  - Added runtime library detection")
    print("  - Forced static runtime library for all targets")
    print("  - Added proper MSVC_RUNTIME_LIBRARY settings")
    
    return True

def clean_build_directory(root_dir):
    """Clean the build directory to ensure fresh build"""
    build_dir = os.path.join(root_dir, "build")
    
    if os.path.exists(build_dir):
        print("\n🧹 Cleaning build directory...")
        
        # Remove specific problematic directories
        dirs_to_clean = [
            "_deps/libwebsockets-build",
            "_deps/libwebsockets-subbuild",
            "_deps/json-build",
            "_deps/json-subbuild",
            "CMakeFiles",
            "src/archipelago"
        ]
        
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(build_dir, dir_name)
            if os.path.exists(dir_path):
                print(f"  Removing {dir_name}...")
                shutil.rmtree(dir_path, ignore_errors=True)
        
        # Remove CMakeCache
        cache_file = os.path.join(build_dir, "CMakeCache.txt")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print("  Removed CMakeCache.txt")
        
        print("✅ Build directory cleaned")

def main():
    import sys
    
    if len(sys.argv) < 2:
        root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
        print(f"Using default path: {root_dir}")
    else:
        root_dir = sys.argv[1]
    
    if fix_cmake_runtime_library(root_dir):
        clean_build_directory(root_dir)
        
        print("\n✅ Fix applied successfully!")
        print("\n🔨 Now rebuild with these steps:")
        print("  1. Open a Visual Studio command prompt")
        print("  2. cd build")
        print("  3. cmake -G \"Visual Studio 17 2022\" -A x64 ..")
        print("  4. cmake --build . --config Debug")
        print("\nOr for a completely clean build:")
        print("  1. Delete the entire build directory")
        print("  2. Create a new build directory")
        print("  3. Run cmake again")
    else:
        print("\n❌ Failed to apply fix")

if __name__ == "__main__":
    main()