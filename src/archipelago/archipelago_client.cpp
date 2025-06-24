// archipelago_client.cpp
// Thread-safe WebSocketPP implementation for Archipelago

#include "archipelago_client.h"
#include "../common/engine/printf.h"

// Define ASIO standalone before including WebSocketPP
#define ASIO_STANDALONE
#define _WEBSOCKETPP_CPP11_STL_

// WebSocketPP includes
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
#include <memory>

// Network includes for hostname resolution
#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <netdb.h>
    #include <arpa/inet.h>
#endif

// Type definitions
typedef websocketpp::client<websocketpp::config::asio_client> ws_client;
typedef websocketpp::config::asio_client::message_type::ptr message_ptr;
typedef websocketpp::connection_hdl connection_hdl;

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

// Message structure for thread-safe communication
struct ThreadMessage {
    enum Type {
        CONNECT,
        DISCONNECT,
        SEND,
        RECEIVED
    };
    
    Type type;
    std::string data;
    std::string extra;
    int port;
};

// Private implementation class
class ArchipelagoClient::Impl {
public:
    ws_client m_client;
    connection_hdl m_hdl;
    std::thread m_thread;
    
    // Thread synchronization
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_connected{false};
    std::atomic<ConnectionStatus> m_status{ConnectionStatus::Disconnected};
    
    // Message queues
    std::queue<ThreadMessage> m_toThread;
    std::queue<ThreadMessage> m_fromThread;
    std::mutex m_toThreadMutex;
    std::mutex m_fromThreadMutex;
    
    // Constructor
    Impl() {
        try {
            #ifdef _WIN32
            WSADATA wsaData;
            WSAStartup(MAKEWORD(2, 2), &wsaData);
            #endif
            
            // Set up WebSocket client
            m_client.clear_access_channels(websocketpp::log::alevel::all);
            m_client.clear_error_channels(websocketpp::log::elevel::all);
            
            m_client.init_asio();
            
            // Set handlers
            m_client.set_open_handler([this](connection_hdl hdl) {
                on_open(hdl);
            });
            
            m_client.set_close_handler([this](connection_hdl hdl) {
                on_close(hdl);
            });
            
            m_client.set_fail_handler([this](connection_hdl hdl) {
                on_fail(hdl);
            });
            
            m_client.set_message_handler([this](connection_hdl hdl, message_ptr msg) {
                on_message(hdl, msg);
            });
            
        } catch (const std::exception& e) {
            Printf("Archipelago: Error initializing: %s\n", e.what());
        }
    }
    
    // Destructor
    ~Impl() {
        StopThread();
        #ifdef _WIN32
        WSACleanup();
        #endif
    }
    
    // Start the worker thread
    void StartThread() {
        if (m_running.exchange(true)) return; // Already running
        
        m_thread = std::thread([this]() {
            ThreadLoop();
        });
    }
    
    // Stop the worker thread
    void StopThread() {
        if (!m_running.exchange(false)) return; // Not running
        
        // Wake up the thread
        m_client.get_io_service().stop();
        
        if (m_thread.joinable()) {
            m_thread.join();
        }
    }
    
    // Main thread loop
    void ThreadLoop() {
        Printf("Archipelago: Worker thread started\n");
        
        while (m_running) {
            try {
                // Process pending messages
                ProcessThreadMessages();
                
                // Run ASIO for a short time
                m_client.get_io_service().reset();
                m_client.get_io_service().run_for(std::chrono::milliseconds(10));
                
                // Small sleep to prevent busy waiting
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                
            } catch (const std::exception& e) {
                Printf("Archipelago: Thread error: %s\n", e.what());
            }
        }
        
        Printf("Archipelago: Worker thread stopped\n");
    }
    
    // Process messages sent to the thread
    void ProcessThreadMessages() {
        std::unique_lock<std::mutex> lock(m_toThreadMutex);
        while (!m_toThread.empty()) {
            ThreadMessage msg = m_toThread.front();
            m_toThread.pop();
            lock.unlock();
            
            switch (msg.type) {
                case ThreadMessage::CONNECT:
                    DoConnect(msg.data, msg.port);
                    break;
                case ThreadMessage::DISCONNECT:
                    DoDisconnect();
                    break;
                case ThreadMessage::SEND:
                    DoSend(msg.data);
                    break;
            }
            
            lock.lock();
        }
    }
    
