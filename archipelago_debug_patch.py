#!/usr/bin/env python3
"""
Add comprehensive debugging to Archipelago client to diagnose connection issues
This will help us see exactly what's happening during the connection process
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

def add_debugging_to_client(filepath):
    """Add extensive debugging to help diagnose the connection issue"""
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return False
    
    print(f"Adding debugging to: {filepath}")
    
    # Read the current file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create the enhanced version with debugging
    debugged_content = '''#include "archipelago_client.h"
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
    Printf("Archipelago: Constructor called\\n");
}

ArchipelagoClient::~ArchipelagoClient() {
    Printf("Archipelago: Destructor called\\n");
    Disconnect();
}

bool ArchipelagoClient::Connect(const std::string& host, int port) {
    Printf("Archipelago: Connect() called with host=%s, port=%d\\n", host.c_str(), port);
    
    if (m_websocket && m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected\\n");
        return false;
    }

    m_host = host;
    m_port = port;
    
    // Build WebSocket URL
    std::stringstream url;
    url << "ws://" << host << ":" << port;
    
    Printf("Archipelago: Attempting to connect to URL: %s\\n", url.str().c_str());
    
    m_status = ConnectionStatus::Connecting;
    
    // Create WebSocket connection
    Printf("Archipelago: Creating WebSocket...\\n");
    m_websocket.reset(easywsclient::WebSocket::from_url(url.str()));
    
    if (!m_websocket) {
        Printf("Archipelago: ERROR - Failed to create WebSocket for %s\\n", url.str().c_str());
        m_status = ConnectionStatus::Error;
        return false;
    }
    
    Printf("Archipelago: WebSocket created successfully\\n");
    
    // Check the ready state
    easywsclient::WebSocket::readyStateValues state = m_websocket->getReadyState();
    Printf("Archipelago: WebSocket state after creation: %d\\n", (int)state);
    
    if (state != easywsclient::WebSocket::OPEN) {
        Printf("Archipelago: WARNING - WebSocket not in OPEN state immediately after creation\\n");
        
        // Try polling a few times to see if it opens
        for (int i = 0; i < 10; i++) {
            m_websocket->poll();
            state = m_websocket->getReadyState();
            Printf("Archipelago: Poll %d - WebSocket state: %d\\n", i+1, (int)state);
            
            if (state == easywsclient::WebSocket::OPEN) {
                Printf("Archipelago: WebSocket opened after %d polls\\n", i+1);
                break;
            }
            
            // Small delay between polls
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        
        if (state != easywsclient::WebSocket::OPEN) {
            Printf("Archipelago: ERROR - WebSocket failed to open after polling\\n");
            m_status = ConnectionStatus::Error;
            return false;
        }
    }
    
    m_status = ConnectionStatus::Connected;
    Printf("Archipelago: Status set to Connected\\n");
    
    // Send the initial handshake packet immediately
    Printf("Archipelago: About to send Connect packet...\\n");
    SendConnectPacket();
    Printf("Archipelago: Connect packet send initiated\\n");
    
    // Force process any outgoing messages immediately
    Printf("Archipelago: Forcing immediate message processing...\\n");
    ProcessMessages();
    Printf("Archipelago: Initial message processing complete\\n");
    
    Printf("Archipelago: Connect() completed successfully\\n");
    return true;
}

void ArchipelagoClient::SendConnectPacket() {
    Printf("Archipelago: SendConnectPacket() called\\n");
    
    if (!m_websocket) {
        Printf("Archipelago: ERROR - No websocket available in SendConnectPacket!\\n");
        return;
    }
    
    // Check websocket state
    easywsclient::WebSocket::readyStateValues state = m_websocket->getReadyState();
    Printf("Archipelago: WebSocket state in SendConnectPacket: %d\\n", (int)state);
    
    // Create the Connect packet as required by Archipelago protocol
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    Printf("Archipelago: Building Connect packet...\\n");
    
    // Required fields for Connect packet
    packet.AddMember("cmd", "Connect", allocator);
    packet.AddMember("game", "Selaco", allocator);
    packet.AddMember("name", "SelacoPlayer", allocator);
    packet.AddMember("uuid", "selaco-client-001", allocator);
    
    // Protocol version
    rapidjson::Value version(rapidjson::kObjectType);
    version.AddMember("class", "Version", allocator);
    version.AddMember("major", 0, allocator);
    version.AddMember("minor", 4, allocator);
    version.AddMember("build", 0, allocator);
    packet.AddMember("version", version, allocator);
    
    packet.AddMember("items_handling", 7, allocator);
    
    // Tags
    rapidjson::Value tags(rapidjson::kArrayType);
    tags.PushBack("AP", allocator);
    packet.AddMember("tags", tags, allocator);
    
    // Convert to string
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    packet.Accept(writer);
    
    std::string message = buffer.GetString();
    Printf("Archipelago: Connect packet JSON: %s\\n", message.c_str());
    Printf("Archipelago: Packet length: %d bytes\\n", (int)message.length());
    
    // Try sending directly first
    Printf("Archipelago: Attempting direct send...\\n");
    if (m_websocket->getReadyState() == easywsclient::WebSocket::OPEN) {
        m_websocket->send(message);
        Printf("Archipelago: Direct send completed\\n");
        
        // Poll immediately to flush the send
        m_websocket->poll();
        Printf("Archipelago: Polled after send\\n");
    } else {
        Printf("Archipelago: WARNING - WebSocket not OPEN for direct send, queuing instead\\n");
        SendPacket(message);
    }
}

void ArchipelagoClient::Disconnect() {
    Printf("Archipelago: Disconnect() called\\n");
    if (m_websocket) {
        Printf("Archipelago: Closing websocket...\\n");
        m_websocket->close();
        m_websocket.reset();
    }
    m_status = ConnectionStatus::Disconnected;
    m_checkedLocations.clear();
    Printf("Archipelago: Disconnected\\n");
}

bool ArchipelagoClient::IsConnected() const {
    bool connected = m_websocket && m_websocket->getReadyState() == easywsclient::WebSocket::OPEN;
    if (!connected && m_websocket) {
        // Log the actual state if not connected
        Printf("Archipelago: IsConnected check - WebSocket state: %d\\n", 
               (int)m_websocket->getReadyState());
    }
    return connected;
}

void ArchipelagoClient::ProcessMessages() {
    if (!m_websocket) {
        Printf("Archipelago: ProcessMessages - No websocket\\n");
        return;
    }
    
    // Check state before processing
    easywsclient::WebSocket::readyStateValues stateBefore = m_websocket->getReadyState();
    
    // Process incoming messages
    m_websocket->poll();
    m_websocket->dispatch([this](const std::string& message) {
        Printf("Archipelago: Received message: %s\\n", message.c_str());
        HandleMessage(message);
    });
    
    // Check state after processing
    easywsclient::WebSocket::readyStateValues stateAfter = m_websocket->getReadyState();
    
    if (stateBefore != stateAfter) {
        Printf("Archipelago: WebSocket state changed from %d to %d during message processing\\n",
               (int)stateBefore, (int)stateAfter);
    }
    
    // Send queued outgoing messages
    std::lock_guard<std::mutex> lock(m_queueMutex);
    while (!m_outgoingQueue.empty()) {
        std::string msg = m_outgoingQueue.front();
        Printf("Archipelago: Sending queued message: %s\\n", msg.c_str());
        
        if (m_websocket->getReadyState() == easywsclient::WebSocket::OPEN) {
            m_websocket->send(msg);
            Printf("Archipelago: Message sent\\n");
        } else {
            Printf("Archipelago: ERROR - Cannot send, WebSocket not open (state=%d)\\n",
                   (int)m_websocket->getReadyState());
        }
        
        m_outgoingQueue.pop();
    }
}

void ArchipelagoClient::SendPacket(const std::string& json) {
    Printf("Archipelago: SendPacket queuing message: %s\\n", json.c_str());
    
    if (!m_websocket) {
        Printf("Archipelago: ERROR - SendPacket called with no websocket\\n");
        return;
    }
    
    std::lock_guard<std::mutex> lock(m_queueMutex);
    m_outgoingQueue.push(json);
    Printf("Archipelago: Message queued, queue size: %d\\n", (int)m_outgoingQueue.size());
}

void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
    Printf("Archipelago: Authenticate() called for slot: %s\\n", slot.c_str());
    
    if (m_status != ConnectionStatus::Connected && m_status != ConnectionStatus::InGame) {
        Printf("Archipelago: Cannot authenticate - not connected (status=%d)\\n", (int)m_status);
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
    
    std::string message = buffer.GetString();
    Printf("Archipelago: Sending auth packet: %s\\n", message.c_str());
    SendPacket(message);
    
    // Force immediate processing
    ProcessMessages();
}

void ArchipelagoClient::SendLocationCheck(int locationId) {
    std::vector<int> locations = { locationId };
    SendLocationChecks(locations);
}

void ArchipelagoClient::SendLocationChecks(const std::vector<int>& locationIds) {
    Printf("Archipelago: SendLocationChecks called with %d locations\\n", (int)locationIds.size());
    
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
    Printf("Archipelago: StatusUpdate called with status: %s\\n", status.c_str());
    
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
    Printf("Archipelago: SendPing called\\n");
    
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
    
    std::string message = buffer.GetString();
    Printf("Archipelago: Sending ping: %s\\n", message.c_str());
    SendPacket(message);
}

void ArchipelagoClient::HandleMessage(const std::string& message) {
    Printf("Archipelago: HandleMessage called with: %s\\n", message.c_str());
    
    if (m_messageCallback) {
        m_messageCallback(message);
    }
    
    ParsePacket(message);
}

void ArchipelagoClient::ParsePacket(const std::string& json) {
    Printf("Archipelago: ParsePacket called\\n");
    
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    
    if (doc.HasParseError() || !doc.IsArray() || doc.Empty()) {
        Printf("Archipelago: ERROR - Invalid packet format\\n");
        if (doc.HasParseError()) {
            Printf("  Parse error at offset %d\\n", (int)doc.GetErrorOffset());
        }
        return;
    }
    
    Printf("Archipelago: Packet array has %d elements\\n", (int)doc.Size());
    
    for (rapidjson::SizeType i = 0; i < doc.Size(); i++) {
        const rapidjson::Value& packet = doc[i];
        
        if (!packet.HasMember("cmd") || !packet["cmd"].IsString()) {
            Printf("Archipelago: Packet %d missing cmd field\\n", i);
            continue;
        }
        
        std::string cmd = packet["cmd"].GetString();
        Printf("Archipelago: Processing packet type: %s\\n", cmd.c_str());
        
        if (cmd == "RoomInfo") {
            Printf("Archipelago: Received RoomInfo\\n");
            // This is good - means the handshake was accepted!
            
        } else if (cmd == "Connected") {
            Printf("Archipelago: Authentication successful!\\n");
            m_status = ConnectionStatus::InGame;
            
            if (packet.HasMember("slot")) {
                m_slotId = packet["slot"].GetInt();
                Printf("  Slot ID: %d\\n", m_slotId);
            }
            if (packet.HasMember("team")) {
                m_team = packet["team"].GetInt();
                Printf("  Team: %d\\n", m_team);
            }
            
            // Check for missing locations
            if (packet.HasMember("missing_locations")) {
                const auto& missing = packet["missing_locations"];
                if (missing.IsArray()) {
                    Printf("  Missing locations: %d\\n", missing.Size());
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
            Printf("Archipelago: Received items packet\\n");
            
            if (!packet.HasMember("items") || !packet["items"].IsArray()) {
                Printf("  ERROR - No items array\\n");
                continue;
            }
            
            const auto& items = packet["items"];
            Printf("  %d items in packet\\n", (int)items.Size());
            
            for (rapidjson::SizeType j = 0; j < items.Size(); j++) {
                const auto& item = items[j];
                
                int itemId = item["item"].GetInt();
                int locationId = item["location"].GetInt();
                int playerSlot = item["player"].GetInt();
                
                Printf("  Item %d: id=%d, location=%d, player=%d\\n", 
                       j, itemId, locationId, playerSlot);
                
                if (m_itemReceivedCallback) {
                    m_itemReceivedCallback(itemId, locationId, playerSlot);
                }
            }
            
            if (packet.HasMember("index")) {
                m_lastReceivedIndex = packet["index"].GetInt();
                Printf("  Last index: %d\\n", m_lastReceivedIndex);
            }
            
        } else if (cmd == "PrintJSON") {
            Printf("Archipelago: PrintJSON message\\n");
            if (packet.HasMember("text")) {
                Printf("  Text: %s\\n", packet["text"].GetString());
            }
            
        } else if (cmd == "Bounced") {
            Printf("Archipelago: Pong received\\n");
            
        } else {
            Printf("Archipelago: Unhandled packet type: %s\\n", cmd.c_str());
        }
    }
}

} // namespace Archipelago'''
    
    # Create backup
    backup_path = create_backup(filepath)
    
    # Write the debugged content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(debugged_content)
    
    print("✓ Added extensive debugging to archipelago_client.cpp")
    print("\nDebugging features added:")
    print("1. Detailed logging of every step in the connection process")
    print("2. WebSocket state monitoring at each critical point")
    print("3. Direct packet sending attempt before queuing")
    print("4. Immediate polling after sending the Connect packet")
    print("5. Complete packet content logging")
    print("6. Error detection and reporting at each stage")
    
    print("\nThis will help us see:")
    print("- If the WebSocket is actually opening properly")
    print("- If the Connect packet is being sent")
    print("- What the exact packet content looks like")
    print("- If any messages are received from the server")
    print("- Where exactly the connection is failing")
    
    print("\nNext steps:")
    print("1. Rebuild your project with this debug version")
    print("2. Try connecting again: 'ap_connect localhost' or 'ap_connect archipelago.gg 61366'")
    print("3. Look at the console output carefully")
    print("4. Share the complete debug output so we can diagnose the issue")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python archipelago_debug_patch.py <path_to_archipelago_client.cpp>")
        print("Example: python archipelago_debug_patch.py C:\\path\\to\\archipelago_client.cpp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print(f"This script will add debugging to help diagnose connection issues in:")
    print(f"  {filepath}")
    print("\nA backup will be created before any changes are made.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    success = add_debugging_to_client(filepath)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()