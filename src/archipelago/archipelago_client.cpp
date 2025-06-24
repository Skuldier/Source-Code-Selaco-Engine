// archipelago_client.cpp - Final working implementation
// Based on the minimal test that works, with proper message handling added

#include "archipelago_client.h"
#include "../common/engine/printf.h"
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

#include <thread>
#include <atomic>
#include <queue>
#include <mutex>
#include <sstream>
#include <random>
#include <chrono>
#include <cstring>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define CLOSE_SOCKET closesocket
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
    #define CLOSE_SOCKET close
#endif

namespace Archipelago {


// Global instance with diagnostics
ArchipelagoClient* g_archipelago = nullptr;

// Static initialization checker
static struct ArchipelagoInitChecker {
    ArchipelagoInitChecker() {
        Printf("\nARCHIPELAGO: Module static init\n");
        Printf("  g_archipelago at startup: %p\n", (void*)g_archipelago);
    }
    ~ArchipelagoInitChecker() {
        Printf("ARCHIPELAGO: Module static destructor\n");
        Printf("  g_archipelago at shutdown: %p\n", (void*)g_archipelago);
    }
} g_initChecker;


void AP_Init() {
    Printf("\n=====================================\n");
    Printf("ARCHIPELAGO: AP_Init() called\n");
    Printf("  Function address: %p\n", (void*)&AP_Init);
    Printf("  g_archipelago before: %p\n", (void*)g_archipelago);
    Printf("  &g_archipelago: %p\n", (void*)&g_archipelago);
    
    if (!g_archipelago) {
        Printf("ARCHIPELAGO: Creating new client...\n");
        try {
            g_archipelago = new ArchipelagoClient();
            Printf("ARCHIPELAGO: Client created at %p\n", (void*)g_archipelago);
            
            // Verify it's really there
            if (g_archipelago) {
                Printf("ARCHIPELAGO: Verification - client exists\n");
                Printf("ARCHIPELAGO: Client status: %d\n", (int)g_archipelago->GetStatus());
            } else {
                Printf("ARCHIPELAGO: ERROR - Client is null after creation!\n");
            }
        } catch (const std::exception& e) {
            Printf("ARCHIPELAGO: EXCEPTION: %s\n", e.what());
            g_archipelago = nullptr;
        } catch (...) {
            Printf("ARCHIPELAGO: UNKNOWN EXCEPTION\n");
            g_archipelago = nullptr;
        }
    } else {
        Printf("ARCHIPELAGO: Client already exists\n");
    }
    
    Printf("  g_archipelago after: %p\n", (void*)g_archipelago);
    Printf("=====================================\n\n");
}

void AP_Shutdown() {
    if (g_archipelago) {
        delete g_archipelago;
        g_archipelago = nullptr;
        Printf("Archipelago: Client shutdown\n");
    }
}

// Simple base64 encoding
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

// WebSocket frame encoder
std::vector<uint8_t> EncodeWebSocketFrame(const std::string& message) {
    std::vector<uint8_t> frame;
    
    // FIN = 1, Opcode = 1 (text)
    frame.push_back(0x81);
    
    size_t len = message.length();
    
    // Client must mask
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

// WebSocket frame decoder
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
    
    bool DecodeFrame(std::vector<uint8_t>& buffer, Frame& frame) {
        if (buffer.size() < 2) return false;
        
        size_t pos = 0;
        uint8_t byte1 = buffer[pos++];
        uint8_t byte2 = buffer[pos++];
        
        frame.fin = (byte1 & 0x80) != 0;
        frame.opcode = static_cast<OpCode>(byte1 & 0x0F);
        
        bool masked = (byte2 & 0x80) != 0;
        uint64_t payload_len = byte2 & 0x7F;
        
        if (payload_len == 126) {
            if (buffer.size() < pos + 2) return false;
            payload_len = (static_cast<uint64_t>(buffer[pos]) << 8) | buffer[pos + 1];
            pos += 2;
        } else if (payload_len == 127) {
            if (buffer.size() < pos + 8) return false;
            payload_len = 0;
            for (int i = 0; i < 8; ++i) {
                payload_len = (payload_len << 8) | buffer[pos++];
            }
        }
        
        uint8_t mask_key[4] = {0};
        if (masked) {
            if (buffer.size() < pos + 4) return false;
            std::memcpy(mask_key, &buffer[pos], 4);
            pos += 4;
        }
        
        if (buffer.size() < pos + payload_len) return false;
        
        frame.payload.resize(payload_len);
        for (size_t i = 0; i < payload_len; ++i) {
            if (masked) {
                frame.payload[i] = buffer[pos + i] ^ mask_key[i % 4];
            } else {
                frame.payload[i] = buffer[pos + i];
            }
        }
        
        buffer.erase(buffer.begin(), buffer.begin() + pos + payload_len);
        return true;
    }
};

// Private implementation
class ArchipelagoClient::Impl {
public:
    socket_t m_socket{INVALID_SOCKET};
    std::thread m_readThread;
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_connected{false};
    
