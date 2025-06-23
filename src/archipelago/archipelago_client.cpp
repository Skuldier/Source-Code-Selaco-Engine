// archipelago_client.cpp
// WebSocket implementation for Archipelago using websocketpp

#include "archipelago_client.h"
#include "../common/engine/printf.h"

// Define necessary preprocessor directives before including WebSocketPP
#define ASIO_STANDALONE
#define _WEBSOCKETPP_CPP11_STL_

// WebSocketPP includes - using standard include style
#include <websocketpp/config/asio_no_tls_client.hpp>
#include <websocketpp/client.hpp>

// JSON handling
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

// Standard library includes
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>
#include <atomic>
#include <condition_variable>
#include <queue>

// Type definitions for cleaner code
typedef websocketpp::client<websocketpp::config::asio_client> ws_client;
typedef websocketpp::config::asio_client::message_type::ptr message_ptr;

namespace Archipelago {

// Global instance
ArchipelagoClient* g_archipelago = nullptr;

// Initialize the Archipelago client system
void AP_Init() {
    if (!g_archipelago) {
        g_archipelago = new ArchipelagoClient();
        Printf("Archipelago: Client initialized\n");
    }
}

// Shutdown the Archipelago client system
void AP_Shutdown() {
    if (g_archipelago) {
        delete g_archipelago;
        g_archipelago = nullptr;
        Printf("Archipelago: Client shutdown\n");
    }
}

// Private implementation class to hide WebSocket details
class ArchipelagoClient::Impl {
public:
    ws_client m_client;
    ws_client::connection_ptr m_connection;
    std::thread m_asio_thread;
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_connected{false};
    std::mutex m_send_mutex;
    std::condition_variable m_connect_cv;
    std::mutex m_connect_mutex;
    
    // Message queue for thread-safe communication
    std::queue<std::string> m_outgoing_queue;
    std::mutex m_queue_mutex;
    
    // Constructor - sets up the WebSocket client
    Impl() {
        // Initialize the ASIO io_service
        m_client.init_asio();
        
        // Set logging to only show errors
        m_client.set_error_channels(websocketpp::log::elevel::all);
        m_client.set_access_channels(websocketpp::log::alevel::none);
        
        // Set up message handler
        m_client.set_message_handler([this](websocketpp::connection_hdl hdl, message_ptr msg) {
            HandleMessage(msg->get_payload());
        });
        
        // Set up connection opened handler
        m_client.set_open_handler([this](websocketpp::connection_hdl hdl) {
            Printf("Archipelago: WebSocket connection opened\n");
            m_connected = true;
            m_connect_cv.notify_all();
        });
        
        // Set up connection closed handler
        m_client.set_close_handler([this](websocketpp::connection_hdl hdl) {
            Printf("Archipelago: WebSocket connection closed\n");
            m_connected = false;
            auto con = m_client.get_con_from_hdl(hdl);
            Printf("  Close code: %d, reason: %s\n", 
                   con->get_remote_close_code(), 
                   con->get_remote_close_reason().c_str());
        });
        
        // Set up connection failed handler
        m_client.set_fail_handler([this](websocketpp::connection_hdl hdl) {
            Printf("Archipelago: WebSocket connection failed\n");
            m_connected = false;
            m_connect_cv.notify_all();
            
            auto con = m_client.get_con_from_hdl(hdl);
            Printf("  Error: %s\n", con->get_ec().message().c_str());
        });
    }
    
    // Destructor
    ~Impl() {
        Stop();
    }
    
    // Start the ASIO processing thread
    void Start() {
        if (!m_running) {
            m_running = true;
            m_asio_thread = std::thread([this]() {
                Printf("Archipelago: ASIO thread started\n");
                m_client.run();
                Printf("Archipelago: ASIO thread ended\n");
            });
        }
    }
    
    // Stop the ASIO processing thread
    void Stop() {
        if (m_running) {
            m_running = false;
            m_client.stop();
            if (m_asio_thread.joinable()) {
                m_asio_thread.join();
            }
        }
    }
    
    // Process incoming messages
    void HandleMessage(const std::string& message);
    
