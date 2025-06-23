// Simplified easywsclient implementation for Archipelago
// This is a minimal WebSocket client implementation

#include "easywsclient.hpp"

#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define INVALID_SOCKET_VALUE INVALID_SOCKET
    #define SOCKET_ERROR_VALUE SOCKET_ERROR
    #define socketerrno WSAGetLastError()
    #define SOCKET_EAGAIN_EINPROGRESS WSAEINPROGRESS
    #define SOCKET_EWOULDBLOCK WSAEWOULDBLOCK
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netinet/tcp.h>
    #include <netdb.h>
    #include <unistd.h>
    #include <fcntl.h>
    #include <errno.h>
    typedef int socket_t;
    #define INVALID_SOCKET_VALUE -1
    #define SOCKET_ERROR_VALUE -1
    #define closesocket(s) close(s)
    #define socketerrno errno
    #define SOCKET_EAGAIN_EINPROGRESS EINPROGRESS
    #define SOCKET_EWOULDBLOCK EWOULDBLOCK
#endif

#include <vector>
#include <string>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <algorithm>

namespace {

bool globalWSAStartup = false;

// Base64 encoding for WebSocket handshake
std::string base64_encode(const std::string& input) {
    static const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    result.reserve(((input.size() + 2) / 3) * 4);
    
    for (size_t i = 0; i < input.size(); i += 3) {
        int b = (input[i] & 0xFC) >> 2;
        result.push_back(chars[b]);
        b = (input[i] & 0x03) << 4;
        if (i + 1 < input.size()) {
            b |= (input[i + 1] & 0xF0) >> 4;
            result.push_back(chars[b]);
            b = (input[i + 1] & 0x0F) << 2;
            if (i + 2 < input.size()) {
                b |= (input[i + 2] & 0xC0) >> 6;
                result.push_back(chars[b]);
                b = input[i + 2] & 0x3F;
                result.push_back(chars[b]);
            } else {
                result.push_back(chars[b]);
                result.push_back('=');
            }
        } else {
            result.push_back(chars[b]);
            result.push_back('=');
            result.push_back('=');
        }
    }
    
    return result;
}

// Simple WebSocket implementation
class WebSocketImpl : public easywsclient::WebSocket {
public:
    WebSocketImpl(socket_t sockfd, bool useMask) 
        : sockfd(sockfd), readyState(OPEN), useMask(useMask), isRxBad(false) {
    }
    
    virtual ~WebSocketImpl() {
        if (readyState != CLOSED) {
            close();
        }
    }
    
    readyStateValues getReadyState() const { 
        return readyState; 
    }
    
    void poll(int timeout) {
        if (readyState == CLOSED) {
            return;
        }
        
        if (timeout > 0) {
            fd_set rfds;
            FD_ZERO(&rfds);
            FD_SET(sockfd, &rfds);
            
            struct timeval tv;
            tv.tv_sec = timeout / 1000;
            tv.tv_usec = (timeout % 1000) * 1000;
            
            select(sockfd + 1, &rfds, NULL, NULL, &tv);
        }
        
        while (true) {
            // Try to receive some data
            size_t oldSize = rxbuf.size();
            rxbuf.resize(oldSize + 1500);
            
            int ret = recv(sockfd, (char*)&rxbuf[oldSize], 1500, 0);
            if (ret < 0 && (socketerrno == SOCKET_EWOULDBLOCK || socketerrno == SOCKET_EAGAIN_EINPROGRESS)) {
                rxbuf.resize(oldSize);
                break;
            } else if (ret <= 0) {
                rxbuf.resize(oldSize);
                closesocket(sockfd);
                readyState = CLOSED;
                break;
            } else {
                rxbuf.resize(oldSize + ret);
            }
        }
        
        // Process received data
        while (rxbuf.size() >= 2) {
            bool fin = (rxbuf[0] & 0x80) == 0x80;
            int opcode = rxbuf[0] & 0x0F;
            bool mask = (rxbuf[1] & 0x80) == 0x80;
            size_t payloadLength = rxbuf[1] & 0x7F;
            size_t pos = 2;
            
            if (payloadLength == 126) {
                if (rxbuf.size() < 4) break;
                payloadLength = (rxbuf[2] << 8) | rxbuf[3];
                pos = 4;
            } else if (payloadLength == 127) {
                if (rxbuf.size() < 10) break;
                payloadLength = 0;
                for (int i = 0; i < 8; i++) {
                    payloadLength = (payloadLength << 8) | rxbuf[2 + i];
                }
                pos = 10;
            }
            
            if (mask) pos += 4;
            if (rxbuf.size() < pos + payloadLength) break;
            
            std::vector<uint8_t> payload;
            payload.reserve(payloadLength);
            
            if (mask) {
                uint8_t maskKey[4] = { rxbuf[pos-4], rxbuf[pos-3], rxbuf[pos-2], rxbuf[pos-1] };
                for (size_t i = 0; i < payloadLength; i++) {
                    payload.push_back(rxbuf[pos + i] ^ maskKey[i % 4]);
                }
            } else {
                payload.insert(payload.end(), rxbuf.begin() + pos, rxbuf.begin() + pos + payloadLength);
            }
            
            rxbuf.erase(rxbuf.begin(), rxbuf.begin() + pos + payloadLength);
            
            if (opcode == 1) { // Text frame
                receivedMessages.push_back(std::string(payload.begin(), payload.end()));
            } else if (opcode == 8) { // Close frame
                close();
            } else if (opcode == 9) { // Ping frame
                // Send pong
                std::vector<uint8_t> pong;
                pong.push_back(0x8A); // FIN + Pong opcode
                if (payload.size() <= 125) {
                    pong.push_back(payload.size());
                } else if (payload.size() <= 65535) {
                    pong.push_back(126);
                    pong.push_back((payload.size() >> 8) & 0xFF);
                    pong.push_back(payload.size() & 0xFF);
                }
                pong.insert(pong.end(), payload.begin(), payload.end());
                ::send(sockfd, (char*)pong.data(), pong.size(), 0);
            }
        }
    }
    
