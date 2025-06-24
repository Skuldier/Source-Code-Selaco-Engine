#pragma once

#include <string>
#include <functional>
#include <memory>
#include <queue>
#include <mutex>
#include <vector>
#include <set>
#include <chrono>

namespace Archipelago {

// Basic packet types that Archipelago uses
enum class PacketType {
    RoomInfo,
    ConnectionRefused,
    Connected,
    ReceivedItems,
    LocationInfo,
    RoomUpdate,
    PrintJSON,
    DataPackage,
    Bounced,
    InvalidPacket,
    Retrieved,
    SetReply,
    Connect,
    Sync,
    LocationChecks,
    LocationScouts,
    StatusUpdate,
    Say,
    GetDataPackage,
    Bounce,
    Get,
    Set,
    SetNotify
};

// Connection status states
enum class ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    InGame,
    Error
};

// Simple packet structure for future use
struct Packet {
    PacketType type;
    std::string json;
};

// Main Archipelago client class
// This class handles all communication with an Archipelago server
class ArchipelagoClient {
public:
    ArchipelagoClient();
    ~ArchipelagoClient();

    // Connection management
    bool Connect(const std::string& host, int port = 38281);
    void Disconnect();
    bool IsConnected() const;
    ConnectionStatus GetStatus() const { return m_status; }

    // Authentication
    void Authenticate(const std::string& slot, const std::string& password = "", int version = 0);

    // Game operations
    void SendLocationCheck(int locationId);
    void SendLocationChecks(const std::vector<int>& locationIds);
    void StatusUpdate(const std::string& status); // "READY", "PLAYING", "GOAL"

    // Communication
    void SendPacket(const std::string& json);
    void ProcessMessages();
    
    // Callbacks for game integration
    using MessageCallback = std::function<void(const std::string&)>;
    void SetMessageCallback(MessageCallback callback) { m_messageCallback = callback; }
    
    using ItemReceivedCallback = std::function<void(int itemId, int locationId, int playerSlot)>;
    void SetItemReceivedCallback(ItemReceivedCallback callback) { m_itemReceivedCallback = callback; }

    // Testing and debugging
    void SendPing();
    void SetDebugEnabled(bool enabled);

    // Get current slot information
    const std::string& GetSlot() const { return m_slot; }
    int GetSlotId() const { return m_slotId; }
    int GetTeam() const { return m_team; }
    
    // Get connection information
    const std::string& GetHost() const { return m_host; }
    int GetPort() const { return m_port; }

    // Check if we've already checked a location
    bool HasCheckedLocation(int locationId) const {
        return m_checkedLocations.find(locationId) != m_checkedLocations.end();
    }

private:
    // Private implementation
    class Impl;
    std::unique_ptr<Impl> m_impl;

    // Connection state
    ConnectionStatus m_status;
    std::string m_host;
    int m_port;
    
    // Game state
    std::string m_slot;
    int m_slotId;
    int m_team;
    
    // Locations we've already checked
    std::set<int> m_checkedLocations;
    
    // Message handling
    void HandleMessage(const std::string& message);
    void ParsePacket(const std::string& json);
    void SendConnectPacket();
    
    // Message queue for outgoing messages
    std::queue<std::string> m_outgoingQueue;
    std::mutex m_queueMutex;
    
    // Callbacks
    MessageCallback m_messageCallback;
    ItemReceivedCallback m_itemReceivedCallback;
    
    // For tracking received items
    int m_lastReceivedIndex;
    
    // Timeout tracking
    std::chrono::steady_clock::time_point m_connectionTimeout;
};

// Global functions for engine integration
void AP_Init();
void AP_Shutdown();
void AP_Tick();

// Global client instance
extern ArchipelagoClient* g_archipelago;

} // namespace Archipelago