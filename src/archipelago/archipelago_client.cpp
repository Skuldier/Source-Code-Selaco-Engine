// archipelago_client.cpp
// Complete implementation using basic sockets to avoid WebSocketPP crashes
// Fixed version with compilation error fixes

#include "archipelago_client.h"
#include "../common/engine/printf.h"
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

#include <thread>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <sstream>
#include <random>
#include <iomanip>
#include <chrono>
#include <algorithm>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define SOCKET_ERROR_CHECK(x) ((x) == SOCKET_ERROR)
    #define CLOSE_SOCKET closesocket
    // Prevent Windows.h from defining min/max macros
    #ifndef NOMINMAX
        #define NOMINMAX
    #endif
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netinet/tcp.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <netdb.h>
    #include <fcntl.h>
    typedef int socket_t;
    #define INVALID_SOCKET -1
    #define SOCKET_ERROR -1
    #define SOCKET_ERROR_CHECK(x) ((x) < 0)
    #define CLOSE_SOCKET close
#endif

namespace Archipelago {

// Global instance
ArchipelagoClient* g_archipelago = nullptr;

void AP_Init() {
    if (!g_archipelago) {
        g_archipelago = new ArchipelagoClient();
        Printf("Archipelago: Simple client initialized\n");
    }
}

void AP_Shutdown() {
    if (g_archipelago) {
        delete g_archipelago;
        g_archipelago = nullptr;
        Printf("Archipelago: Client shutdown\n");
    }
}

// Simple base64 encoding for WebSocket handshake
std::string base64_encode(const unsigned char* data, size_t len) {
    static const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    result.reserve(((len + 2) / 3) * 4);
    
    for (size_t i = 0; i < len; i += 3) {
        int b = (data[i] & 0xFC) >> 2;
        result.push_back(chars[b]);
        b = (data[i] & 0x03) << 4;
        if (i + 1 < len) {
            b |= (data[i + 1] & 0xF0) >> 4;
            result.push_back(chars[b]);
            b = (data[i + 1] & 0x0F) << 2;
            if (i + 2 < len) {
                b |= (data[i + 2] & 0xC0) >> 6;
                result.push_back(chars[b]);
                b = data[i + 2] & 0x3F;
                result.push_back(chars[b]);
            } else {
                result.push_back(chars[b]);
                result.push_back('=');
            }
        } else {
            result.push_back(chars[b]);
            result.append("==");
        }
    }
    
    return result;
}

// Generate WebSocket key
std::string generate_websocket_key() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    unsigned char bytes[16];
    for (int i = 0; i < 16; ++i) {
        bytes[i] = dis(gen);
    }
    
    return base64_encode(bytes, 16);
}

// Simple WebSocket frame decoder
class WebSocketFrameDecoder {
public:
    enum OpCode {
        CONTINUATION = 0x0,
        TEXT = 0x1,
        BINARY = 0x2,
        CLOSE = 0x8,
        PING = 0x9,
        PONG = 0xA
    };
    
    struct Frame {
        bool fin;
        OpCode opcode;
        std::vector<uint8_t> payload;
    };
    
    bool DecodeFrame(const std::vector<uint8_t>& data, size_t& offset, Frame& frame) {
        // Add safety check
        if (offset >= data.size()) {
            return false;
        }
        
        if (data.size() - offset < 2) return false;
        
        uint8_t byte1 = data[offset++];
        uint8_t byte2 = data[offset++];
        
        frame.fin = (byte1 & 0x80) != 0;
        frame.opcode = static_cast<OpCode>(byte1 & 0x0F);
        
        bool masked = (byte2 & 0x80) != 0;
        uint64_t payload_len = byte2 & 0x7F;
        
        if (payload_len == 126) {
            if (data.size() - offset < 2) return false;
            payload_len = (data[offset] << 8) | data[offset + 1];
            offset += 2;
        } else if (payload_len == 127) {
            if (data.size() - offset < 8) return false;
            payload_len = 0;
            for (int i = 0; i < 8; ++i) {
                payload_len = (payload_len << 8) | data[offset++];
            }
        }
        
        if (masked) {
            if (data.size() - offset < 4) return false;
            offset += 4; // Skip mask key (server shouldn't send masked frames)
        }
        
        if (data.size() - offset < payload_len) return false;
        
        frame.payload.assign(data.begin() + offset, data.begin() + offset + payload_len);
        offset += payload_len;
        
        return true;
    }
};