    // Perform connection
    void DoConnect(const std::string& uri, int port) {
        try {
            websocketpp::lib::error_code ec;
            auto con = m_client.get_connection(uri, ec);
            
            if (ec) {
                Printf("Archipelago: Connection creation failed: %s\n", ec.message().c_str());
                m_status = ConnectionStatus::Error;
                return;
            }
            
            m_hdl = con->get_handle();
            m_client.connect(con);
            
        } catch (const std::exception& e) {
            Printf("Archipelago: Connect error: %s\n", e.what());
            m_status = ConnectionStatus::Error;
        }
    }
    
    // Perform disconnection
    void DoDisconnect() {
        try {
            if (m_connected) {
                websocketpp::lib::error_code ec;
                m_client.close(m_hdl, websocketpp::close::status::going_away, "Client disconnect", ec);
            }
        } catch (...) {
            // Ignore errors during disconnect
        }
    }
    
    // Send a message
    void DoSend(const std::string& message) {
        try {
            if (m_connected) {
                websocketpp::lib::error_code ec;
                m_client.send(m_hdl, message, websocketpp::frame::opcode::text, ec);
                
                if (ec) {
                    Printf("Archipelago: Send error: %s\n", ec.message().c_str());
                }
            }
        } catch (const std::exception& e) {
            Printf("Archipelago: Send exception: %s\n", e.what());
        }
    }
    
    // Connection opened
    void on_open(connection_hdl hdl) {
        m_connected = true;
        m_status = ConnectionStatus::Connected;
        
        // Queue a message for the main thread
        ThreadMessage msg;
        msg.type = ThreadMessage::RECEIVED;
        msg.data = "__CONNECTED__";
        
        std::lock_guard<std::mutex> lock(m_fromThreadMutex);
        m_fromThread.push(msg);
    }
    
    // Connection closed
    void on_close(connection_hdl hdl) {
        m_connected = false;
        m_status = ConnectionStatus::Disconnected;
        
        ThreadMessage msg;
        msg.type = ThreadMessage::RECEIVED;
        msg.data = "__DISCONNECTED__";
        
        std::lock_guard<std::mutex> lock(m_fromThreadMutex);
        m_fromThread.push(msg);
    }
    
    // Connection failed
    void on_fail(connection_hdl hdl) {
        m_connected = false;
        m_status = ConnectionStatus::Error;
        
        ThreadMessage msg;
        msg.type = ThreadMessage::RECEIVED;
        msg.data = "__FAILED__";
        
        std::lock_guard<std::mutex> lock(m_fromThreadMutex);
        m_fromThread.push(msg);
    }
    
    // Message received
    void on_message(connection_hdl hdl, message_ptr msg) {
        ThreadMessage tmsg;
        tmsg.type = ThreadMessage::RECEIVED;
        tmsg.data = msg->get_payload();
        
        std::lock_guard<std::mutex> lock(m_fromThreadMutex);
        m_fromThread.push(tmsg);
    }
    
    // Send message to thread
    void SendToThread(const ThreadMessage& msg) {
        std::lock_guard<std::mutex> lock(m_toThreadMutex);
        m_toThread.push(msg);
    }
    
    // Get messages from thread
    std::vector<ThreadMessage> GetFromThread() {
        std::vector<ThreadMessage> messages;
        std::lock_guard<std::mutex> lock(m_fromThreadMutex);
        
        while (!m_fromThread.empty()) {
            messages.push_back(m_fromThread.front());
            m_fromThread.pop();
        }
        
        return messages;
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
    Printf("Archipelago: Client created\n");
}

// Destructor
ArchipelagoClient::~ArchipelagoClient() {
    Disconnect();
    Printf("Archipelago: Client destroyed\n");
}

// Connect to server
bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected or connecting\n");
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
    uri << "ws://" << resolved_host << ":" << port;
    
    Printf("Archipelago: Connecting to %s\n", uri.str().c_str());
    
