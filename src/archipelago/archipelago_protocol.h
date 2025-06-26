// archipelago_protocol.h - Archipelago protocol implementation
#pragma once

#include "lws_client.h"
#include <set>
#include <chrono>

namespace Archipelago {

// Connection states for Archipelago
enum class APState {
    Disconnected,
    Connecting,
    Connected,      // WebSocket connected, waiting for RoomInfo
    Authenticated,  // Successfully joined room
    Error
};

// Callback for when items are received
using ItemReceivedCallback = std::function<void(int64_t itemId, int64_t locationId, int playerSlot)>;

class ArchipelagoClient {
public:
    ArchipelagoClient();
    ~ArchipelagoClient();

    // Connection management
    bool connect(const std::string& host, int port = 38281);
    void disconnect();
    bool isConnected() const { return m_state == APState::Authenticated; }
    
    // Authentication
    void authenticate(const std::string& slotName, const std::string& password = "");
    
    // Game actions
    void sendLocationCheck(int64_t locationId);
    void sendLocationChecks(const std::vector<int64_t>& locationIds);
    void setGameStatus(const std::string& status);
    void sendChat(const std::string& message);
    
    // Process events (call from game loop)
    void update();
    
    // Callbacks
    void setItemReceivedCallback(ItemReceivedCallback cb) { m_itemReceivedCallback = cb; }
    
    // State queries
    APState getState() const { return m_state; }
    const std::string& getSlotName() const { return m_slotName; }
    int getSlotNumber() const { return m_slotNumber; }
    
    // Get checked locations
    bool hasCheckedLocation(int64_t locationId) const {
        return m_checkedLocations.find(locationId) != m_checkedLocations.end();
    }

private:
    // Message handlers
    void onWebSocketConnected();
    void onWebSocketDisconnected();
    void onWebSocketError(const std::string& error);
    void onWebSocketMessage(const json& message);
    
    // Protocol message handlers
    void handleRoomInfo(const json& packet);
    void handleConnected(const json& packet);
    void handleConnectionRefused(const json& packet);
    void handleReceivedItems(const json& packet);
    void handleLocationInfo(const json& packet);
    void handleRoomUpdate(const json& packet);
    void handlePrintJSON(const json& packet);
    void handleBounced(const json& packet);
    
    // Send protocol messages
    void sendConnectPacket();
    void sendPacket(const json& packet);
    
    // Utilities
    std::string generateUUID();
    
    // WebSocket client
    std::unique_ptr<LWSClient> m_wsClient;
    
    // Connection state
    APState m_state;
    std::string m_host;
    int m_port;
    
    // Authentication info
    std::string m_slotName;
    std::string m_password;
    int m_slotNumber;
    int m_teamNumber;
    
    // Game state
    std::set<int64_t> m_checkedLocations;
    int m_lastReceivedIndex;
    
    // Server info
    json m_roomInfo;
    json m_slotData;
    
    // Callbacks
    ItemReceivedCallback m_itemReceivedCallback;
    
    // Timing
    std::chrono::steady_clock::time_point m_lastHeartbeat;
    std::chrono::steady_clock::time_point m_connectTime;
};

// Global instance (initialized by AP_Init)
extern ArchipelagoClient* g_archipelago;

// Engine integration functions
extern "C" {
void AP_Init();
void AP_Shutdown();
void AP_Update();
}

} // namespace Archipelago