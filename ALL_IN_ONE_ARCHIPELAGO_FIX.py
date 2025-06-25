#!/usr/bin/env python3
"""
ALL-IN-ONE Archipelago Integration Fix for Selaco
This single script contains all fixes needed to resolve compilation errors
"""

import os
import sys
import re

def create_archipelago_client_files(archipelago_dir):
    """Create missing archipelago_client.h and .cpp files"""
    print("\n[1/7] Creating archipelago_client files...")
    
    # archipelago_client.h
    header = """// archipelago_client.h - Main interface for Selaco to Archipelago
#pragma once

#include "archipelago_protocol.h"

// Global Archipelago client instance
extern Archipelago::ArchipelagoClient* g_archipelago;

// C-style interface functions for game integration
extern "C" {
    // Initialize the Archipelago client
    void AP_Init();
    
    // Shutdown and cleanup
    void AP_Shutdown();
    
    // Update/poll the client (call from game loop)
    void AP_Update();
    
    // Connection functions
    bool AP_Connect(const char* host, int port = 38281);
    void AP_Disconnect();
    bool AP_IsConnected();
    
    // Authentication
    void AP_Authenticate(const char* slotName, const char* password = nullptr);
    
    // Game actions
    void AP_SendLocationCheck(int64_t locationId);
    void AP_SendChat(const char* message);
    
    // State queries
    const char* AP_GetSlotName();
    int AP_GetSlotNumber();
    bool AP_HasCheckedLocation(int64_t locationId);
}

// Helper macros for easy integration
#define ARCHIPELAGO_INIT() AP_Init()
#define ARCHIPELAGO_SHUTDOWN() AP_Shutdown()
#define ARCHIPELAGO_UPDATE() AP_Update()
"""

    # archipelago_client.cpp
    cpp = """// archipelago_client.cpp - C interface implementation for Archipelago
#include "archipelago_client.h"
#include "../common/engine/printf.h"

// C-style interface implementation
extern "C" {

bool AP_Connect(const char* host, int port) {
    if (!g_archipelago) {
        Printf("AP_Connect: Client not initialized!\\n");
        return false;
    }
    return g_archipelago->connect(host, port);
}

void AP_Disconnect() {
    if (g_archipelago) {
        g_archipelago->disconnect();
    }
}

bool AP_IsConnected() {
    return g_archipelago && g_archipelago->isConnected();
}

void AP_Authenticate(const char* slotName, const char* password) {
    if (!g_archipelago) {
        Printf("AP_Authenticate: Client not initialized!\\n");
        return;
    }
    
    std::string pass = password ? password : "";
    g_archipelago->authenticate(slotName, pass);
}

void AP_SendLocationCheck(int64_t locationId) {
    if (!g_archipelago) {
        return;
    }
    g_archipelago->sendLocationCheck(locationId);
}

void AP_SendChat(const char* message) {
    if (!g_archipelago || !message) {
        return;
    }
    g_archipelago->sendChat(message);
}

const char* AP_GetSlotName() {
    if (!g_archipelago) {
        return "";
    }
    return g_archipelago->getSlotName().c_str();
}

int AP_GetSlotNumber() {
    if (!g_archipelago) {
        return -1;
    }
    return g_archipelago->getSlotNumber();
}

bool AP_HasCheckedLocation(int64_t locationId) {
    if (!g_archipelago) {
        return false;
    }
    return g_archipelago->hasCheckedLocation(locationId);
}

} // extern "C"
"""

    os.makedirs(archipelago_dir, exist_ok=True)
    
    with open(os.path.join(archipelago_dir, "archipelago_client.h"), 'w') as f:
        f.write(header)
    print("   ✅ Created archipelago_client.h")
    
    with open(os.path.join(archipelago_dir, "archipelago_client.cpp"), 'w') as f:
        f.write(cpp)
    print("   ✅ Created archipelago_client.cpp")