    void dispatch(MessageCallback callback) {
        for (const std::string& message : receivedMessages) {
            callback(message);
        }
        receivedMessages.clear();
    }
    
    void send(const std::string& message) {
        sendData(1, message);
    }
    
    void sendBinary(const std::string& message) {
        sendData(2, message);
    }
    
    void sendBinary(const std::vector<uint8_t>& message) {
        sendData(2, std::string(message.begin(), message.end()));
    }
    
    void sendPing() {
        std::string empty;
        sendData(9, empty);
    }
    
    void close() {
        if (readyState == CLOSING || readyState == CLOSED) {
            return;
        }
        
        readyState = CLOSING;
        uint8_t closeFrame[6] = { 0x88, 0x80, 0x00, 0x00, 0x00, 0x00 };
        std::vector<uint8_t> header(closeFrame, closeFrame + 6);
        txbuf.insert(txbuf.end(), header.begin(), header.end());
        
        // Send any remaining data
        while (txbuf.size()) {
            int ret = ::send(sockfd, (char*)txbuf.data(), txbuf.size(), 0);
            if (ret > 0) {
                txbuf.erase(txbuf.begin(), txbuf.begin() + ret);
            } else {
                break;
            }
        }
        
        closesocket(sockfd);
        readyState = CLOSED;
    }
    
private:
    void sendData(int opcode, const std::string& data) {
        if (readyState != OPEN) return;
        
        std::vector<uint8_t> header;
        header.push_back(0x80 | opcode); // FIN + opcode
        
        if (data.size() <= 125) {
            header.push_back((useMask ? 0x80 : 0) | data.size());
        } else if (data.size() <= 65535) {
            header.push_back((useMask ? 0x80 : 0) | 126);
            header.push_back((data.size() >> 8) & 0xFF);
            header.push_back(data.size() & 0xFF);
        } else {
            header.push_back((useMask ? 0x80 : 0) | 127);
            for (int i = 7; i >= 0; i--) {
                header.push_back((data.size() >> (8 * i)) & 0xFF);
            }
        }
        
        if (useMask) {
            uint8_t maskKey[4] = { (uint8_t)rand(), (uint8_t)rand(), (uint8_t)rand(), (uint8_t)rand() };
            header.insert(header.end(), maskKey, maskKey + 4);
            
            for (size_t i = 0; i < data.size(); i++) {
                header.push_back(data[i] ^ maskKey[i % 4]);
            }
        } else {
            header.insert(header.end(), data.begin(), data.end());
        }
        
        txbuf.insert(txbuf.end(), header.begin(), header.end());
        
        // Try to send immediately
        while (txbuf.size()) {
            int ret = ::send(sockfd, (char*)txbuf.data(), txbuf.size(), 0);
            if (ret > 0) {
                txbuf.erase(txbuf.begin(), txbuf.begin() + ret);
            } else {
                break;
            }
        }
    }
    
