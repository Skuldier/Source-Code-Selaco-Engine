// archipelago_protocol.cpp - Archipelago protocol implementation
#include "archipelago_protocol.h"
#include "../common/engine/printf.h"
#include <random>
#include <sstream>
#include <iomanip>

namespace Archipelago {

// Global instance
ArchipelagoClient* g_archipelago = nullptr;

void AP_Init() {
    if (!g_archipelago) {
        g_archipelago = new ArchipelagoClient();
        Printf("Archipelago: Client initialized\n");
    }
}

void AP_Shutdown() {
    if (g_archipelago) {
        delete g_archipelago;
        g_archipelago = nullptr;
        Printf("Archipelago: Client shutdown\n");
    }
}

void AP_Update() {
    if (g_archipelago) {
        g_archipelago->update();
    }
}

ArchipelagoClient::ArchipelagoClient()
    : m_state(APState::Disconnected)
    , m_port(38281)
    , m_slotNumber(-1)
    , m_teamNumber(0)
    , m_lastReceivedIndex(0)
{
    m_wsClient = std::make_unique<LWSClient>();
    
    // Set up WebSocket callbacks
    m_wsClient->setConnectedCallback([this]() { onWebSocketConnected(); });
    m_wsClient->setDisconnectedCallback([this]() { onWebSocketDisconnected(); });
    m_wsClient->setErrorCallback([this](const std::string& err) { onWebSocketError(err); });
    m_wsClient->setMessageCallback([this](const json& msg) { onWebSocketMessage(msg); });
}

ArchipelagoClient::~ArchipelagoClient() {
    disconnect();
}

bool ArchipelagoClient::connect(const std::string& host, int port) {
    if (m_state != APState::Disconnected) {
        Printf("Archipelago: Already connected or connecting\n");
        return false;
    }
    
    m_host = host;
    m_port = port;
    m_state = APState::Connecting;
    m_connectTime = std::chrono::steady_clock::now();
    
    Printf("Archipelago: Connecting to %s:%d\n", host.c_str(), port);
    
    // Try SSL first, fall back to non-SSL
    if (!m_wsClient->connect(host, port, true)) {
        Printf("Archipelago: SSL connection failed, trying without SSL\n");
        if (!m_wsClient->connect(host, port, false)) {
            Printf("Archipelago: Connection failed\n");
            m_state = APState::Error;
            return false;
        }
    }
    
    return true;
}

void ArchipelagoClient::disconnect() {
    if (m_state == APState::Disconnected) {
        return;
    }
    
    Printf("Archipelago: Disconnecting\n");
    m_wsClient->disconnect();
    m_state = APState::Disconnected;
    
    // Clear state
    m_checkedLocations.clear();
    m_lastReceivedIndex = 0;
    m_roomInfo.clear();
    m_slotData.clear();
}

void ArchipelagoClient::authenticate(const std::string& slotName, const std::string& password) {
    m_slotName = slotName;
    m_password = password;
    
    if (m_state == APState::Connected) {
        sendConnectPacket();
    }
}

void ArchipelagoClient::sendLocationCheck(int64_t locationId) {
    std::vector<int64_t> locations = { locationId };
    sendLocationChecks(locations);
}

void ArchipelagoClient::sendLocationChecks(const std::vector<int64_t>& locationIds) {
    if (m_state != APState::Authenticated) {
        return;
    }
    
    json packet = {
        {"cmd", "LocationChecks"},
        {"locations", locationIds}
    };
    
    // Track checked locations
    for (int64_t id : locationIds) {
        m_checkedLocations.insert(id);
    }
    
    sendPacket(packet);
}

void ArchipelagoClient::setGameStatus(const std::string& status) {
    if (m_state != APState::Authenticated) {
        return;
    }
    
    json packet = {
        {"cmd", "StatusUpdate"},
        {"status", status}
    };
    
    sendPacket(packet);
}

void ArchipelagoClient::sendChat(const std::string& message) {
    if (m_state != APState::Authenticated) {
        return;
    }
    
    json packet = {
        {"cmd", "Say"},
        {"text", message}
    };
    
    sendPacket(packet);
}

void ArchipelagoClient::update() {
    if (m_wsClient) {
        m_wsClient->service(0);  // Non-blocking
        
        // Send heartbeat every 30 seconds if connected
        if (m_state == APState::Authenticated) {
            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - m_lastHeartbeat);
            
            if (elapsed.count() >= 30) {
                json bounce = {{"cmd", "Bounce"}};
                sendPacket(bounce);
                m_lastHeartbeat = now;
            }
        }
    }
}

void ArchipelagoClient::onWebSocketConnected() {
    Printf("Archipelago: WebSocket connected, waiting for RoomInfo\n");
    m_state = APState::Connected;
    // Server will send RoomInfo automatically
}

void ArchipelagoClient::onWebSocketDisconnected() {
    Printf("Archipelago: WebSocket disconnected\n");
    m_state = APState::Disconnected;
}

void ArchipelagoClient::onWebSocketError(const std::string& error) {
    Printf("Archipelago: WebSocket error: %s\n", error.c_str());
    m_state = APState::Error;
}