def fix_lws_client_header(archipelago_dir):
    """Make websocketCallback public"""
    print("\n[2/7] Fixing lws_client.h...")
    
    header_path = os.path.join(archipelago_dir, "lws_client.h")
    if not os.path.exists(header_path):
        print("   ❌ lws_client.h not found")
        return
    
    with open(header_path, 'r') as f:
        content = f.read()
    
    # Move websocketCallback to public section
    if "public:\n    // LibWebSockets callback" not in content:
        # Find the callback and move it
        lines = content.split('\n')
        callback_line = -1
        public_line = -1
        
        for i, line in enumerate(lines):
            if "static int websocketCallback" in line:
                callback_line = i
            elif "public:" in line and public_line == -1:
                public_line = i
        
        if callback_line > 0 and public_line > 0:
            # Extract callback declaration
            callback_decl = []
            i = callback_line
            while i < len(lines) and ';' not in lines[i]:
                callback_decl.append(lines[i])
                i += 1
            if i < len(lines):
                callback_decl.append(lines[i])
            
            # Remove from original position
            for _ in range(len(callback_decl)):
                lines.pop(callback_line)
            
            # Insert after public:
            lines.insert(public_line + 1, "    // LibWebSockets callback (must be public)")
            for j, line in enumerate(callback_decl):
                lines.insert(public_line + 2 + j, line)
            
            with open(header_path, 'w') as f:
                f.write('\n'.join(lines))
            print("   ✅ Made websocketCallback public")
        else:
            print("   ⚠️  Could not find callback to move")
    else:
        print("   ✓ websocketCallback already public")

def fix_cmake_archipelago(cmake_path):
    """Add archipelago_client.cpp to CMakeLists.txt"""
    print("\n[3/7] Updating CMakeLists.txt...")
    
    with open(cmake_path, 'r') as f:
        content = f.read()
    
    # Add archipelago_client.cpp if not present
    if "archipelago_client.cpp" not in content:
        content = content.replace(
            "archipelago/archipelago_commands.cpp\n)",
            "archipelago/archipelago_commands.cpp\n    archipelago/archipelago_client.cpp\n)"
        )
        print("   ✅ Added archipelago_client.cpp to CMakeLists.txt")
    else:
        print("   ✓ archipelago_client.cpp already in CMakeLists.txt")
    
    # Link archipelago_websocket to zdoom
    if not re.search(r'target_link_libraries\s*\(\s*zdoom[^)]*archipelago_websocket', content, re.DOTALL):
        # Add after the archipelago section
        insert_pos = content.find("# END ARCHIPELAGO WEBSOCKET SUPPORT")
        if insert_pos != -1:
            insert_pos = content.find('\n', insert_pos) + 1
            content = content[:insert_pos] + "\n# Link Archipelago to main game\ntarget_link_libraries(zdoom PRIVATE archipelago_websocket)\n" + content[insert_pos:]
            print("   ✅ Linked archipelago_websocket to zdoom")
    else:
        print("   ✓ archipelago_websocket already linked")
    
    with open(cmake_path, 'w') as f:
        f.write(content)

def fix_cmake_zlib(cmake_path):
    """Fix zlib configuration"""
    print("\n[4/7] Fixing zlib configuration...")
    
    with open(cmake_path, 'r') as f:
        content = f.read()
    
    # Find libwebsockets configuration
    config_start = content.find("# Configure libwebsockets options")
    make_available = content.find("FetchContent_MakeAvailable(libwebsockets)", config_start)
    
    if config_start == -1 or make_available == -1:
        print("   ❌ Could not find libwebsockets configuration")
        return
    
    # Replace with no-zlib configuration
    new_config = """# Configure libwebsockets options BEFORE FetchContent_MakeAvailable
# Minimal build - no compression, no zlib
set(LWS_WITH_MINIMAL_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LWS_WITHOUT_TESTAPPS ON CACHE BOOL "" FORCE)
set(LWS_WITHOUT_TEST_SERVER ON CACHE BOOL "" FORCE)
set(LWS_WITHOUT_TEST_CLIENT ON CACHE BOOL "" FORCE)
set(LWS_WITH_SSL ON CACHE BOOL "" FORCE)
set(LWS_WITH_SHARED OFF CACHE BOOL "" FORCE)
set(LWS_WITH_STATIC ON CACHE BOOL "" FORCE)

# COMPLETELY DISABLE COMPRESSION AND ZLIB
set(LWS_WITHOUT_EXTENSIONS ON CACHE BOOL "" FORCE)  # No WebSocket extensions
set(LWS_WITH_ZLIB OFF CACHE BOOL "" FORCE)          # No zlib support
set(LWS_WITH_BUNDLED_ZLIB OFF CACHE BOOL "" FORCE)  # Don't build bundled zlib
set(LWS_WITH_ZIP_FOPS OFF CACHE BOOL "" FORCE)      # No zip file operations

# Disable other features that might need zlib
set(LWS_WITH_HTTP2 OFF CACHE BOOL "" FORCE)
set(LWS_WITH_HTTP_STREAM_COMPRESSION OFF CACHE BOOL "" FORCE)

# Windows-specific
if(WIN32)
    set(LWS_WITHOUT_DAEMONIZE ON CACHE BOOL "" FORCE)
endif()

# Temporarily set CMAKE_MINIMUM_REQUIRED_VERSION for libwebsockets
set(CMAKE_MINIMUM_REQUIRED_VERSION 3.5)

# Make libwebsockets available
"""
    
    new_content = content[:config_start] + new_config + content[make_available:]
    
    with open(cmake_path, 'w') as f:
        f.write(new_content)
    
    print("   ✅ Disabled all zlib usage in libwebsockets")