// Simple WebSocket frame encoder
std::vector<uint8_t> EncodeWebSocketFrame(const std::string& message) {
    std::vector<uint8_t> frame;
    
    // FIN = 1, RSV = 0, Opcode = 1 (text)
    frame.push_back(0x81);
    
    size_t len = message.length();
    
    // Client must mask, so set mask bit
    if (len <= 125) {
        frame.push_back(0x80 | len);
    } else if (len <= 65535) {
        frame.push_back(0x80 | 126);
        frame.push_back((len >> 8) & 0xFF);
        frame.push_back(len & 0xFF);
    } else {
        frame.push_back(0x80 | 127);
        for (int i = 7; i >= 0; --i) {
            frame.push_back((len >> (i * 8)) & 0xFF);
        }
    }
    
    // Generate mask key
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    uint8_t mask[4];
    for (int i = 0; i < 4; ++i) {
        mask[i] = dis(gen);
        frame.push_back(mask[i]);
    }
    
    // Mask and add payload
    for (size_t i = 0; i < message.length(); ++i) {
        frame.push_back(message[i] ^ mask[i % 4]);
    }
    
    return frame;
}

// Private implementation
class ArchipelagoClient::Impl {
public:
    socket_t m_socket{INVALID_SOCKET};
    std::thread m_readThread;
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_connected{false};
    std::atomic<int> m_debugState{0};  // For crash debugging
    
    std::queue<std::string> m_incomingMessages;
    std::queue<std::string> m_outgoingMessages;
    std::mutex m_incomingMutex;
    std::mutex m_outgoingMutex;
    
    std::string m_host;
    int m_port;
    std::vector<uint8_t> m_initialData;  // Store any data that comes with handshake
    
