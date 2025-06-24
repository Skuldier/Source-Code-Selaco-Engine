// lws_client.h - LibWebSockets client wrapper for Selaco
#pragma once

#include <libwebsockets.h>
#include <nlohmann/json.hpp>
#include <string>
#include <queue>
#include <mutex>
#include <atomic>
#include <memory>
#include <functional>

namespace Archipelago {

using json = nlohmann::json;

// Forward declarations
class LWSClient;

// Callback types
using MessageCallback = std::function<void(const json&)>;
using ConnectedCallback = std::function<void()>;
using DisconnectedCallback = std::function<void()>;
using ErrorCallback = std::function<void(const std::string&)>;

// Per-connection session data
struct SessionData {
    bool established;
    bool initial_connection;
    LWSClient* client;
    std::vector<uint8_t> rx_buffer;
};

class LWSClient {
public:
    LWSClient();
    ~LWSClient();

    // Connection management
    bool connect(const std::string& host, int port, bool use_ssl = false);
    void disconnect();
    bool isConnected() const { return m_connected.load(); }

    // Send JSON message
    bool sendMessage(const json& message);
    
    // Process events (call from main game loop)
    void service(int timeout_ms = 0);

    // Set callbacks
    void setMessageCallback(MessageCallback cb) { m_messageCallback = cb; }
    void setConnectedCallback(ConnectedCallback cb) { m_connectedCallback = cb; }
    void setDisconnectedCallback(DisconnectedCallback cb) { m_disconnectedCallback = cb; }
    void setErrorCallback(ErrorCallback cb) { m_errorCallback = cb; }

    // Get connection info
    const std::string& getHost() const { return m_host; }
    int getPort() const { return m_port; }

private:
    // LibWebSockets callback (must be static)
    static int websocketCallback(struct lws* wsi, enum lws_callback_reasons reason,
                                void* user, void* in, size_t len);

    // Internal methods
    void processReceivedData(const std::string& data);
    void processOutgoingQueue();
    void triggerError(const std::string& error);

    // LibWebSockets context and connection
    struct lws_context* m_context;
    struct lws* m_wsi;
    
    // Connection state
    std::atomic<bool> m_connected{false};
    std::atomic<bool> m_shouldStop{false};
    std::string m_host;
    int m_port;
    bool m_useSSL;
    
    // Message queues
    std::mutex m_sendQueueMutex;
    std::queue<std::string> m_sendQueue;
    
    // Callbacks
    MessageCallback m_messageCallback;
    ConnectedCallback m_connectedCallback;
    DisconnectedCallback m_disconnectedCallback;
    ErrorCallback m_errorCallback;
    
    // Session data
    SessionData m_sessionData;
    
    // Write buffer with LWS_PRE padding
    static constexpr size_t WRITE_BUFFER_SIZE = 65536;
    std::unique_ptr<unsigned char[]> m_writeBuffer;
};

} // namespace Archipelago