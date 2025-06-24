// lws_client.cpp - LibWebSockets client implementation
#include "lws_client.h"
#include "../common/engine/printf.h"
#include <cstring>
#include <algorithm>

namespace Archipelago {

// Protocol list for WebSocket
static const struct lws_protocols protocols[] = {
    {
        "archipelago-protocol",
        LWSClient::websocketCallback,
        sizeof(SessionData),
        65536,  // rx buffer size
    },
    { NULL, NULL, 0, 0 }  // terminator
};

LWSClient::LWSClient() 
    : m_context(nullptr)
    , m_wsi(nullptr)
    , m_writeBuffer(std::make_unique<unsigned char[]>(WRITE_BUFFER_SIZE))
{
    m_sessionData.client = this;
    m_sessionData.established = false;
    m_sessionData.initial_connection = true;
}

LWSClient::~LWSClient() {
    disconnect();
}

bool LWSClient::connect(const std::string& host, int port, bool use_ssl) {
    if (m_connected) {
        Printf("LWSClient: Already connected\n");
        return false;
    }

    m_host = host;
    m_port = port;
    m_useSSL = use_ssl;
    m_shouldStop = false;

    // Create context
    struct lws_context_creation_info info;
    memset(&info, 0, sizeof(info));
    
    info.port = CONTEXT_PORT_NO_LISTEN;
    info.protocols = protocols;
    info.gid = -1;
    info.uid = -1;
    info.user = this;  // Pass this as user data to access in callbacks
    
    // SSL/TLS options
    if (use_ssl) {
        info.options |= LWS_SERVER_OPTION_DO_SSL_GLOBAL_INIT;
        info.ssl_ca_filepath = nullptr;  // Use system certificate store on Windows
    }

    // Create the context
    m_context = lws_create_context(&info);
    if (!m_context) {
        Printf("LWSClient: Failed to create context\n");
        return false;
    }

    // Set up connection info
    struct lws_client_connect_info ccinfo;
    memset(&ccinfo, 0, sizeof(ccinfo));
    
    ccinfo.context = m_context;
    ccinfo.address = host.c_str();
    ccinfo.port = port;
    ccinfo.path = "/";
    ccinfo.host = lws_canonical_hostname(m_context);
    ccinfo.origin = "origin";
    ccinfo.protocol = protocols[0].name;
    ccinfo.ssl_connection = use_ssl ? LCCSCF_USE_SSL : 0;
    ccinfo.userdata = &m_sessionData;
    
    // Skip certificate validation for development
    // TODO: Remove this in production
    if (use_ssl) {
        ccinfo.ssl_connection |= LCCSCF_SKIP_SERVER_CERT_HOSTNAME_CHECK;
        ccinfo.ssl_connection |= LCCSCF_ALLOW_SELFSIGNED;
    }

    // Attempt connection
    m_wsi = lws_client_connect_via_info(&ccinfo);
    if (!m_wsi) {
        Printf("LWSClient: Failed to initiate connection\n");
        lws_context_destroy(m_context);
        m_context = nullptr;
        return false;
    }

    Printf("LWSClient: Initiating connection to %s:%d%s\n", 
           host.c_str(), port, use_ssl ? " (SSL)" : "");
    
    return true;
}

void LWSClient::disconnect() {
    m_shouldStop = true;
    
    if (m_wsi) {
        // This will trigger LWS_CALLBACK_CLOSED
        lws_set_timeout(m_wsi, PENDING_TIMEOUT_USER_REASON_BASE, 0);
        m_wsi = nullptr;
    }
    
    if (m_context) {
        lws_context_destroy(m_context);
        m_context = nullptr;
    }
    
    m_connected = false;
    
    // Clear queues
    {
        std::lock_guard<std::mutex> lock(m_sendQueueMutex);
        std::queue<std::string> empty;
        std::swap(m_sendQueue, empty);
    }
}

bool LWSClient::sendMessage(const json& message) {
    if (!m_connected) {
        return false;
    }
    
    std::string jsonStr = message.dump();
    
    {
        std::lock_guard<std::mutex> lock(m_sendQueueMutex);
        m_sendQueue.push(jsonStr);
    }
    
    // Request writeable callback
    if (m_wsi) {
        lws_callback_on_writable(m_wsi);
    }
    
    return true;
}

void LWSClient::service(int timeout_ms) {
    if (m_context && !m_shouldStop) {
        lws_service(m_context, timeout_ms);
    }
}

void LWSClient::processReceivedData(const std::string& data) {
    try {
        json message = json::parse(data);
        
        if (m_messageCallback) {
            m_messageCallback(message);
        }
    } catch (const json::exception& e) {
        triggerError("JSON parse error: " + std::string(e.what()));
    }
}

void LWSClient::processOutgoingQueue() {
    std::lock_guard<std::mutex> lock(m_sendQueueMutex);
    
    if (!m_sendQueue.empty() && m_wsi) {
        std::string& message = m_sendQueue.front();
        
        // Ensure message fits in buffer
        if (message.length() + LWS_PRE < WRITE_BUFFER_SIZE) {
            // Copy message to buffer with LWS_PRE offset
            memcpy(m_writeBuffer.get() + LWS_PRE, message.c_str(), message.length());
            
            int written = lws_write(m_wsi, 
                                   m_writeBuffer.get() + LWS_PRE, 
                                   message.length(), 
                                   LWS_WRITE_TEXT);
            
            if (written < 0) {
                triggerError("Write failed");
            } else {
                m_sendQueue.pop();
                
                // Request another write if more messages queued
                if (!m_sendQueue.empty()) {
                    lws_callback_on_writable(m_wsi);
                }
            }
        } else {
            triggerError("Message too large for buffer");
            m_sendQueue.pop();
        }
    }
}

void LWSClient::triggerError(const std::string& error) {
    Printf("LWSClient Error: %s\n", error.c_str());
    
    if (m_errorCallback) {
        m_errorCallback(error);
    }
}

// Static callback function
int LWSClient::websocketCallback(struct lws* wsi, enum lws_callback_reasons reason,
                                void* user, void* in, size_t len) {
    SessionData* session = static_cast<SessionData*>(user);
    
    // Get client instance from context user data for some callbacks
    if (!session && reason != LWS_CALLBACK_CLIENT_FILTER_PRE_ESTABLISH) {
        struct lws_context* context = lws_get_context(wsi);
        if (context) {
            void* userPtr = lws_context_user(context);
            if (userPtr) {
                LWSClient* client = static_cast<LWSClient*>(userPtr);
                session = &client->m_sessionData;
            }
        }
    }
    
    if (!session || !session->client) {
        return 0;
    }
    
    LWSClient* client = session->client;
    
    switch (reason) {
        case LWS_CALLBACK_CLIENT_ESTABLISHED:
            Printf("LWSClient: WebSocket connection established\n");
            session->established = true;
            client->m_connected = true;
            
            if (client->m_connectedCallback) {
                client->m_connectedCallback();
            }
            break;
            
        case LWS_CALLBACK_CLIENT_CONNECTION_ERROR:
            Printf("LWSClient: Connection error\n");
            client->triggerError("Connection failed");
            client->m_connected = false;
            return -1;
            
        case LWS_CALLBACK_CLOSED:
            Printf("LWSClient: Connection closed\n");
            client->m_connected = false;
            
            if (client->m_disconnectedCallback) {
                client->m_disconnectedCallback();
            }
            break;
            
        case LWS_CALLBACK_CLIENT_RECEIVE: {
            if (!in || len == 0) break;
            
            const char* data = static_cast<const char*>(in);
            size_t remaining = lws_remaining_packet_payload(wsi);
            
            // Append to receive buffer
            session->rx_buffer.insert(session->rx_buffer.end(), data, data + len);
            
            // If this is the last fragment, process the complete message
            if (remaining == 0 && lws_is_final_fragment(wsi)) {
                std::string completeMessage(session->rx_buffer.begin(), 
                                          session->rx_buffer.end());
                session->rx_buffer.clear();
                
                client->processReceivedData(completeMessage);
            }
            break;
        }
            
        case LWS_CALLBACK_CLIENT_WRITEABLE:
            client->processOutgoingQueue();
            break;
            
        case LWS_CALLBACK_CLIENT_FILTER_PRE_ESTABLISH:
            // Can be used for additional filtering/setup
            break;
            
        case LWS_CALLBACK_WSI_DESTROY:
            // WebSocket instance is being destroyed
            if (session) {
                session->established = false;
            }
            break;
    }
    
    return 0;
}

} // namespace Archipelago