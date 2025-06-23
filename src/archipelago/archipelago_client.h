#pragma once

#include <string>
#include <functional>
#include <memory>
#include <queue>
#include <mutex>

// Forward declarations
namespace easywsclient {
    class WebSocket;
}

namespace Archipelago {

// Basic packet types
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

// Connection status
enum class ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    InGame,
    Error
};

// Simple packet structure
struct Packet {
    PacketType type;
    std::string json;
};

// Main Archipelago client class
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
    
    // Callbacks
    using MessageCallback = std::function<void(const std::string&)>;
    void SetMessageCallback(MessageCallback callback) { m_messageCallback = callback; }
    
    using ItemReceivedCallback = std::function<void(int itemId, int locationId, int playerSlot)>;
    void SetItemReceivedCallback(ItemReceivedCallback callback) { m_itemReceivedCallback = callback; }

    // Testing
    void SendPing();

private:
    void HandleMessage(const std::string& message);
    void ParsePacket(const std::string& json);
    
    std::unique_ptr<easywsclient::WebSocket> m_websocket;
    ConnectionStatus m_status;
    
    // Connection info
    std::string m_host;
    int m_port;
    std::string m_slot;
    int m_team;
    int m_slotId;
    
    // Message handling
    std::queue<std::string> m_outgoingQueue;
    std::mutex m_queueMutex;
    
    // Callbacks
    MessageCallback m_messageCallback;
    ItemReceivedCallback m_itemReceivedCallback;
    
    // State tracking
    int m_lastReceivedIndex;
    std::vector<int> m_checkedLocations;
};

// Global instance (singleton pattern)
extern ArchipelagoClient* g_archipelago;

// Initialization functions
void AP_Init();
void AP_Shutdown();

} // namespace Archipelago