    Impl() {
        #ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            Printf("Archipelago: WSAStartup failed\n");
        }
        #endif
    }
    
    ~Impl() {
        Disconnect();
        #ifdef _WIN32
        WSACleanup();
        #endif
    }
    
    void SetDebugState(int state) {
        m_debugState = state;
        Printf("Archipelago: Debug state = %d\n", state);
    }
    
    bool Connect(const std::string& host, int port) {
        Printf("Archipelago: Simple client connecting to %s:%d\n", host.c_str(), port);
        
        m_host = host;
        m_port = port;
        
        // Create socket
        m_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (m_socket == INVALID_SOCKET) {
            Printf("Archipelago: Failed to create socket\n");
            return false;
        }
        
        // Set socket options for better stability
        #ifdef _WIN32
            // Disable Nagle's algorithm for better latency
            int flag = 1;
            setsockopt(m_socket, IPPROTO_TCP, TCP_NODELAY, (char*)&flag, sizeof(flag));
            
            // Set receive timeout to prevent infinite blocking
            DWORD timeout = 5000; // 5 seconds
            setsockopt(m_socket, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout));
        #endif
        
        // Resolve host
        struct sockaddr_in server_addr;
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port);
        
        // Try to parse as IP first
        #ifdef _WIN32
            // For Windows, use inet_addr instead of inet_pton
            unsigned long addr = inet_addr(host.c_str());
            if (addr != INADDR_NONE) {
                server_addr.sin_addr.s_addr = addr;
            } else {
                // Not an IP, try hostname resolution
                struct hostent* he = gethostbyname(host.c_str());
                if (he == nullptr) {
                    Printf("Archipelago: Failed to resolve hostname\n");
                    CLOSE_SOCKET(m_socket);
                    m_socket = INVALID_SOCKET;
                    return false;
                }
                memcpy(&server_addr.sin_addr, he->h_addr_list[0], he->h_length);
            }
        #else
            if (inet_pton(AF_INET, host.c_str(), &server_addr.sin_addr) != 1) {
                // Not an IP, try hostname resolution
                struct hostent* he = gethostbyname(host.c_str());
                if (he == nullptr) {
                    Printf("Archipelago: Failed to resolve hostname\n");
                    CLOSE_SOCKET(m_socket);
                    m_socket = INVALID_SOCKET;
                    return false;
                }
                memcpy(&server_addr.sin_addr, he->h_addr_list[0], he->h_length);
            }
        #endif
        
        // Connect
        if (connect(m_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
            Printf("Archipelago: Failed to connect\n");
            CLOSE_SOCKET(m_socket);
            m_socket = INVALID_SOCKET;
            return false;
        }
        
        Printf("Archipelago: TCP connection established\n");
        
        // Send WebSocket handshake
        if (!SendWebSocketHandshake()) {
            Printf("Archipelago: WebSocket handshake failed\n");
            CLOSE_SOCKET(m_socket);
            m_socket = INVALID_SOCKET;
            return false;
        }
        
        // IMPORTANT: Ensure socket is ready before starting thread
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Start read thread
        m_running = true;
        
        // Use exception handling for thread creation
        try {
            m_readThread = std::thread([this]() { 
                Printf("Archipelago: Thread lambda started\n");
                ReadThread(); 
                Printf("Archipelago: Thread lambda ended\n");
            });
        } catch (const std::exception& e) {
            Printf("Archipelago: Failed to create thread: %s\n", e.what());
            CLOSE_SOCKET(m_socket);
            m_socket = INVALID_SOCKET;
            m_running = false;
            return false;
        }
        
        // Give thread time to start properly
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        
        return m_connected;
    }
    
    void Disconnect() {
        m_running = false;
        
        if (m_socket != INVALID_SOCKET) {
            // Send close frame
            std::vector<uint8_t> closeFrame;
            closeFrame.push_back(0x88); // FIN + CLOSE opcode
            closeFrame.push_back(0x80); // Masked + 0 length
            // Add mask key (4 zero bytes for simplicity)
            closeFrame.resize(6, 0);
            
            send(m_socket, (const char*)closeFrame.data(), closeFrame.size(), 0);
            
            CLOSE_SOCKET(m_socket);
            m_socket = INVALID_SOCKET;
        }
        
        if (m_readThread.joinable()) {
            m_readThread.join();
        }
        
        m_connected = false;
    }
    
    bool SendWebSocketHandshake() {
        std::string key = generate_websocket_key();
        
        std::stringstream handshake;
        handshake << "GET / HTTP/1.1\r\n";
        handshake << "Host: " << m_host << ":" << m_port << "\r\n";
        handshake << "Upgrade: websocket\r\n";
        handshake << "Connection: Upgrade\r\n";
        handshake << "Sec-WebSocket-Key: " << key << "\r\n";
        handshake << "Sec-WebSocket-Version: 13\r\n";
        handshake << "\r\n";
        
        std::string request = handshake.str();
        Printf("Archipelago: Sending handshake (%zu bytes)\n", request.length());
        
        if (send(m_socket, request.c_str(), request.length(), 0) == SOCKET_ERROR) {
            Printf("Archipelago: Failed to send handshake\n");
            return false;
        }
        
        // Read response - may come in multiple chunks
        std::string response;
        char buffer[1024];
        int total_received = 0;
        
        // Wait up to 5 seconds for response
        auto start_time = std::chrono::steady_clock::now();
        
        while (response.find("\r\n\r\n") == std::string::npos) {
            int received = recv(m_socket, buffer, sizeof(buffer) - 1, 0);
            
            if (received > 0) {
                buffer[received] = '\0';
                response += buffer;
                total_received += received;
                Printf("Archipelago: Received %d bytes of handshake response (total: %d)\n", 
                       received, total_received);
            } else if (received == 0) {
                Printf("Archipelago: Connection closed during handshake\n");
                return false;
            } else {
                #ifdef _WIN32
                    int error = WSAGetLastError();
                    if (error != WSAEWOULDBLOCK) {
                        Printf("Archipelago: Handshake recv error: %d\n", error);
                        return false;
                    }
                #else
                    if (errno != EAGAIN && errno != EWOULDBLOCK) {
                        Printf("Archipelago: Handshake recv error: %d\n", errno);
                        return false;
                    }
                #endif
            }
            
            // Check timeout
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::steady_clock::now() - start_time).count();
            if (elapsed > 5) {
                Printf("Archipelago: Handshake response timeout\n");
                return false;
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        
        Printf("Archipelago: Full handshake response (%zu bytes):\n%s\n", 
               response.length(), response.c_str());
        
        // Check for successful upgrade
        if (response.find("HTTP/1.1 101") != std::string::npos &&
            response.find("Upgrade: websocket") != std::string::npos) {
            Printf("Archipelago: WebSocket handshake successful\n");
            
            // IMPORTANT: Extract any data after the headers
            size_t header_end = response.find("\r\n\r\n");
            if (header_end != std::string::npos) {
                header_end += 4; // Skip past \r\n\r\n
                if (header_end < response.length()) {
                    // There's data after headers - this might be the first WebSocket frame
                    Printf("Archipelago: Found %zu bytes after headers\n", 
                           response.length() - header_end);
                    
                    // Save this data to be processed by the read thread
                    m_initialData.clear();
                    for (size_t j = header_end; j < response.length(); j++) {
                        m_initialData.push_back((uint8_t)response[j]);
                    }
                    
                    Printf("Archipelago: Saved initial data (hex): ");
                    size_t displayCount = (std::min)(size_t(16), m_initialData.size());
                    for (size_t j = 0; j < displayCount; j++) {
                        Printf("%02X ", m_initialData[j]);
                    }
                    Printf("\n");
                }
            }
            
            m_connected = true;
            return true;
        }
        
        Printf("Archipelago: WebSocket handshake failed\n");
        return false;
    }
    
    void ReadThread() {
        SetDebugState(100); // Entering ReadThread
        Printf("Archipelago: Read thread started (thread ID: %d)\n", std::this_thread::get_id());
        
        // Check socket validity first
        if (m_socket == INVALID_SOCKET) {
            SetDebugState(101); // Invalid socket
            Printf("Archipelago: ERROR - Invalid socket in read thread!\n");
            m_connected = false;
            return;
        }
        
        SetDebugState(102); // Setting non-blocking mode
        
        // Set socket to non-blocking mode to avoid hangs
        #ifdef _WIN32
            u_long mode = 1;  // 1 = non-blocking
            if (ioctlsocket(m_socket, FIONBIO, &mode) != 0) {
                Printf("Archipelago: Failed to set non-blocking mode\n");
            } else {
                Printf("Archipelago: Socket set to non-blocking mode\n");
            }
        #else
            int flags = fcntl(m_socket, F_GETFL, 0);
            fcntl(m_socket, F_SETFL, flags | O_NONBLOCK);
        #endif
        
        SetDebugState(103); // Creating buffers
        std::vector<uint8_t> buffer(4096);
        std::vector<uint8_t> frameBuffer;
        WebSocketFrameDecoder decoder;
        
        // Process any initial data from handshake
        if (!m_initialData.empty()) {
            Printf("Archipelago: Processing %zu bytes of initial data\n", m_initialData.size());
            frameBuffer = m_initialData;
            m_initialData.clear();
        }
        
        SetDebugState(104); // Entering main loop
        Printf("Archipelago: Entering read loop...\n");
        
        while (m_running && m_socket != INVALID_SOCKET) {
            // Add try-catch for safety
            try {
                SetDebugState(105); // About to recv
                
                int received = recv(m_socket, (char*)buffer.data(), buffer.size(), 0);
                
                SetDebugState(106); // After recv
                
                if (received > 0) {
                    Printf("Archipelago: Received %d bytes\n", received);
                    
                    // Debug: Print first few bytes
                    Printf("Archipelago: First bytes: ");
                    int displayCount = (std::min)(16, received);
                    for (int j = 0; j < displayCount; j++) {
                        Printf("%02X ", buffer[j]);
                    }
                    Printf("\n");
                    
                    frameBuffer.insert(frameBuffer.end(), buffer.begin(), buffer.begin() + received);
                    
                    // Try to decode frames
                    size_t offset = 0;
                    while (offset < frameBuffer.size()) {
                        Printf("Archipelago: Attempting to decode frame at offset %zu\n", offset);
                        
                        WebSocketFrameDecoder::Frame frame;
                        if (decoder.DecodeFrame(frameBuffer, offset, frame)) {
                            Printf("Archipelago: Frame decoded successfully\n");
                            HandleFrame(frame);
                        } else {
                            Printf("Archipelago: Not enough data for frame, waiting for more\n");
                            break;
                        }
                    }
                    
                    // Remove processed data
                    if (offset > 0) {
                        frameBuffer.erase(frameBuffer.begin(), frameBuffer.begin() + offset);
                    }
                    
                } else if (received == 0) {
                    Printf("Archipelago: Connection closed by server\n");
                    break;
                } else {
                    // Check for non-blocking "would block" error
                    #ifdef _WIN32
                        int error = WSAGetLastError();
                        if (error == WSAEWOULDBLOCK) {
                            // No data available, just continue
                            std::this_thread::sleep_for(std::chrono::milliseconds(10));
                            continue;
                        } else {
                            Printf("Archipelago: Receive error: %d\n", error);
                            break;
                        }
                    #else
                        if (errno == EAGAIN || errno == EWOULDBLOCK) {
                            // No data available, just continue
                            std::this_thread::sleep_for(std::chrono::milliseconds(10));
                            continue;
                        } else {
                            Printf("Archipelago: Receive error: %d\n", errno);
                            break;
                        }
                    #endif
                }
                
                // Small delay to prevent CPU spinning
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                
            } catch (const std::exception& e) {
                Printf("Archipelago: Exception in read thread: %s\n", e.what());
                break;
            } catch (...) {
                Printf("Archipelago: Unknown exception in read thread\n");
                break;
            }
        }
        
        m_connected = false;
        Printf("Archipelago: Read thread ended\n");
    }
    
    void HandleFrame(const WebSocketFrameDecoder::Frame& frame) {
        switch (frame.opcode) {
            case WebSocketFrameDecoder::TEXT: {
                std::string message(frame.payload.begin(), frame.payload.end());
                std::lock_guard<std::mutex> lock(m_incomingMutex);
                m_incomingMessages.push(message);
                Printf("Archipelago: Queued text frame (%zu bytes)\n", message.length());
                break;
            }
            
            case WebSocketFrameDecoder::PING: {
                Printf("Archipelago: Received PING, sending PONG\n");
                // Send PONG
                std::vector<uint8_t> pong;
                pong.push_back(0x8A); // FIN + PONG
                pong.push_back(0x80 | frame.payload.size()); // Masked + length
                // Add mask key
                for (int i = 0; i < 4; ++i) pong.push_back(0);
                // Add payload
                pong.insert(pong.end(), frame.payload.begin(), frame.payload.end());
                send(m_socket, (const char*)pong.data(), pong.size(), 0);
                break;
            }
            
            case WebSocketFrameDecoder::CLOSE: {
                Printf("Archipelago: Received close frame\n");
                m_running = false;
                break;
            }
            
            default:
                Printf("Archipelago: Received frame with opcode %d\n", frame.opcode);
                break;
        }
    }
    
    void SendMessage(const std::string& message) {
        if (!m_connected || m_socket == INVALID_SOCKET) {
            Printf("Archipelago: Cannot send - not connected\n");
            return;
        }
        
        auto frame = EncodeWebSocketFrame(message);
        if (send(m_socket, (const char*)frame.data(), frame.size(), 0) == SOCKET_ERROR) {
            Printf("Archipelago: Send failed\n");
        }
    }
    
    std::vector<std::string> GetIncomingMessages() {
        std::vector<std::string> messages;
        std::lock_guard<std::mutex> lock(m_incomingMutex);
        
        while (!m_incomingMessages.empty()) {
            messages.push_back(m_incomingMessages.front());
            m_incomingMessages.pop();
        }
        
        return messages;
    }
};