    socket_t sockfd;
    readyStateValues readyState;
    bool useMask;
    bool isRxBad;
    std::vector<uint8_t> rxbuf;
    std::vector<uint8_t> txbuf;
    std::vector<std::string> receivedMessages;
};

} // namespace

namespace easywsclient {

WebSocket* WebSocket::from_url(const std::string& url, const std::string& origin) {
    // Initialize Winsock on Windows
#ifdef _WIN32
    if (!globalWSAStartup) {
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            return NULL;
        }
        globalWSAStartup = true;
    }
#endif
    
    // Parse URL
    std::string host;
    int port = 80;
    std::string path = "/";
    
    if (url.substr(0, 5) == "ws://") {
        size_t hostStart = 5;
        size_t hostEnd = url.find('/', hostStart);
        if (hostEnd == std::string::npos) {
            hostEnd = url.length();
        }
        
        size_t portStart = url.find(':', hostStart);
        if (portStart != std::string::npos && portStart < hostEnd) {
            host = url.substr(hostStart, portStart - hostStart);
            port = atoi(url.substr(portStart + 1, hostEnd - portStart - 1).c_str());
        } else {
            host = url.substr(hostStart, hostEnd - hostStart);
        }
        
        if (hostEnd < url.length()) {
            path = url.substr(hostEnd);
        }
    } else {
        return NULL;
    }
    
    // Resolve host
    struct addrinfo hints, *result;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    
    char portStr[16];
    snprintf(portStr, sizeof(portStr), "%d", port);
    
    if (getaddrinfo(host.c_str(), portStr, &hints, &result) != 0) {
        return NULL;
    }
    
    // Create socket
    socket_t sockfd = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (sockfd == INVALID_SOCKET_VALUE) {
        freeaddrinfo(result);
        return NULL;
    }
    
    // Set non-blocking mode
#ifdef _WIN32
    u_long mode = 1;
    ioctlsocket(sockfd, FIONBIO, &mode);
#else
    fcntl(sockfd, F_SETFL, O_NONBLOCK);
#endif
    
    // Connect
    if (connect(sockfd, result->ai_addr, result->ai_addrlen) == SOCKET_ERROR_VALUE) {
        if (socketerrno != SOCKET_EAGAIN_EINPROGRESS && socketerrno != SOCKET_EWOULDBLOCK) {
            closesocket(sockfd);
            freeaddrinfo(result);
            return NULL;
        }
    }
    
    freeaddrinfo(result);
    
    // Wait for connection
    fd_set wfds;
    FD_ZERO(&wfds);
    FD_SET(sockfd, &wfds);
    
    struct timeval tv;
    tv.tv_sec = 5; // 5 second timeout
    tv.tv_usec = 0;
    
    if (select(sockfd + 1, NULL, &wfds, NULL, &tv) <= 0) {
        closesocket(sockfd);
        return NULL;
    }
    
    // Send WebSocket handshake
    std::string key = base64_encode("archipelagokey12");
    
    std::stringstream handshake;
    handshake << "GET " << path << " HTTP/1.1\r\n";
    handshake << "Host: " << host << "\r\n";
    handshake << "Upgrade: websocket\r\n";
    handshake << "Connection: Upgrade\r\n";
    handshake << "Sec-WebSocket-Key: " << key << "\r\n";
    handshake << "Sec-WebSocket-Version: 13\r\n";
    if (!origin.empty()) {
        handshake << "Origin: " << origin << "\r\n";
    }
    handshake << "\r\n";
    
    if (::send(sockfd, handshake.str().c_str(), handshake.str().length(), 0) == SOCKET_ERROR_VALUE) {
        closesocket(sockfd);
        return NULL;
    }
    
    // Read handshake response
    std::string response;
    char buffer[1024];
    while (response.find("\r\n\r\n") == std::string::npos) {
        int ret = recv(sockfd, buffer, sizeof(buffer) - 1, 0);
        if (ret <= 0) {
            closesocket(sockfd);
            return NULL;
        }
        buffer[ret] = 0;
        response += buffer;
    }
    
    // Check response
    if (response.find("HTTP/1.1 101") != 0) {
        closesocket(sockfd);
        return NULL;
    }
    
    return new WebSocketImpl(sockfd, true);
}

} // namespace easywsclient