    // Send a message (thread-safe)
    void SendMessage(const std::string& message) {
        if (!m_connected || !m_connection) {
            Printf("Archipelago: Cannot send - not connected\n");
            return;
        }
        
        std::lock_guard<std::mutex> lock(m_send_mutex);
        websocketpp::lib::error_code ec;
        m_client.send(m_connection, message, websocketpp::frame::opcode::text, ec);
        
        if (ec) {
            Printf("Archipelago: Send failed: %s\n", ec.message().c_str());
        }
    }
};

// Main client constructor
ArchipelagoClient::ArchipelagoClient() 
    : m_impl(std::make_unique<Impl>())
    , m_status(ConnectionStatus::Disconnected)
    , m_port(38281)
    , m_team(0)
    , m_slotId(-1)
    , m_lastReceivedIndex(0) {
    Printf("Archipelago: Client object created\n");
}

// Destructor
ArchipelagoClient::~ArchipelagoClient() {
    Printf("Archipelago: Client object destroying\n");
    Disconnect();
}

// Connect to an Archipelago server
bool ArchipelagoClient::Connect(const std::string& host, int port) {
    Printf("Archipelago: Connect() called with host=%s, port=%d\n", host.c_str(), port);
    
    if (m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected or connecting\n");
        return false;
    }
    
    m_host = host;
    m_port = port;
    
    // Build the WebSocket URI
    std::stringstream uri;
    uri << "ws://" << host << ":" << port;
    
    Printf("Archipelago: Attempting to connect to: %s\n", uri.str().c_str());
    m_status = ConnectionStatus::Connecting;
    
    try {
        // Start the ASIO thread if not already running
        m_impl->Start();
        
        // Create a new connection
        websocketpp::lib::error_code ec;
        m_impl->m_connection = m_impl->m_client.get_connection(uri.str(), ec);
        
        if (ec) {
            Printf("Archipelago: Failed to create connection: %s\n", ec.message().c_str());
            m_status = ConnectionStatus::Error;
            return false;
        }
        
        // Queue the connection
        m_impl->m_client.connect(m_impl->m_connection);
        
        // Wait for the connection to be established
        std::unique_lock<std::mutex> lock(m_impl->m_connect_mutex);
        if (m_impl->m_connect_cv.wait_for(lock, std::chrono::seconds(5), 
            [this]{ return m_impl->m_connected.load(); })) {
            
            Printf("Archipelago: Connection established successfully\n");
            m_status = ConnectionStatus::Connected;
            
            // Send the initial Connect packet
            SendConnectPacket();
            
            return true;
        } else {
            Printf("Archipelago: Connection attempt timed out\n");
            m_status = ConnectionStatus::Error;
            return false;
        }
        
    } catch (const std::exception& e) {
        Printf("Archipelago: Connection error: %s\n", e.what());
        m_status = ConnectionStatus::Error;
        return false;
    }
}

// Send the initial Connect packet
void ArchipelagoClient::SendConnectPacket() {
    Printf("Archipelago: Sending initial Connect packet\n");
    
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "Connect", allocator);
    packet.AddMember("game", "Selaco", allocator);
    packet.AddMember("name", "SelacoPlayer", allocator);
    packet.AddMember("uuid", "selaco-client-001", allocator);
    
    rapidjson::Value version(rapidjson::kObjectType);
    version.AddMember("class", "Version", allocator);
    version.AddMember("major", 0, allocator);
    version.AddMember("minor", 4, allocator);
    version.AddMember("build", 0, allocator);
    packet.AddMember("version", version, allocator);
    
    packet.AddMember("items_handling", 7, allocator);
    