// Main client implementation
ArchipelagoClient::ArchipelagoClient() 
    : m_impl(std::make_unique<Impl>())
    , m_status(ConnectionStatus::Disconnected)
    , m_port(38281)
    , m_team(0)
    , m_slotId(-1)
    , m_lastReceivedIndex(0) {
    Printf("Archipelago: Simple client created\n");
}

ArchipelagoClient::~ArchipelagoClient() {
    Disconnect();
}

bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_status != ConnectionStatus::Disconnected) {
        Printf("Archipelago: Already connected or connecting\n");
        return false;
    }
    
    m_host = host;
    m_port = port;
    
    m_status = ConnectionStatus::Connecting;
    
    if (m_impl->Connect(host, port)) {
        m_status = ConnectionStatus::Connected;
        // Wait for RoomInfo
        m_connectionTimeout = std::chrono::steady_clock::now() + std::chrono::seconds(10);
        return true;
    } else {
        m_status = ConnectionStatus::Error;
        return false;
    }
}

void ArchipelagoClient::Disconnect() {
    if (m_status == ConnectionStatus::Disconnected) return;
    
    m_impl->Disconnect();
    m_status = ConnectionStatus::Disconnected;
    m_checkedLocations.clear();
}

bool ArchipelagoClient::IsConnected() const {
    return m_impl->m_connected && 
           (m_status == ConnectionStatus::Connected || m_status == ConnectionStatus::InGame);
}

