#!/usr/bin/env python3
"""
Fix the structural issues in archipelago_client.cpp
Moves SendConnectPacket to the correct location and fixes the Connect function
"""

import sys
import os
import shutil
from datetime import datetime

def create_backup(filepath):
    """Create a timestamped backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✓ Created backup: {backup_path}")
    return backup_path

def fix_archipelago_structure(filepath):
    """Fix the misplaced SendConnectPacket function and correct the Connect function"""
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return False
    
    print(f"Fixing structural issues in: {filepath}")
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The correct structure for the file
    # We need to extract the SendConnectPacket function and move it to the right place
    # Then fix the Connect function
    
    # First, let's build the corrected content piece by piece
    corrected_content = '''#include "archipelago_client.h"
#include "../common/engine/printf.h"
#include "easywsclient.hpp"
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>

namespace Archipelago {

// Global instance
ArchipelagoClient* g_archipelago = nullptr;

void AP_Init() {
    if (!g_archipelago) {
        g_archipelago = new ArchipelagoClient();
        Printf("Archipelago: Client initialized\\n");
    }
}

void AP_Shutdown() {
    if (g_archipelago) {
        delete g_archipelago;
        g_archipelago = nullptr;
        Printf("Archipelago: Client shutdown\\n");
    }
}

ArchipelagoClient::ArchipelagoClient() 
    : m_status(ConnectionStatus::Disconnected)
    , m_port(38281)
    , m_team(0)
    , m_slotId(-1)
    , m_lastReceivedIndex(0) {
}

ArchipelagoClient::~ArchipelagoClient() {
    Disconnect();
}

bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_websocket && m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected\\n");
        return false;
    }

    m_host = host;
    m_port = port;
    
    // Build WebSocket URL
    std::stringstream url;
    url << "ws://" << host << ":" << port;
    
    Printf("Archipelago: Connecting to %s...\\n", url.str().c_str());
    
    m_status = ConnectionStatus::Connecting;
    
    // Create WebSocket connection
    m_websocket.reset(easywsclient::WebSocket::from_url(url.str()));
    
    if (!m_websocket) {
        Printf("Archipelago: Failed to connect to %s\\n", url.str().c_str());
        m_status = ConnectionStatus::Error;
        return false;
    }
    
    m_status = ConnectionStatus::Connected;
    Printf("Archipelago: Connected successfully!\\n");
    
    // Send the initial handshake packet immediately
    // This is REQUIRED by the Archipelago protocol
    SendConnectPacket();
    
    return true;
}

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

void ArchipelagoClient::Disconnect() {
    if (m_websocket) {
        m_websocket->close();
        m_websocket.reset();
    }
    m_status = ConnectionStatus::Disconnected;
    m_checkedLocations.clear();
    Printf("Archipelago: Disconnected\\n");
}

bool ArchipelagoClient::IsConnected() const {
    return m_websocket && m_websocket->getReadyState() == easywsclient::WebSocket::OPEN;
}

void ArchipelagoClient::ProcessMessages() {
    if (!m_websocket) return;
    
    // Process incoming messages
    m_websocket->poll();
    m_websocket->dispatch([this](const std::string& message) {
        HandleMessage(message);
    });
    
    // Send queued outgoing messages
    std::lock_guard<std::mutex> lock(m_queueMutex);
    while (!m_outgoingQueue.empty()) {
        m_websocket->send(m_outgoingQueue.front());
        m_outgoingQueue.pop();
    }
}

void ArchipelagoClient::SendPacket(const std::string& json) {
    if (!m_websocket) return;
    
    std::lock_guard<std::mutex> lock(m_queueMutex);
    m_outgoingQueue.push(json);
}

void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
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
}

void ArchipelagoClient::SendLocationCheck(int locationId) {
    std::vector<int> locations = { locationId };
    SendLocationChecks(locations);
}

void ArchipelagoClient::SendLocationChecks(const std::vector<int>& locationIds) {
    rapidjson::Document doc;
    doc.SetArray();
    
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "LocationChecks", allocator);
    
    rapidjson::Value locations(rapidjson::kArrayType);
    for (int id : locationIds) {
        locations.PushBack(id, allocator);
        m_checkedLocations.push_back(id);
    }
    packet.AddMember("locations", locations, allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::StatusUpdate(const std::string& status) {
    rapidjson::Document doc;
    doc.SetArray();
    
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "StatusUpdate", allocator);
    
    int statusValue = 0;
    if (status == "READY") statusValue = 10;
    else if (status == "PLAYING") statusValue = 20;
    else if (status == "GOAL") statusValue = 30;
    
    packet.AddMember("status", statusValue, allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::SendPing() {
    rapidjson::Document doc;
    doc.SetArray();
    
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "Bounce", allocator);
    packet.AddMember("data", rapidjson::Value().SetObject(), allocator);
    packet["data"].AddMember("time", std::chrono::system_clock::now().time_since_epoch().count(), allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
    Printf("Archipelago: Ping sent\\n");
}

void ArchipelagoClient::HandleMessage(const std::string& message) {
    if (m_messageCallback) {
        m_messageCallback(message);
    }
    
    ParsePacket(message);
}

void ArchipelagoClient::ParsePacket(const std::string& json) {
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    
    if (doc.HasParseError() || !doc.IsArray() || doc.Empty()) {
        Printf("Archipelago: Invalid packet received\\n");
        return;
    }
    
    for (rapidjson::SizeType i = 0; i < doc.Size(); i++) {
        const rapidjson::Value& packet = doc[i];
        
        if (!packet.HasMember("cmd") || !packet["cmd"].IsString()) {
            continue;
        }
        
        std::string cmd = packet["cmd"].GetString();
        
        if (cmd == "RoomInfo") {
            Printf("Archipelago: Received RoomInfo\\n");
            // Room info contains version info, tags, password required, etc.
            
        } else if (cmd == "Connected") {
            Printf("Archipelago: Authentication successful!\\n");
            m_status = ConnectionStatus::InGame;
            
            if (packet.HasMember("slot")) {
                m_slotId = packet["slot"].GetInt();
            }
            if (packet.HasMember("team")) {
                m_team = packet["team"].GetInt();
            }
            
            // Check for missing locations
            if (packet.HasMember("missing_locations")) {
                const auto& missing = packet["missing_locations"];
                if (missing.IsArray()) {
                    Printf("Archipelago: %d unchecked locations\\n", missing.Size());
                }
            }
            
        } else if (cmd == "ConnectionRefused") {
            Printf("Archipelago: Connection refused!\\n");
            m_status = ConnectionStatus::Error;
            
            if (packet.HasMember("errors")) {
                const auto& errors = packet["errors"];
                if (errors.IsArray()) {
                    for (rapidjson::SizeType j = 0; j < errors.Size(); j++) {
                        if (errors[j].IsString()) {
                            Printf("  Error: %s\\n", errors[j].GetString());
                        }
                    }
                }
            }
            
        } else if (cmd == "ReceivedItems") {
            if (!packet.HasMember("items") || !packet["items"].IsArray()) {
                continue;
            }
            
            const auto& items = packet["items"];
            for (rapidjson::SizeType j = 0; j < items.Size(); j++) {
                const auto& item = items[j];
                
                int itemId = item["item"].GetInt();
                int locationId = item["location"].GetInt();
                int playerSlot = item["player"].GetInt();
                
                Printf("Archipelago: Received item %d from location %d (player %d)\\n", 
                       itemId, locationId, playerSlot);
                
                if (m_itemReceivedCallback) {
                    m_itemReceivedCallback(itemId, locationId, playerSlot);
                }
            }
            
            if (packet.HasMember("index")) {
                m_lastReceivedIndex = packet["index"].GetInt();
            }
            
        } else if (cmd == "PrintJSON") {
            if (packet.HasMember("text")) {
                Printf("Archipelago: %s\\n", packet["text"].GetString());
            }
            
        } else if (cmd == "Bounced") {
            Printf("Archipelago: Pong received\\n");
            
        } else {
            Printf("Archipelago: Received packet type: %s\\n", cmd.c_str());
        }
    }
}

} // namespace Archipelago'''
    
    # Create backup
    backup_path = create_backup(filepath)
    
    # Write the corrected content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(corrected_content)
    
    print("✓ Fixed structural issues in archipelago_client.cpp")
    print("\nChanges made:")
    print("1. Moved SendConnectPacket() to its proper location after Connect()")
    print("2. Fixed Connect() function to properly complete and call SendConnectPacket()")
    print("3. Ensured proper function boundaries and flow")
    
    # Now update the header file to add the declaration
    header_path = filepath.replace('.cpp', '.h')
    if os.path.exists(header_path):
        print(f"\nUpdating header file: {header_path}")
        
        with open(header_path, 'r', encoding='utf-8') as f:
            header_content = f.read()
        
        # Check if SendConnectPacket is already declared
        if 'SendConnectPacket' not in header_content:
            # Find the private section
            private_pos = header_content.find('private:')
            if private_pos != -1:
                # Find the next good insertion point after private:
                insert_pos = header_content.find('\n', private_pos) + 1
                # Skip any existing member declarations to find a good spot
                lines_after_private = header_content[insert_pos:].split('\n')
                
                # Insert after the first line of member variables/functions
                for i, line in enumerate(lines_after_private):
                    if line.strip() and not line.strip().startswith('//'):
                        actual_pos = insert_pos + sum(len(l) + 1 for l in lines_after_private[:i+1])
                        break
                else:
                    actual_pos = insert_pos
                
                # Insert the declaration
                new_header = (header_content[:actual_pos] + 
                             "    void SendConnectPacket();\n" + 
                             header_content[actual_pos:])
                
                # Create backup of header
                create_backup(header_path)
                
                with open(header_path, 'w', encoding='utf-8') as f:
                    f.write(new_header)
                
                print("✓ Added SendConnectPacket() declaration to header file")
        else:
            print("✓ SendConnectPacket() already declared in header")
    
    print("\nThe Archipelago client structure has been fixed!")
    print("\nWhat was wrong:")
    print("- SendConnectPacket() function was defined inside Connect() function")
    print("- This broke the syntax and prevented the handshake from being called")
    print("\nWhat's fixed now:")
    print("- Connect() properly establishes the WebSocket connection")
    print("- Connect() calls SendConnectPacket() at the end")
    print("- SendConnectPacket() sends the required protocol handshake")
    print("\nNext steps:")
    print("1. Rebuild your project")
    print("2. Test connection with 'ap_connect localhost' or 'ap_connect archipelago.gg 61366'")
    print("3. The connection should now stay open!")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_archipelago_structure.py <path_to_archipelago_client.cpp>")
        print("Example: python fix_archipelago_structure.py C:\\path\\to\\archipelago_client.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"This script will fix the structural issues in:")
    print(f"  {filepath}")
    print("\nThis will:")
    print("  - Fix the misplaced SendConnectPacket function")
    print("  - Ensure Connect() properly calls the handshake")
    print("  - Update the header file with proper declaration")
    print("\nA backup will be created before any changes are made.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    success = fix_archipelago_structure(filepath)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()