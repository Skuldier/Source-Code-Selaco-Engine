#!/usr/bin/env python3
"""
Patch to add proper hostname resolution to Archipelago client
Enables connection to remote servers like archipelago.gg
"""

import os
import shutil
from datetime import datetime

def patch_archipelago_hostname_resolution():
    """Add hostname resolution support to archipelago_client.cpp"""
    
    client_cpp = "src/archipelago/archipelago_client.cpp"
    
    if not os.path.exists(client_cpp):
        print(f"Error: {client_cpp} not found!")
        print("Make sure you run this from the Selaco source root directory")
        return False
    
    # Backup file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{client_cpp}.backup_{timestamp}"
    shutil.copy2(client_cpp, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Read the current file
    with open(client_cpp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add hostname resolution function after the ThreadMessage struct
    hostname_resolver = '''
// Hostname resolution helper
std::string ResolveHostname(const std::string& hostname) {
    // Quick check for localhost
    if (hostname == "localhost" || hostname == "127.0.0.1") {
        return "127.0.0.1";
    }
    
    // Check if it's already an IP address (simple check)
    bool isIP = true;
    int dotCount = 0;
    for (char c : hostname) {
        if (c == '.') {
            dotCount++;
        } else if (!isdigit(c)) {
            isIP = false;
            break;
        }
    }
    
    if (isIP && dotCount == 3) {
        return hostname; // Already an IP
    }
    
    Printf("Archipelago: Resolving hostname '%s'...\\n", hostname.c_str());
    
#ifdef _WIN32
    // Windows already has WSA initialized in Impl constructor
    struct hostent* host = gethostbyname(hostname.c_str());
    if (host && host->h_addr_list[0]) {
        struct in_addr addr;
        memcpy(&addr, host->h_addr_list[0], sizeof(struct in_addr));
        std::string resolved = inet_ntoa(addr);
        Printf("Archipelago: Resolved to %s\\n", resolved.c_str());
        return resolved;
    }
#else
    // POSIX systems
    struct addrinfo hints = {0}, *result = nullptr;
    hints.ai_family = AF_INET; // IPv4
    hints.ai_socktype = SOCK_STREAM;
    
    int status = getaddrinfo(hostname.c_str(), nullptr, &hints, &result);
    if (status == 0 && result) {
        struct sockaddr_in* addr_in = (struct sockaddr_in*)result->ai_addr;
        char ip_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &(addr_in->sin_addr), ip_str, INET_ADDRSTRLEN);
        std::string resolved(ip_str);
        freeaddrinfo(result);
        Printf("Archipelago: Resolved to %s\\n", resolved.c_str());
        return resolved;
    }
    
    if (result) freeaddrinfo(result);
#endif
    
    Printf("Archipelago: Failed to resolve hostname '%s', using as-is\\n", hostname.c_str());
    return hostname; // Return original, WebSocketPP might handle it
}

'''
    
    # Find where to insert the resolver function
    insert_pos = content.find("// Private implementation class")
    if insert_pos == -1:
        print("Error: Could not find insertion point for hostname resolver")
        return False
    
    # Insert the resolver function
    content = content[:insert_pos] + hostname_resolver + content[insert_pos:]
    
    # Update the Connect method to use the resolver
    old_connect = """// Connect to server
bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected or connecting\\n");
        return false;
    }
    
    m_host = host;
    m_port = port;
    
    // Resolve hostname
    std::string resolved_host = host;
    if (host == "localhost") {
        resolved_host = "127.0.0.1";
    }
    
    // Build URI
    std::stringstream uri;
    uri << "ws://" << resolved_host << ":" << port;"""
    
    new_connect = """// Connect to server
bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected or connecting\\n");
        return false;
    }
    
    m_host = host;
    m_port = port;
    
    // Resolve hostname to IP address
    std::string resolved_host = ResolveHostname(host);
    
    // Build URI
    std::stringstream uri;
    uri << "ws://" << resolved_host << ":" << port;"""
    
    if old_connect not in content:
        print("Warning: Could not find exact Connect method to patch")
        print("Trying alternative pattern...")
        
        # Try to find and replace just the hostname resolution part
        old_pattern = """    // Resolve hostname
    std::string resolved_host = host;
    if (host == "localhost") {
        resolved_host = "127.0.0.1";
    }"""
        
        new_pattern = """    // Resolve hostname to IP address
    std::string resolved_host = ResolveHostname(host);"""
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print("Applied alternative hostname resolution patch")
        else:
            print("Error: Could not find hostname resolution code to patch")
            return False
    else:
        content = content.replace(old_connect, new_connect)
        print("Updated Connect method to use hostname resolver")
    
    # Add timeout handling for remote connections
    timeout_addition = """
    // Add connection timeout for remote servers
    m_connectionTimeout = std::chrono::steady_clock::now() + std::chrono::seconds(10);"""
    
    # Find where to add timeout in Connect method
    timeout_marker = "m_status = ConnectionStatus::Connecting;"
    if timeout_marker in content:
        content = content.replace(
            timeout_marker,
            timeout_marker + timeout_addition
        )
    
    # Update ProcessMessages to check for timeout
    old_process = """void ArchipelagoClient::ProcessMessages() {
    // Get messages from worker thread
    auto messages = m_impl->GetFromThread();
    
    Printf("Archipelago: ProcessMessages - got %d messages\\n", (int)messages.size());"""
    
    new_process = """void ArchipelagoClient::ProcessMessages() {
    // Check for connection timeout
    if (m_status == ConnectionStatus::Connecting) {
        auto now = std::chrono::steady_clock::now();
        if (now > m_connectionTimeout) {
            Printf("Archipelago: Connection timeout after 10 seconds\\n");
            m_status = ConnectionStatus::Error;
            Disconnect();
            return;
        }
    }
    
    // Get messages from worker thread
    auto messages = m_impl->GetFromThread();
    
    Printf("Archipelago: ProcessMessages - got %d messages\\n", (int)messages.size());"""
    
    if old_process in content:
        content = content.replace(old_process, new_process)
        print("Added connection timeout handling")
    
    # Add member variable for timeout
    timeout_member = """    // State tracking
    int m_lastReceivedIndex;
    std::vector<int> m_checkedLocations;
    std::chrono::steady_clock::time_point m_connectionTimeout;"""
    
    old_member = """    // State tracking
    int m_lastReceivedIndex;
    std::vector<int> m_checkedLocations;"""
    
    if old_member in content:
        content = content.replace(old_member, timeout_member)
    
    # Also need to add the include for chrono steady_clock if not present
    if "#include <chrono>" in content and "steady_clock" not in content:
        # Add steady_clock usage
        chrono_include = "#include <chrono>"
        content = content.replace(chrono_include, chrono_include + "\n#include <cstring>  // for memcpy")
    
    # Write the patched content
    with open(client_cpp, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Successfully patched {client_cpp}")
    
    # Now patch the header file to add the timeout member
    client_h = "src/archipelago/archipelago_client.h"
    if os.path.exists(client_h):
        with open(client_h, 'r', encoding='utf-8') as f:
            header_content = f.read()
        
        # Add include if needed
        if "#include <chrono>" not in header_content:
            includes_end = header_content.find("namespace Archipelago {")
            if includes_end != -1:
                header_content = header_content[:includes_end] + "#include <chrono>\n\n" + header_content[includes_end:]
        
        # Add timeout member
        old_tracking = """    // State tracking
    int m_lastReceivedIndex;
    std::vector<int> m_checkedLocations;"""
        
        new_tracking = """    // State tracking
    int m_lastReceivedIndex;
    std::vector<int> m_checkedLocations;
    std::chrono::steady_clock::time_point m_connectionTimeout;"""
        
        if old_tracking in header_content:
            header_content = header_content.replace(old_tracking, new_tracking)
            
            with open(client_h, 'w', encoding='utf-8') as f:
                f.write(header_content)
            print(f"Successfully patched {client_h}")
    
    return True

def create_remote_test_script():
    """Create a test script for remote connections"""
    
    test_script = '''#!/usr/bin/env python3
"""
Test remote Archipelago server connections
"""

import asyncio
import websockets
import json
import socket
import sys

async def test_remote_connection(host, port):
    # First test DNS resolution
    print(f"Testing connection to {host}:{port}")
    print("\\n1. DNS Resolution Test:")
    try:
        ip = socket.gethostbyname(host)
        print(f"   ✓ {host} resolves to {ip}")
    except socket.gaierror as e:
        print(f"   ✗ Failed to resolve {host}: {e}")
        return
    
    # Test WebSocket connection
    print("\\n2. WebSocket Connection Test:")
    uri = f"ws://{host}:{port}"
    
    try:
        print(f"   Connecting to {uri}...")
        async with websockets.connect(uri, timeout=10) as websocket:
            print("   ✓ WebSocket connection established!")
            
            # Get RoomInfo
            print("\\n3. Archipelago Protocol Test:")
            room_info_raw = await asyncio.wait_for(websocket.recv(), timeout=5)
            room_info = json.loads(room_info_raw)[0]
            
            if room_info.get("cmd") == "RoomInfo":
                print("   ✓ Received valid RoomInfo packet")
                print(f"   Games: {', '.join(room_info.get('games', []))}")
                print(f"   Version: {room_info['version']['major']}.{room_info['version']['minor']}.{room_info['version']['build']}")
                
                if "Selaco" in room_info.get('games', []):
                    print("   ✓ Selaco is loaded on this server!")
                else:
                    print("   ⚠ Selaco is NOT loaded on this server")
                    print("   Available games:", ', '.join(room_info.get('games', [])))
            else:
                print("   ✗ Unexpected initial packet:", room_info.get("cmd"))
                
    except asyncio.TimeoutError:
        print("   ✗ Connection timed out")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        
    print("\\nTest complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_remote.py <host> [port]")
        print("Example: python test_remote.py archipelago.gg 58697")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 38281
    
    asyncio.run(test_remote_connection(host, port))
'''
    
    with open("test_remote.py", 'w') as f:
        f.write(test_script)
    
    print("Created test_remote.py")

if __name__ == "__main__":
    print("Archipelago Hostname Resolution Patch")
    print("=====================================")
    
    # Check if we're in the right directory
    if not os.path.exists("src/archipelago/archipelago_client.cpp"):
        print("Error: This script must be run from the Selaco source root directory")
        print("Current directory:", os.getcwd())
        exit(1)
    
    # Apply the patch
    if patch_archipelago_hostname_resolution():
        print("\nPatch applied successfully!")
        print("\nNext steps:")
        print("1. Rebuild the project:")
        print("   cd build")
        print("   cmake ..")
        print("   make -j$(nproc)")
        print("\n2. Test remote connection:")
        print("   python test_remote.py archipelago.gg 58697")
        print("\n3. In Selaco:")
        print("   ap_connect archipelago.gg 58697")
        print("   ap_status")
        
        create_remote_test_script()
    else:
        print("\nPatch failed! Check the error messages above.")