void ArchipelagoClient::ProcessMessages() {
    // Check timeout
    if (m_status == ConnectionStatus::Connecting) {
        auto now = std::chrono::steady_clock::now();
        if (now > m_connectionTimeout) {
            Printf("Archipelago: Connection timeout\n");
            m_status = ConnectionStatus::Error;
            Disconnect();
            return;
        }
    }
    
    // Process incoming messages
    auto messages = m_impl->GetIncomingMessages();
    for (const auto& msg : messages) {
        HandleMessage(msg);
    }
    
    // Send queued messages
    std::lock_guard<std::mutex> lock(m_queueMutex);
    while (!m_outgoingQueue.empty()) {
        m_impl->SendMessage(m_outgoingQueue.front());
        m_outgoingQueue.pop();
    }
}

void ArchipelagoClient::SendPacket(const std::string& json) {
    if (!m_impl->m_connected) {
        Printf("Archipelago: Cannot send - not connected\n");
        return;
    }
    
    std::lock_guard<std::mutex> lock(m_queueMutex);
    m_outgoingQueue.push(json);
}

// Send initial connect packet
void ArchipelagoClient::SendConnectPacket() {
    Printf("Archipelago: Sending Connect packet\n");
    
    // Archipelago expects an array of packets
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "Connect", allocator);
    packet.AddMember("game", "Selaco", allocator);
    packet.AddMember("name", "Player", allocator);
    packet.AddMember("uuid", "selaco-client-001", allocator);
    
    // Version to match server
    rapidjson::Value version(rapidjson::kObjectType);
    version.AddMember("class", "Version", allocator);
    version.AddMember("major", 0, allocator);
    version.AddMember("minor", 5, allocator);
    version.AddMember("build", 0, allocator);
    packet.AddMember("version", version, allocator);
    
    packet.AddMember("items_handling", 7, allocator);
    
    rapidjson::Value tags(rapidjson::kArrayType);
    tags.PushBack("AP", allocator);
    packet.AddMember("tags", tags, allocator);
    
    // Add packet to array
    doc.PushBack(packet, allocator);
    
    // Convert to JSON string
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    std::string message = buffer.GetString();
    Printf("Archipelago: Connect packet JSON: %s\n", message.c_str());
    SendPacket(message);
}