    // Start thread if not running
    m_impl->StartThread();
    
    // Send connect message to thread
    ThreadMessage msg;
    msg.type = ThreadMessage::CONNECT;
    msg.data = uri.str();
    msg.port = port;
    m_impl->SendToThread(msg);
    
    m_status = ConnectionStatus::Connecting;
    return true;
}

// Disconnect from server
void ArchipelagoClient::Disconnect() {
    if (m_status == ConnectionStatus::Disconnected) return;
    
    // Send disconnect message to thread
    ThreadMessage msg;
    msg.type = ThreadMessage::DISCONNECT;
    m_impl->SendToThread(msg);
    
    // Give it time to disconnect
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    // Stop thread
    m_impl->StopThread();
    
    m_status = ConnectionStatus::Disconnected;
    m_checkedLocations.clear();
    Printf("Archipelago: Disconnected\n");
}

// Check connection status
bool ArchipelagoClient::IsConnected() const {
    return m_impl->m_connected.load();
}

// Process messages (called from main thread)
void ArchipelagoClient::ProcessMessages() {
    // Get messages from worker thread
    auto messages = m_impl->GetFromThread();
    
    for (const auto& msg : messages) {
        if (msg.data == "__CONNECTED__") {
            Printf("Archipelago: Connected successfully\n");
            m_status = ConnectionStatus::Connected;
            SendConnectPacket();
        } else if (msg.data == "__DISCONNECTED__") {
            Printf("Archipelago: Disconnected\n");
            m_status = ConnectionStatus::Disconnected;
        } else if (msg.data == "__FAILED__") {
            Printf("Archipelago: Connection failed\n");
            m_status = ConnectionStatus::Error;
        } else {
            // Regular message
            HandleMessage(msg.data);
        }
    }
    
    // Update our status from the implementation
    m_status = m_impl->m_status.load();
}

// Send packet to server
void ArchipelagoClient::SendPacket(const std::string& json) {
    if (m_status != ConnectionStatus::Connected && m_status != ConnectionStatus::InGame) {
        return;
    }
    
    ThreadMessage msg;
    msg.type = ThreadMessage::SEND;
    msg.data = json;
    m_impl->SendToThread(msg);
}

// Send initial connect packet
void ArchipelagoClient::SendConnectPacket() {
    Printf("Archipelago: Sending Connect packet\n");
    
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

// Authenticate with server
void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
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

// Send location check
void ArchipelagoClient::SendLocationCheck(int locationId) {
    std::vector<int> locations = { locationId };
    SendLocationChecks(locations);
}

// Send multiple location checks
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

// Send ping
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
    if (m_messageCallback) {
        m_messageCallback(message);
    }
    
    ParsePacket(message);
}

// Parse packet
void ArchipelagoClient::ParsePacket(const std::string& json) {
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    
    if (doc.HasParseError() || !doc.IsArray() || doc.Empty()) {
        Printf("Archipelago: Invalid packet\n");
        return;
    }
    
    for (rapidjson::SizeType i = 0; i < doc.Size(); i++) {
        const rapidjson::Value& packet = doc[i];
        
        if (!packet.HasMember("cmd") || !packet["cmd"].IsString()) {
            continue;
        }
        
        std::string cmd = packet["cmd"].GetString();
        
        if (cmd == "RoomInfo") {
            Printf("Archipelago: Received RoomInfo\n");
            
        } else if (cmd == "Connected") {
            Printf("Archipelago: Authentication successful!\n");
            m_status = ConnectionStatus::InGame;
            
            if (packet.HasMember("slot")) {
                m_slotId = packet["slot"].GetInt();
            }
            if (packet.HasMember("team")) {
                m_team = packet["team"].GetInt();
            }
            
        } else if (cmd == "ConnectionRefused") {
            Printf("Archipelago: Connection refused!\n");
            m_status = ConnectionStatus::Error;
            
        } else if (cmd == "ReceivedItems") {
            // Handle received items
            
        } else if (cmd == "Bounced") {
            Printf("Archipelago: Pong received\n");
            
        } else {
            Printf("Archipelago: Received: %s\n", cmd.c_str());
        }
    }
}

} // namespace Archipelago