    rapidjson::Value tags(rapidjson::kArrayType);
    tags.PushBack("AP", allocator);
    packet.AddMember("tags", tags, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    packet.Accept(writer);
    
    SendPacket(buffer.GetString());
}

// Disconnect from the server
void ArchipelagoClient::Disconnect() {
    Printf("Archipelago: Disconnect() called\n");
    
    if (m_impl->m_connection && m_impl->m_connected) {
        websocketpp::lib::error_code ec;
        m_impl->m_client.close(m_impl->m_connection, 
                               websocketpp::close::status::going_away, 
                               "Client disconnecting", ec);
        
        if (ec) {
            Printf("Archipelago: Error during disconnect: %s\n", ec.message().c_str());
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    m_impl->Stop();
    
    m_status = ConnectionStatus::Disconnected;
    m_checkedLocations.clear();
    Printf("Archipelago: Disconnected\n");
}

// Check if we're currently connected
bool ArchipelagoClient::IsConnected() const {
    return m_impl->m_connected && m_status == ConnectionStatus::Connected;
}

// Process any pending messages
void ArchipelagoClient::ProcessMessages() {
    std::lock_guard<std::mutex> lock(m_queueMutex);
    while (!m_outgoingQueue.empty()) {
        m_impl->SendMessage(m_outgoingQueue.front());
        m_outgoingQueue.pop();
    }
}

// Queue a packet for sending
void ArchipelagoClient::SendPacket(const std::string& json) {
    std::lock_guard<std::mutex> lock(m_queueMutex);
    m_outgoingQueue.push(json);
    
    // For initial connection, send immediately
    if (m_outgoingQueue.size() == 1 && m_impl->m_connected) {
        m_impl->SendMessage(json);
        m_outgoingQueue.pop();
    }
}

// Authenticate to a specific slot
void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
    Printf("Archipelago: Authenticating as slot: %s\n", slot.c_str());
    
    if (m_status != ConnectionStatus::Connected) {
        Printf("Archipelago: Cannot authenticate - not connected\n");
        return;
    }
    
    m_slot = slot;
    
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "ConnectSlot", allocator);
    
    rapidjson::Value slotValue;
    slotValue.SetString(slot.c_str(), allocator);
    packet.AddMember("name", slotValue, allocator);
    
    if (!password.empty()) {
        rapidjson::Value passValue;
        passValue.SetString(password.c_str(), allocator);
        packet.AddMember("password", passValue, allocator);
    }
    
    packet.AddMember("clientVer", version, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    packet.Accept(writer);
    
    SendPacket(buffer.GetString());
}

// Send location checks
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

// Update game status
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

// Send a ping packet
void ArchipelagoClient::SendPing() {
    rapidjson::Document doc;
    doc.SetArray();
    
    rapidjson::Document packet;
    packet.SetObject();
    auto& allocator = packet.GetAllocator();
    
    packet.AddMember("cmd", "Bounce", allocator);
    packet.AddMember("data", rapidjson::Value().SetObject(), allocator);
    packet["data"].AddMember("time", 
        std::chrono::system_clock::now().time_since_epoch().count(), allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
    Printf("Archipelago: Ping sent\n");
}

// Handle incoming message
void ArchipelagoClient::HandleMessage(const std::string& message) {
    Printf("Archipelago: Received message: %s\n", message.c_str());
    
    if (m_messageCallback) {
        m_messageCallback(message);
    }
    
    ParsePacket(message);
}

// Implementation of Impl::HandleMessage
void ArchipelagoClient::Impl::HandleMessage(const std::string& message) {
    if (g_archipelago) {
        g_archipelago->HandleMessage(message);
    }
}

// Parse incoming packet
void ArchipelagoClient::ParsePacket(const std::string& json) {
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    
    if (doc.HasParseError() || !doc.IsArray() || doc.Empty()) {
        Printf("Archipelago: Invalid packet received\n");
        return;
    }
    
    for (rapidjson::SizeType i = 0; i < doc.Size(); i++) {
        const rapidjson::Value& packet = doc[i];
        
        if (!packet.HasMember("cmd") || !packet["cmd"].IsString()) {
            continue;
        }
        
        std::string cmd = packet["cmd"].GetString();
        
        if (cmd == "RoomInfo") {
            Printf("Archipelago: Received RoomInfo - handshake accepted!\n");
            
        } else if (cmd == "Connected") {
            Printf("Archipelago: Authentication successful!\n");
            m_status = ConnectionStatus::InGame;
            
            if (packet.HasMember("slot")) {
                m_slotId = packet["slot"].GetInt();
            }
            if (packet.HasMember("team")) {
                m_team = packet["team"].GetInt();
            }
            
            if (packet.HasMember("missing_locations")) {
                const auto& missing = packet["missing_locations"];
                if (missing.IsArray()) {
                    Printf("Archipelago: %d unchecked locations\n", missing.Size());
                }
            }
            
        } else if (cmd == "ConnectionRefused") {
            Printf("Archipelago: Connection refused!\n");
            m_status = ConnectionStatus::Error;
            
            if (packet.HasMember("errors")) {
                const auto& errors = packet["errors"];
                if (errors.IsArray()) {
                    for (rapidjson::SizeType j = 0; j < errors.Size(); j++) {
                        if (errors[j].IsString()) {
                            Printf("  Error: %s\n", errors[j].GetString());
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
                
                Printf("Archipelago: Received item %d from location %d (player %d)\n", 
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
                Printf("Archipelago: %s\n", packet["text"].GetString());
            }
            
        } else if (cmd == "Bounced") {
            Printf("Archipelago: Pong received\n");
            
        } else {
            Printf("Archipelago: Received packet type: %s\n", cmd.c_str());
        }
    }
}

} // namespace Archipelago