    std::queue<std::string> m_incomingMessages;
    std::mutex m_incomingMutex;
    
    std::string m_host;
    int m_port;
    std::vector<uint8_t> m_receiveBuffer;
    
    // Track if we've logged the first message
    bool m_firstMessage = true;
    
    Impl() {
        #ifdef _WIN32
        WSADATA wsaData;
        WSAStartup(MAKEWORD(2, 2), &wsaData);
        #endif
    }
    
    ~Impl() {
        Disconnect();
        #ifdef _WIN32
        WSACleanup();
        #endif
    }
    
    bool Connect(const std::string& host, int port) {
        m_host = host;
        m_port = port;
        
        // Create socket
        m_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (m_socket == INVALID_SOCKET) {
            Printf("Archipelago: Failed to create socket\n");
            return false;
        }
        
        // Resolve host
        struct hostent* server = gethostbyname(host.c_str());
        if (!server) {
            Printf("Archipelago: Failed to resolve host\n");
            CLOSE_SOCKET(m_socket);
            return false;
        }
        
        struct sockaddr_in server_addr;
        std::memset(&server_addr, 0, sizeof(server_addr));
        server_addr.sin_family = AF_INET;
        std::memcpy(&server_addr.sin_addr.s_addr, server->h_addr, server->h_length);
        server_addr.sin_port = htons(port);
        
        // Connect
        if (connect(m_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
            Printf("Archipelago: TCP connection failed\n");
            CLOSE_SOCKET(m_socket);
            return false;
        }
        
        // Send WebSocket handshake
        if (!SendWebSocketHandshake()) {
            CLOSE_SOCKET(m_socket);
            return false;
        }
        
        // Start read thread
        m_running = true;
        m_connected = true;
        m_firstMessage = true;
        m_readThread = std::thread(&Impl::ReadThread, this);
        
        return true;
    }
    
    void Disconnect() {
        m_running = false;
        
        if (m_socket != INVALID_SOCKET) {
            // Send close frame
            std::vector<uint8_t> closeFrame;
            closeFrame.push_back(0x88); // FIN + CLOSE
            closeFrame.push_back(0x80); // Masked + 0 length
            closeFrame.resize(6, 0); // Add 4 zero mask bytes
            
            send(m_socket, (const char*)closeFrame.data(), closeFrame.size(), 0);
            
            CLOSE_SOCKET(m_socket);
            m_socket = INVALID_SOCKET;
        }
        
        if (m_readThread.joinable()) {
            m_readThread.join();
        }
        
        m_connected = false;
        m_receiveBuffer.clear();
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
        
        if (send(m_socket, request.c_str(), request.length(), 0) == SOCKET_ERROR) {
            Printf("Archipelago: Failed to send handshake\n");
            return false;
        }
        
        // Read response
        std::string response;
        char buffer[1024];
        
        while (response.find("\r\n\r\n") == std::string::npos) {
            int received = recv(m_socket, buffer, sizeof(buffer) - 1, 0);
            if (received <= 0) {
                Printf("Archipelago: Failed to receive handshake response\n");
                return false;
            }
            buffer[received] = '\0';
            response += buffer;
        }
        
        if (response.find("HTTP/1.1 101") == std::string::npos) {
            Printf("Archipelago: Invalid handshake response\n");
            return false;
        }
        
        // Check for initial data
        size_t header_end = response.find("\r\n\r\n") + 4;
        if (header_end < response.length()) {
            m_receiveBuffer.insert(m_receiveBuffer.end(), 
                                 response.begin() + header_end, 
                                 response.end());
        }
        
        return true;
    }
    
    void ReadThread() {
        WebSocketFrameDecoder decoder;
        char buffer[4096];
        
        while (m_running && m_socket != INVALID_SOCKET) {
            int received = recv(m_socket, buffer, sizeof(buffer), 0);
            
            if (received > 0) {
                m_receiveBuffer.insert(m_receiveBuffer.end(), buffer, buffer + received);
                
                // Decode frames
                while (!m_receiveBuffer.empty()) {
                    WebSocketFrameDecoder::Frame frame;
                    if (decoder.DecodeFrame(m_receiveBuffer, frame)) {
                        HandleFrame(frame);
                    } else {
                        break;
                    }
                }
            } else if (received == 0) {
                Printf("Archipelago: Connection closed by server\n");
                break;
            } else {
                // Socket error - only log if it's not a would-block error
                #ifdef _WIN32
                int error = WSAGetLastError();
                if (error != WSAEWOULDBLOCK) {
                    break;
                }
                #else
                if (errno != EAGAIN && errno != EWOULDBLOCK) {
                    break;
                }
                #endif
                
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        }
        
        m_connected = false;
    }
    
    void HandleFrame(const WebSocketFrameDecoder::Frame& frame) {
        switch (frame.opcode) {
            case WebSocketFrameDecoder::TEXT: {
                std::string message(frame.payload.begin(), frame.payload.end());
                std::lock_guard<std::mutex> lock(m_incomingMutex);
                m_incomingMessages.push(message);
                
                // Only log the first message
                if (m_firstMessage) {
                    Printf("Archipelago: Received first server message\n");
                    m_firstMessage = false;
                }
                break;
            }
            
            case WebSocketFrameDecoder::PING: {
                // Send PONG
                std::vector<uint8_t> pong;
                pong.push_back(0x8A); // FIN + PONG
                
                size_t len = frame.payload.size();
                if (len <= 125) {
                    pong.push_back(0x80 | len);
                } else if (len <= 65535) {
                    pong.push_back(0x80 | 126);
                    pong.push_back((len >> 8) & 0xFF);
                    pong.push_back(len & 0xFF);
                }
                
                // Add mask key (zeros)
                for (int i = 0; i < 4; ++i) pong.push_back(0);
                // Add payload
                pong.insert(pong.end(), frame.payload.begin(), frame.payload.end());
                
                send(m_socket, (const char*)pong.data(), pong.size(), 0);
                break;
            }
            
            case WebSocketFrameDecoder::CLOSE: {
                Printf("Archipelago: Server sent close frame\n");
                m_running = false;
                break;
            }
            
            default:
                break;
        }
    }
    
    void SendMessage(const std::string& message) {
        if (!m_connected || m_socket == INVALID_SOCKET) {
            return;
        }
        
        auto frame = EncodeWebSocketFrame(message);
        send(m_socket, (const char*)frame.data(), frame.size(), 0);
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
    : m_impl(std::make_unique<Impl>()),
      m_status(ConnectionStatus::Disconnected),
      m_port(38281),
      m_slotId(-1),
      m_team(0),
      m_lastReceivedIndex(0)
{
}

ArchipelagoClient::~ArchipelagoClient() {
    Printf("ARCHIPELAGO: Destructor called for client at %p\n", (void*)this);
    Disconnect();
}

bool ArchipelagoClient::Connect(const std::string& host, int port) {
    if (m_status != ConnectionStatus::Disconnected) {
        return false;
    }
    
    m_host = host;
    m_port = port;
    
    m_status = ConnectionStatus::Connecting;
    
    if (m_impl->Connect(host, port)) {
        m_status = ConnectionStatus::Connected;
        
        // Send Connect packet
        SendConnectPacket();
        
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
    std::lock_guard<std::mutex> lock(m_queueMutex);
    m_outgoingQueue.push(json);
}

void ArchipelagoClient::SendConnectPacket() {
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "Connect", allocator);
    packet.AddMember("game", "Selaco", allocator);
    packet.AddMember("name", "Player", allocator);
    packet.AddMember("uuid", "selaco-client-001", allocator);
    
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
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::HandleMessage(const std::string& message) {
    if (message.empty()) return;
    
    if (m_messageCallback) {
        try {
            m_messageCallback(message);
        } catch (...) {
            // Ignore callback exceptions
        }
    }
    
    ParsePacket(message);
}

void ArchipelagoClient::ParsePacket(const std::string& json) {
    if (json.empty()) return;
    
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    
    if (doc.HasParseError() || !doc.IsArray() || doc.Empty()) {
        return;
    }
    
    for (rapidjson::SizeType i = 0; i < doc.Size(); i++) {
        const rapidjson::Value& packet = doc[i];
        
        if (!packet.IsObject() || !packet.HasMember("cmd") || !packet["cmd"].IsString()) {
            continue;
        }
        
        std::string cmd = packet["cmd"].GetString();
        
        if (cmd == "RoomInfo") {
            Printf("Archipelago: Connected to server\n");
            m_status = ConnectionStatus::Connected;
            
        } else if (cmd == "Connected") {
            Printf("Archipelago: Authenticated successfully\n");
            m_status = ConnectionStatus::InGame;
            
            if (packet.HasMember("slot") && packet["slot"].IsInt()) {
                m_slotId = packet["slot"].GetInt();
            }
            
            // Set slot name from successful auth
            if (packet.HasMember("slot_info") && packet["slot_info"].IsObject()) {
                const auto& slotInfo = packet["slot_info"];
                if (slotInfo.HasMember(std::to_string(m_slotId).c_str())) {
                    const auto& mySlot = slotInfo[std::to_string(m_slotId).c_str()];
                    if (mySlot.HasMember("name") && mySlot["name"].IsString()) {
                        m_slot = mySlot["name"].GetString();
                    }
                }
            }
            
        } else if (cmd == "ConnectionRefused") {
            Printf("Archipelago: Connection refused\n");
            m_status = ConnectionStatus::Error;
            
            if (packet.HasMember("errors") && packet["errors"].IsArray()) {
                const auto& errors = packet["errors"];
                for (rapidjson::SizeType j = 0; j < errors.Size(); j++) {
                    if (errors[j].IsString()) {
                        Printf("  Error: %s\n", errors[j].GetString());
                    }
                }
            }
            
        } else if (cmd == "ReceivedItems") {
            if (packet.HasMember("index") && packet["index"].IsInt()) {
                int index = packet["index"].GetInt();
                Printf("Archipelago: Received items (index %d)\n", index);
            }
            
            if (packet.HasMember("items") && packet["items"].IsArray()) {
                const auto& items = packet["items"];
                for (rapidjson::SizeType j = 0; j < items.Size(); j++) {
                    if (items[j].IsObject()) {
                        int itemId = items[j].HasMember("item") ? items[j]["item"].GetInt() : 0;
                        int locationId = items[j].HasMember("location") ? items[j]["location"].GetInt() : 0;
                        int playerSlot = items[j].HasMember("player") ? items[j]["player"].GetInt() : 0;
                        
                        Printf("  Item %d from location %d (player %d)\n", 
                               itemId, locationId, playerSlot);
                        
                        if (m_itemReceivedCallback) {
                            m_itemReceivedCallback(itemId, locationId, playerSlot);
                        }
                    }
                }
            }
            
        } else if (cmd == "PrintJSON") {
            // Server messages
            if (packet.HasMember("data") && packet["data"].IsArray()) {
                std::stringstream message;
                const auto& data = packet["data"];
                
                for (rapidjson::SizeType j = 0; j < data.Size(); j++) {
                    if (data[j].IsObject() && data[j].HasMember("text")) {
                        message << data[j]["text"].GetString();
                    }
                }
                
                if (!message.str().empty()) {
                    Printf("Server: %s\n", message.str().c_str());
                }
            }
            
        } else if (cmd == "Bounced") {
            // Ping response - silent
        }
    }
}

// Other member functions
void ArchipelagoClient::Authenticate(const std::string& slot, const std::string& password, int version) {
    if (m_status != ConnectionStatus::Connected) {
        Printf("Archipelago: Cannot authenticate - not connected\n");
        return;
    }
    
    m_slot = slot;
    
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "Connect", allocator);
    packet.AddMember("game", "Selaco", allocator);
    
    rapidjson::Value nameVal;
    nameVal.SetString(slot.c_str(), allocator);
    packet.AddMember("name", nameVal, allocator);
    
    packet.AddMember("uuid", "selaco-client-001", allocator);
    
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
        rapidjson::Value passVal;
        passVal.SetString(password.c_str(), allocator);
        packet.AddMember("password", passVal, allocator);
    }
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::SendLocationCheck(int locationId) {
    if (m_status != ConnectionStatus::InGame) {
        return;
    }
    
    std::vector<int> locations;
    locations.push_back(locationId);
    SendLocationChecks(locations);
}

void ArchipelagoClient::SendLocationChecks(const std::vector<int>& locationIds) {
    if (m_status != ConnectionStatus::InGame) {
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
        m_checkedLocations.insert(id);
    }
    packet.AddMember("locations", locations, allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::StatusUpdate(const std::string& status) {
    if (m_status != ConnectionStatus::InGame) {
        return;
    }
    
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "StatusUpdate", allocator);
    
    rapidjson::Value statusVal;
    statusVal.SetString(status.c_str(), allocator);
    packet.AddMember("status", statusVal, allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::SendPing() {
    rapidjson::Document doc;
    doc.SetArray();
    auto& allocator = doc.GetAllocator();
    
    rapidjson::Document packet;
    packet.SetObject();
    
    packet.AddMember("cmd", "Bounce", allocator);
    
    doc.PushBack(packet, allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    doc.Accept(writer);
    
    SendPacket(buffer.GetString());
}

void ArchipelagoClient::SetDebugEnabled(bool enabled) {
    // For future use
}


// Static initialization to verify module is loaded
namespace {
    struct ArchipelagoStartup {
        ArchipelagoStartup() {
            Printf("\n");
            Printf("=====================================\n");
            Printf("Archipelago module loaded\n");
            Printf("Use 'ap_connect <host>' to connect\n");
            Printf("=====================================\n");
            Printf("\n");
        }
    };
    static ArchipelagoStartup g_archipelagoStartup;
}

} // namespace Archipelago