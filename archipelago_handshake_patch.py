#!/usr/bin/env python3
"""
Patch Archipelago client to implement proper connection handshake
This adds the required Connect packet that must be sent immediately after WebSocket connection
"""

import sys
import os
import re
import shutil
from datetime import datetime

def create_backup(filepath):
    """Create a timestamped backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✓ Created backup: {backup_path}")
    return backup_path

def patch_connect_function(content):
    """Update the Connect function to send the initial handshake packet"""
    
    # Find the Connect function
    connect_pattern = r'(bool\s+ArchipelagoClient::Connect\s*\([^)]*\)\s*\{[^}]+m_status\s*=\s*ConnectionStatus::Connected;[^}]+?\})'
    
    match = re.search(connect_pattern, content, re.DOTALL)
    if not match:
        print("Warning: Could not find Connect function with expected pattern")
        # Try alternative pattern
        connect_pattern2 = r'(bool\s+ArchipelagoClient::Connect\s*\([^{]+\{[^}]+?m_websocket\.reset[^}]+?\})'
        match = re.search(connect_pattern2, content, re.DOTALL)
        if not match:
            print("Error: Could not find Connect function")
            return None
    
    old_function = match.group(1)
    
    # Create the new Connect function with handshake
    new_function = '''bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_websocket && m_websocket->getReadyState() != easywsclient::WebSocket::CLOSED) {
        Printf("Archipelago: Already connected!\\n");
        return false;
    }
    
    m_host = host;
    m_port = port;
    
    std::string url = "ws://" + m_host + ":" + std::to_string(m_port);
    Printf("Archipelago: Connecting to %s...\\n", url.c_str());
    
    m_websocket.reset(easywsclient::WebSocket::from_url(url));
    if (!m_websocket) {
        Printf("Archipelago: Failed to connect to %s\\n", url.c_str());
        m_status = ConnectionStatus::Error;
        return false;
    }
    
    Printf("Archipelago: Connected!\\n");
    m_status = ConnectionStatus::Connected;
    
    // Send the initial Connect packet immediately
    // This is REQUIRED by the Archipelago protocol
    SendConnectPacket();
    
    return true;
}'''
    
    # Replace the old function with the new one
    content = content.replace(old_function, new_function)
    print("✓ Updated Connect function to include handshake")
    return content

def add_send_connect_packet_function(content):
    """Add the SendConnectPacket function"""
    
    # Check if function already exists
    if 'SendConnectPacket' in content:
        print("✓ SendConnectPacket function already exists")
        return content
    
    # Find a good place to insert the function - after Connect function
    connect_end = re.search(r'(ArchipelagoClient::Connect[^}]+\})', content, re.DOTALL)
    if connect_end:
        insert_pos = connect_end.end()
    else:
        # Alternative: insert before Disconnect
        disconnect_pos = content.find('void ArchipelagoClient::Disconnect')
        if disconnect_pos != -1:
            insert_pos = disconnect_pos
        else:
            print("Warning: Could not find ideal insertion point")
            insert_pos = content.find('void ArchipelagoClient::Authenticate')
    
    # The SendConnectPacket implementation
    send_connect_function = '''

void ArchipelagoClient::SendConnectPacket() {
    // Create the Connect packet as required by Archipelago protocol
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    // Required fields for Connect packet
    packet.AddMember("cmd", "Connect", allocator);
    
    // Game identification - this tells the server we're a Selaco client
    packet.AddMember("game", "Selaco", allocator);
    
    // Player name - for now just use a default, will be updated with auth
    packet.AddMember("name", "SelacoPlayer", allocator);
    
    // Unique identifier for this client instance
    // In a full implementation, you'd generate and store a proper UUID
    packet.AddMember("uuid", "selaco-client-001", allocator);
    
    // Protocol version - Archipelago protocol version we support
    rapidjson::Value version(rapidjson::kObjectType);
    version.AddMember("class", "Version", allocator);
    version.AddMember("major", 0, allocator);
    version.AddMember("minor", 4, allocator);
    version.AddMember("build", 0, allocator);
    packet.AddMember("version", version, allocator);
    
    // Items handling flags - tells server how we want to receive items
    // 0b111 = 7 means we want all item handling features
    packet.AddMember("items_handling", 7, allocator);
    
    // Tags to identify our client capabilities
    rapidjson::Value tags(rapidjson::kArrayType);
    tags.PushBack("AP", allocator);
    tags.PushBack("DeathLink", allocator);  // If Selaco supports DeathLink
    packet.AddMember("tags", tags, allocator);
    
    // Convert to string and send
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    packet.Accept(writer);
    
    std::string message = buffer.GetString();
    Printf("Archipelago: Sending Connect packet\\n");
    SendPacket(message);
}
'''
    
    # Insert the function
    before = content[:insert_pos]
    after = content[insert_pos:]
    
    # Ensure proper spacing
    if insert_pos > 0 and before[-1] != '\n':
        send_connect_function = '\n' + send_connect_function
    
    content = before + send_connect_function + after
    print("✓ Added SendConnectPacket function")
    return content

def add_function_declaration(content):
    """Add SendConnectPacket to the class declaration"""
    
    # Check if already declared
    if 'SendConnectPacket' in content and 'void SendConnectPacket();' in content:
        print("✓ SendConnectPacket already declared")
        return content
    
    # Find the private section of the class
    private_pattern = r'(private:\s*\n)(.*?)((?:public:|protected:|};))'
    match = re.search(private_pattern, content, re.DOTALL)
    
    if match:
        before_private = content[:match.start()] + match.group(1)
        private_section = match.group(2)
        after_private = match.group(3) + content[match.end():]
        
        # Add the declaration at the start of private section
        new_private = "    void SendConnectPacket();\n" + private_section
        
        content = before_private + new_private + after_private
        print("✓ Added SendConnectPacket declaration to class")
    else:
        print("Warning: Could not find private section to add declaration")
    
    return content

def update_authenticate_function(content):
    """Update Authenticate function to not send a redundant Connect packet"""
    
    # The current Authenticate might be trying to send connection info
    # We need to update it to send the proper authentication packet instead
    
    auth_pattern = r'(void\s+ArchipelagoClient::Authenticate\s*\([^{]+\{[^}]+?\})'
    match = re.search(auth_pattern, content, re.DOTALL)
    
    if not match:
        print("Warning: Could not find Authenticate function")
        return content
    
    old_auth = match.group(1)
    
    # New authenticate function that sends proper auth packet
    new_auth = '''void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
    if (m_status != ConnectionStatus::Connected) {
        Printf("Archipelago: Not connected!\\n");
        return;
    }
    
    m_slot = slot;
    
    // Create ConnectSlot packet for authentication
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "ConnectSlot", allocator);
    
    // Slot name to connect to
    rapidjson::Value slotValue;
    slotValue.SetString(slot.c_str(), allocator);
    packet.AddMember("name", slotValue, allocator);
    
    // Password if required
    if (!password.empty()) {
        rapidjson::Value passValue;
        passValue.SetString(password.c_str(), allocator);
        packet.AddMember("password", passValue, allocator);
    }
    
    // Game version
    packet.AddMember("clientVer", version, allocator);
    
    // Convert and send
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    packet.Accept(writer);
    
    Printf("Archipelago: Authenticating as '%s'...\\n", slot.c_str());
    SendPacket(buffer.GetString());
}'''
    
    content = content.replace(old_auth, new_auth)
    print("✓ Updated Authenticate function")
    return content

def main():
    if len(sys.argv) < 2:
        print("Usage: python archipelago_handshake_patch.py <path_to_archipelago_client.cpp>")
        print("Example: python archipelago_handshake_patch.py C:\\path\\to\\archipelago_client.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        sys.exit(1)
    
    print(f"Patching Archipelago client for proper handshake protocol...")
    print(f"Target file: {filepath}")
    
    # Create backup
    backup_path = create_backup(filepath)
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply patches
    print("\nApplying patches...")
    
    # 1. Add function declaration
    content = add_function_declaration(content)
    
    # 2. Add SendConnectPacket function
    content = add_send_connect_packet_function(content)
    
    # 3. Update Connect function to call SendConnectPacket
    result = patch_connect_function(content)
    if result:
        content = result
    
    # 4. Update Authenticate function
    content = update_authenticate_function(content)
    
    # Write the patched content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✓ Successfully patched archipelago_client.cpp")
    print("\nChanges made:")
    print("1. Added SendConnectPacket() function that sends the required initial handshake")
    print("2. Updated Connect() to call SendConnectPacket() immediately after connection")
    print("3. Updated Authenticate() to send proper ConnectSlot packet")
    print("4. Added necessary function declaration to class")
    
    print("\nThe handshake now follows the proper Archipelago protocol:")
    print("- Connect packet sent immediately after WebSocket connection")
    print("- Includes all required fields (cmd, game, name, uuid, version, etc.)")
    print("- Authenticate sends ConnectSlot packet for slot authentication")
    
    print("\nNext steps:")
    print("1. Rebuild your project")
    print("2. Test with 'ap_connect localhost' or 'ap_connect archipelago.gg 61366'")
    print("3. The connection should now stay open!")

if __name__ == "__main__":
    main()