// Authenticate with server
void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
    if (m_status != ConnectionStatus::Connected) {
        Printf("Archipelago: Cannot authenticate - not connected (status: %d)\n", (int)m_status);
        return;
    }
    
    Printf("Archipelago: Authenticating as slot: %s\n", slot.c_str());
    m_slot = slot;
    
    // Archipelago expects an array of packets
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "Connect", allocator);
    
    rapidjson::Value slotValue;
    slotValue.SetString(slot.c_str(), allocator);
    packet.AddMember("name", slotValue, allocator);
    
    packet.AddMember("uuid", "selaco-client-001", allocator);
    packet.AddMember("game", "Selaco", allocator);
    
    // Version for Connect packet
    rapidjson::Value ver(rapidjson::kObjectType);
    ver.AddMember("class", "Version", allocator);
    ver.AddMember("major", 0, allocator);
    ver.AddMember("minor", 5, allocator);
    ver.AddMember("build", 0, allocator);
    packet.AddMember("version", ver, allocator);
    
    packet.AddMember("items_handling", 7, allocator);
    
    rapidjson::Value tags(rapidjson::kArrayType);
    tags.PushBack("AP", allocator);
    packet.AddMember("tags", tags, allocator);
    
    if (!password.empty()) {
        rapidjson::Value passValue;
        passValue.SetString(password.c_str(), allocator);
        packet.AddMember("password", passValue, allocator);
    }
    
    // Add packet to array
    doc.PushBack(packet, allocator);
    
    // Convert to JSON string
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    std::string message = buffer.GetString();
    Printf("Archipelago: Auth packet JSON: %s\n", message.c_str());
    SendPacket(message);
}