void ArchipelagoClient::onWebSocketMessage(const json& message) {
    if (!message.is_array()) {
        Printf("Archipelago: Received non-array message\n");
        return;
    }
    
    for (const auto& packet : message) {
        if (!packet.is_object() || !packet.contains("cmd")) {
            continue;
        }
        
        std::string cmd = packet["cmd"];
        
        if (cmd == "RoomInfo") {
            handleRoomInfo(packet);
        } else if (cmd == "Connected") {
            handleConnected(packet);
        } else if (cmd == "ConnectionRefused") {
            handleConnectionRefused(packet);
        } else if (cmd == "ReceivedItems") {
            handleReceivedItems(packet);
        } else if (cmd == "LocationInfo") {
            handleLocationInfo(packet);
        } else if (cmd == "RoomUpdate") {
            handleRoomUpdate(packet);
        } else if (cmd == "PrintJSON") {
            handlePrintJSON(packet);
        } else if (cmd == "Bounced") {
            handleBounced(packet);
        }
    }
}

void ArchipelagoClient::handleRoomInfo(const json& packet) {
    Printf("Archipelago: Received RoomInfo\n");
    m_roomInfo = packet;
    
    // If we have credentials, connect now
    if (!m_slotName.empty()) {
        sendConnectPacket();
    }
}

void ArchipelagoClient::handleConnected(const json& packet) {
    Printf("Archipelago: Successfully authenticated\n");
    m_state = APState::Authenticated;
    
    if (packet.contains("slot")) {
        m_slotNumber = packet["slot"];
    }
    
    if (packet.contains("team")) {
        m_teamNumber = packet["team"];
    }
    
    if (packet.contains("slot_data")) {
        m_slotData = packet["slot_data"];
    }
    
    m_lastHeartbeat = std::chrono::steady_clock::now();
    
    Printf("Archipelago: Connected as slot %d (%s) on team %d\n", 
           m_slotNumber, m_slotName.c_str(), m_teamNumber);
}

void ArchipelagoClient::handleConnectionRefused(const json& packet) {
    Printf("Archipelago: Connection refused by server\n");
    
    if (packet.contains("errors")) {
        for (const auto& error : packet["errors"]) {
            Printf("  Error: %s\n", error.get<std::string>().c_str());
        }
    }
    
    m_state = APState::Error;
}

void ArchipelagoClient::handleReceivedItems(const json& packet) {
    if (!packet.contains("items")) {
        return;
    }
    
    int index = packet.value("index", 0);
    
    for (const auto& item : packet["items"]) {
        int64_t itemId = item.value("item", 0);
        int64_t locationId = item.value("location", 0);
        int playerSlot = item.value("player", 0);
        
        Printf("Archipelago: Received item %lld from location %lld (player %d)\n",
               itemId, locationId, playerSlot);
        
        if (m_itemReceivedCallback) {
            m_itemReceivedCallback(itemId, locationId, playerSlot);
        }
    }
    
    m_lastReceivedIndex = index + packet["items"].size();
}

void ArchipelagoClient::handleLocationInfo(const json& packet) {
    // Location information for scouting
    if (packet.contains("locations")) {
        for (const auto& loc : packet["locations"]) {
            Printf("Archipelago: Location %lld contains item %lld for player %d\n",
                   loc.value("location", 0),
                   loc.value("item", 0),
                   loc.value("player", 0));
        }
    }
}

void ArchipelagoClient::handleRoomUpdate(const json& packet) {
    // Room state updates (players joining/leaving, etc)
    Printf("Archipelago: Room update received\n");
}

void ArchipelagoClient::handlePrintJSON(const json& packet) {
    // Chat messages and server announcements
    if (packet.contains("data")) {
        std::stringstream message;
        
        for (const auto& part : packet["data"]) {
            if (part.contains("text")) {
                message << part["text"].get<std::string>();
            }
        }
        
        if (!message.str().empty()) {
            Printf("Server: %s\n", message.str().c_str());
        }
    }
}

void ArchipelagoClient::handleBounced(const json& packet) {
    // Heartbeat response - no action needed
}

void ArchipelagoClient::sendConnectPacket() {
    json packet = {
        {"cmd", "Connect"},
        {"password", m_password},
        {"game", "Selaco"},
        {"name", m_slotName},
        {"uuid", generateUUID()},
        {"version", {
            {"major", 0},
            {"minor", 5},
            {"build", 0},
            {"class", "Version"}
        }},
        {"items_handling", 0b111},  // Full item handling
        {"tags", json::array({"AP"})}
    };
    
    sendPacket(packet);
}

void ArchipelagoClient::sendPacket(const json& packet) {
    // Archipelago expects an array of packets
    json message = json::array({packet});
    m_wsClient->sendMessage(message);
}

std::string ArchipelagoClient::generateUUID() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 15);
    
    std::stringstream ss;
    ss << std::hex;
    
    for (int i = 0; i < 32; i++) {
        if (i == 8 || i == 12 || i == 16 || i == 20) {
            ss << "-";
        }
        ss << dis(gen);
    }
    
    return ss.str();
}

} // namespace Archipelago