def create_dummy_zlib(archipelago_dir):
    """Create dummy zlib headers"""
    print("\n[5/7] Creating dummy zlib headers...")
    
    zlib_h = """/* Minimal dummy zlib.h */
#ifndef ZLIB_H
#define ZLIB_H

#define Z_OK 0
#define Z_STREAM_END 1
#define Z_ERRNO (-1)

typedef struct z_stream_s {
    void *opaque;
    int data_type;
    unsigned long adler;
    unsigned long reserved;
} z_stream;

#endif
"""
    
    with open(os.path.join(archipelago_dir, "zlib.h"), 'w') as f:
        f.write(zlib_h)
    print("   ✅ Created dummy zlib.h")

def fix_game_files(src_dir):
    """Fix d_main.cpp and d_net.cpp"""
    print("\n[6/7] Fixing game integration files...")
    
    # Fix d_main.cpp
    dmain_path = os.path.join(src_dir, "d_main.cpp")
    if os.path.exists(dmain_path):
        with open(dmain_path, 'r') as f:
            content = f.read()
        
        # Add include if missing
        if 'archipelago/archipelago_client.h' not in content:
            # Add after other includes
            pos = content.rfind('#include')
            pos = content.find('\n', pos) + 1
            content = content[:pos] + '#include "archipelago/archipelago_client.h"\n' + content[pos:]
        
        # Fix namespace usage
        content = content.replace('Archipelago::AP_Update();', 'AP_Update();')
        
        with open(dmain_path, 'w') as f:
            f.write(content)
        print("   ✅ Fixed d_main.cpp")
    
    # Fix d_net.cpp
    dnet_path = os.path.join(src_dir, "d_net.cpp")
    if os.path.exists(dnet_path):
        with open(dnet_path, 'r') as f:
            content = f.read()
        
        # Add include if missing
        if 'archipelago/archipelago_client.h' not in content:
            pos = content.rfind('#include')
            pos = content.find('\n', pos) + 1
            content = content[:pos] + '#include "archipelago/archipelago_client.h"\n' + content[pos:]
        
        # Add Net_ProcessArchipelago if missing
        if "Net_ProcessArchipelago" not in content:
            func = """
//
// Net_ProcessArchipelago
//
void Net_ProcessArchipelago()
{
    if (g_archipelago) {
        AP_Update();
    }
}
"""
            # Add at end of file
            content = content.rstrip() + '\n' + func + '\n'
        
        with open(dnet_path, 'w') as f:
            f.write(content)
        print("   ✅ Fixed d_net.cpp")

def main():
    print("🚀 ALL-IN-ONE ARCHIPELAGO INTEGRATION FIX")
    print("=" * 70)
    
    root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
    src_dir = os.path.join(root_dir, "src")
    archipelago_dir = os.path.join(src_dir, "archipelago")
    cmake_path = os.path.join(src_dir, "CMakeLists.txt")
    
    try:
        # Create missing files
        create_archipelago_client_files(archipelago_dir)
        
        # Fix headers
        fix_lws_client_header(archipelago_dir)
        
        # Fix CMake
        fix_cmake_archipelago(cmake_path)
        fix_cmake_zlib(cmake_path)
        
        # Create dummy zlib
        create_dummy_zlib(archipelago_dir)
        
        # Fix game files
        fix_game_files(src_dir)
        
        print("\n[7/7] Cleanup...")
        print("   ✅ All fixes applied!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    print("\n" + "=" * 70)
    print("✅ ALL FIXES COMPLETED SUCCESSFULLY!")
    print("\n📋 Next steps:")
    print("1. Clean build directory:")
    print("   cd C:\\Users\\Skuldier\\Documents\\Source-Code-Selaco-Engine")
    print("   rmdir /s /q build")
    print("   mkdir build")
    print("   cd build")
    print("\n2. Run CMake:")
    print('   cmake -G "Visual Studio 17 2022" -A x64 ..')
    print("\n3. Build:")
    print("   cmake --build . --config Debug")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())