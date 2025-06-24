// archipelago_client.h
// Header file for Archipelago client with enhanced debugging support

#pragma once

#include <string>
#include <functional>
#include <memory>
#include <queue>
#include <mutex>
#include <vector>
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

private:
    // Private implementation class
    // This hides all the WebSocket details from the header
    class Impl;
    
    // IMPORTANT: m_impl must be initialized first in constructor
    std::unique_ptr<Impl> m_impl;
    
    // Internal methods
    void HandleMessage(const std::string& message);
    void ParsePacket(const std::string& json);
    void SendConnectPacket();
    
    // Connection state
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
    std::chrono::steady_clock::time_point m_connectionTimeout;
};

// Global instance (singleton pattern)
extern ArchipelagoClient* g_archipelago;

// Initialization functions
void AP_Init();
void AP_Shutdown();

// Game loop tick function
void AP_Tick();

} // namespace Archipelago