// Send location check
void ArchipelagoClient::SendLocationCheck(int locationId) {
    std::vector<int> locations = { locationId };
    SendLocationChecks(locations);
}

// Send multiple location checks
void ArchipelagoClient::SendLocationChecks(const std::vector<int>& locationIds) {
    if (m_status != ConnectionStatus::InGame) {
        Printf("Archipelago: Cannot send location checks - not in game\n");
        return;
    }
    
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
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
    if (m_status != ConnectionStatus::InGame) {
        Printf("Archipelago: Cannot update status - not in game\n");
        return;
    }
    
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
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
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "Bounce", allocator);
    
    rapidjson::Value data(rapidjson::kObjectType);
    data.AddMember("time", 
        std::chrono::system_clock::now().time_since_epoch().count(), allocator);
    packet.AddMember("data", data, allocator);
    
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

// Parse packet
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
            Printf("Archipelago: Received RoomInfo - connection established\n");
            m_status = ConnectionStatus::Connected;
            // Now send the Connect packet
            SendConnectPacket();
            
        } else if (cmd == "Connected") {
            Printf("Archipelago: Slot authentication successful!\n");
            m_status = ConnectionStatus::InGame;
            
            if (packet.HasMember("slot")) {
                m_slotId = packet["slot"].GetInt();
                Printf("  Slot ID: %d\n", m_slotId);
            }
            if (packet.HasMember("team")) {
                m_team = packet["team"].GetInt();
                Printf("  Team: %d\n", m_team);
            }
            if (packet.HasMember("slot_data")) {
                Printf("  Slot data received\n");
            }
            
        } else if (cmd == "ConnectionRefused") {
            Printf("Archipelago: Connection refused!\n");
            if (packet.HasMember("errors") && packet["errors"].IsArray()) {
                for (auto& error : packet["errors"].GetArray()) {
                    if (error.IsString()) {
                        Printf("  Error: %s\n", error.GetString());
                        
                        // Provide helpful messages for common errors
                        if (strcmp(error.GetString(), "InvalidSlot") == 0) {
                            Printf("  The slot name '%s' is not valid for this game.\n", m_slot.c_str());
                            Printf("  Please check the slot name and try again.\n");
                        } else if (strcmp(error.GetString(), "InvalidGame") == 0) {
                            Printf("  The game 'Selaco' is not loaded on the server.\n");
                        }
                    }
                }
            }
            m_status = ConnectionStatus::Error;
            
        } else if (cmd == "ReceivedItems") {
            Printf("Archipelago: Received items\n");
            if (packet.HasMember("index") && packet.HasMember("items")) {
                int index = packet["index"].GetInt();
                const auto& items = packet["items"].GetArray();
                Printf("  Starting at index %d, %d items\n", index, (int)items.Size());
                
                // Process received items
                if (m_itemReceivedCallback) {
                    for (auto& item : items) {
                        if (item.HasMember("item") && item.HasMember("location") && item.HasMember("player")) {
                            m_itemReceivedCallback(
                                item["item"].GetInt(),
                                item["location"].GetInt(),
                                item["player"].GetInt()
                            );
                        }
                    }
                }
            }
            
        } else if (cmd == "Bounced") {
            Printf("Archipelago: Pong received\n");
            if (packet.HasMember("data") && packet["data"].HasMember("time")) {
                auto sentTime = packet["data"]["time"].GetInt64();
                auto now = std::chrono::system_clock::now().time_since_epoch().count();
                auto latency = (now - sentTime) / 1000000; // Convert to milliseconds
                Printf("  Latency: %lld ms\n", latency);
            }
            
        } else if (cmd == "PrintJSON") {
            Printf("Archipelago: Server message:\n");
            if (packet.HasMember("data") && packet["data"].IsArray()) {
                for (auto& part : packet["data"].GetArray()) {
                    if (part.HasMember("text")) {
                        Printf("  %s", part["text"].GetString());
                    }
                }
                Printf("\n");
            }
            
        } else {
            Printf("Archipelago: Received packet type: %s\n", cmd.c_str());
        }
    }
}

// Enable or disable debug logging
void ArchipelagoClient::SetDebugEnabled(bool enabled) {
    // Simple implementation doesn't need special debug mode
}

// Process messages - called from game loop
void AP_Tick() {
    if (g_archipelago) {
        g_archipelago->ProcessMessages();
    }
}

} // namespace Archipelago