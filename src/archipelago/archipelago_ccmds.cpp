// archipelago_ccmds.cpp
// Console commands for Archipelago integration with enhanced debugging

#include "c_dispatch.h"
#include "../common/engine/printf.h"
#include "archipelago_client.h"
#include <sstream>
#include <thread>
#include <chrono>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
#endif

using namespace Archipelago;

// Connect to Archipelago server (non-blocking)
CCMD(ap_connect)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_connect <host:port> OR ap_connect <host> [port]\n");
        Printf("Examples:\n");
        Printf("  ap_connect archipelago.gg:58697\n");
        Printf("  ap_connect localhost 38281\n");
        Printf("  ap_connect 127.0.0.1 38281\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    // Check current status
    auto status = g_archipelago->GetStatus();
    if (status == ConnectionStatus::Connecting) {
        Printf("Already attempting to connect...\n");
        return;
    } else if (status == ConnectionStatus::Connected || status == ConnectionStatus::InGame) {
        Printf("Already connected! Use ap_disconnect first.\n");
        return;
    }
    
    std::string host;
    int port = 38281;
    
    // Check if first argument contains a colon (host:port format)
    std::string firstArg = argv[1];
    size_t colonPos = firstArg.find(':');
    
    if (colonPos != std::string::npos) {
        // Parse host:port format
        host = firstArg.substr(0, colonPos);
        std::string portStr = firstArg.substr(colonPos + 1);
        port = atoi(portStr.c_str());
        
        if (port <= 0 || port > 65535) {
            Printf("Invalid port number: %s\n", portStr.c_str());
            return;
        }
    } else {
        // Traditional format: host [port]
        host = firstArg;
        
        if (argv.argc() >= 3) {
            port = atoi(argv[2]);
            
            if (port <= 0 || port > 65535) {
                Printf("Invalid port number: %s\n", argv[2]);
                return;
            }
        }
    }
    
    Printf("Archipelago: Starting connection to %s:%d...\n", host.c_str(), port);
    if (g_archipelago->Connect(host, port)) {
        Printf("Archipelago: Connection attempt initiated. Use 'ap_status' to check progress.\n");
    } else {
        Printf("Archipelago: Failed to start connection attempt.\n");
    }
}

// Disconnect from server
CCMD(ap_disconnect)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    g_archipelago->Disconnect();
}

// Authenticate with the server
CCMD(ap_auth)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_auth <slot_name> [password]\n");
        Printf("Example: ap_auth Player1\n");
        return;
    }
    
    if (!g_archipelago || !g_archipelago->IsConnected()) {
        Printf("Not connected to Archipelago server!\n");
        return;
    }
    
    std::string slot = argv[1];
    std::string password = "";
    
    if (argv.argc() >= 3) {
        password = argv[2];
    }
    
    g_archipelago->Authenticate(slot, password);
}

// Send a ping to test connection
CCMD(ap_ping)
{
    if (!g_archipelago || !g_archipelago->IsConnected()) {
        Printf("Not connected to Archipelago server!\n");
        return;
    }
    
    g_archipelago->SendPing();
}

// Check connection status
CCMD(ap_status)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    auto status = g_archipelago->GetStatus();
    switch (status) {
        case ConnectionStatus::Disconnected:
            Printf("Archipelago: Disconnected\n");
            break;
        case ConnectionStatus::Connecting:
            Printf("Archipelago: Connecting... (please wait)\n");
            break;
        case ConnectionStatus::Connected:
            Printf("Archipelago: Connected (not authenticated)\n");
            Printf("Use 'ap_auth <slot_name>' to authenticate\n");
            break;
        case ConnectionStatus::InGame:
            Printf("Archipelago: Connected and authenticated\n");
            break;
        case ConnectionStatus::Error:
            Printf("Archipelago: Error state - use ap_disconnect to reset\n");
            break;
    }
}

// Test location check
CCMD(ap_check)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_check <location_id>\n");
        Printf("Example: ap_check 1001\n");
        return;
    }
    
    if (!g_archipelago || g_archipelago->GetStatus() != ConnectionStatus::InGame) {
        Printf("Not in game! Connect and authenticate first.\n");
        return;
    }
    
    int locationId = atoi(argv[1]);
    g_archipelago->SendLocationCheck(locationId);
    Printf("Sent location check for ID %d\n", locationId);
}

// Update game status
CCMD(ap_setstatus)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_setstatus <READY|PLAYING|GOAL>\n");
        return;
    }
    
    if (!g_archipelago || g_archipelago->GetStatus() != ConnectionStatus::InGame) {
        Printf("Not in game! Connect and authenticate first.\n");
        return;
    }
    
    std::string status = argv[1];
    // Convert to uppercase
    for (char& c : status) {
        c = toupper(c);
    }
    
    if (status != "READY" && status != "PLAYING" && status != "GOAL") {
        Printf("Invalid status. Use READY, PLAYING, or GOAL\n");
        return;
    }
    
    g_archipelago->StatusUpdate(status);
    Printf("Status updated to: %s\n", status.c_str());
}

// Debug message callback
static void DebugMessageCallback(const std::string& message) {
    Printf("AP Debug: %s\n", message.c_str());
}

// Toggle debug messages
CCMD(ap_debug)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    static bool debugEnabled = false;
    debugEnabled = !debugEnabled;
    
    if (debugEnabled) {
        g_archipelago->SetMessageCallback(DebugMessageCallback);
        g_archipelago->SetDebugEnabled(true);
        Printf("Archipelago debug messages enabled\n");
    } else {
        g_archipelago->SetMessageCallback(nullptr);
        g_archipelago->SetDebugEnabled(false);
        Printf("Archipelago debug messages disabled\n");
    }
}

// Test complete connection flow
CCMD(ap_test)
{
    if (argv.argc() < 3) {
        Printf("Usage: ap_test <host:port> <slot_name> [password]\n");
        Printf("Example: ap_test archipelago.gg:58697 Player1\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    // Parse host:port
    std::string hostport = argv[1];
    size_t colonPos = hostport.find(':');
    
    std::string host;
    int port = 38281; // default port
    
    if (colonPos != std::string::npos) {
        host = hostport.substr(0, colonPos);
        port = atoi(hostport.substr(colonPos + 1).c_str());
    } else {
        host = hostport;
    }
    
    std::string slot = argv[2];
    std::string password = (argv.argc() >= 4) ? argv[3] : "";
    
    Printf("=== Archipelago Connection Test ===\n");
    Printf("Server: %s:%d\n", host.c_str(), port);
    Printf("Slot: %s\n", slot.c_str());
    
    // Disconnect if already connected
    if (g_archipelago->GetStatus() != ConnectionStatus::Disconnected) {
        Printf("Disconnecting existing connection...\n");
        g_archipelago->Disconnect();
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }
    
    // Step 1: Connect
    Printf("\n[1/3] Connecting...\n");
    if (!g_archipelago->Connect(host, port)) {
        Printf("ERROR: Failed to initiate connection\n");
        return;
    }
    
    // Wait for connection (with visual feedback)
    int dots = 0;
    for (int i = 0; i < 100; i++) { // 10 seconds timeout
        g_archipelago->ProcessMessages();
        
        auto status = g_archipelago->GetStatus();
        if (status == ConnectionStatus::Connected) {
            Printf("\nSUCCESS: Connected to server!\n");
            break;
        } else if (status == ConnectionStatus::Error) {
            Printf("\nERROR: Connection failed!\n");
            Printf("Possible reasons:\n");
            Printf("- Server is not running\n");
            Printf("- Wrong host/port\n");
            Printf("- Firewall blocking connection\n");
            Printf("- Network issues\n");
            return;
        }
        
        // Visual feedback every 500ms
        if (i % 5 == 0) {
            Printf(".");
            dots++;
            if (dots >= 20) {
                Printf("\n");
                dots = 0;
            }
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    if (g_archipelago->GetStatus() != ConnectionStatus::Connected) {
        Printf("\nERROR: Connection timed out\n");
        g_archipelago->Disconnect();
        return;
    }
    
    // Step 2: Authenticate
    Printf("\n[2/3] Authenticating as '%s'...\n", slot.c_str());
    g_archipelago->Authenticate(slot, password);
    
    // Wait for authentication
    for (int i = 0; i < 50; i++) { // 5 seconds timeout
        g_archipelago->ProcessMessages();
        
        auto status = g_archipelago->GetStatus();
        if (status == ConnectionStatus::InGame) {
            Printf("SUCCESS: Authenticated!\n");
            break;
        } else if (status == ConnectionStatus::Error) {
            Printf("ERROR: Authentication failed!\n");
            Printf("Check your slot name and password.\n");
            g_archipelago->Disconnect();
            return;
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    if (g_archipelago->GetStatus() != ConnectionStatus::InGame) {
        Printf("ERROR: Authentication timed out\n");
        g_archipelago->Disconnect();
        return;
    }
    
    // Step 3: Test communication
    Printf("\n[3/3] Testing communication...\n");
    g_archipelago->SendPing();
    
    // Wait for ping response
    for (int i = 0; i < 30; i++) { // 3 seconds
        g_archipelago->ProcessMessages();
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    Printf("\n=== Test Complete ===\n");
    Printf("Connection is working! You can now:\n");
    Printf("- Send location checks: ap_check <location_id>\n");
    Printf("- Update status: ap_setstatus READY/PLAYING/GOAL\n");
    Printf("- Disconnect: ap_disconnect\n");
}

// Quick connect command - combines connect and auth
CCMD(ap_quick)
{
    if (argv.argc() < 3) {
        Printf("Usage: ap_quick <host:port> <slot_name> [password]\n");
        Printf("Example: ap_quick archipelago.gg:58697 Player1\n");
        Printf("This combines ap_connect and ap_auth into one command.\n");
        return;
    }
    
    // Just call ap_test with the same arguments
    FString command;
    command.Format("ap_test %s %s %s", 
        argv[1], argv[2], 
        (argv.argc() >= 4) ? argv[3] : "");
    C_DoCommand(command.GetChars());
}

// Test basic threading without WebSocket
CCMD(ap_threadtest)
{
    Printf("=== Basic Thread Test ===\n");
    Printf("Testing if threading works without WebSocket...\n");
    
    class TestThread {
    public:
        std::thread m_thread;
        std::atomic<bool> m_running{false};
        std::atomic<int> m_counter{0};
        
        void Start() {
            Printf("Starting test thread...\n");
            m_running = true;
            
            try {
                m_thread = std::thread([this]() {
                    Printf("Test thread started (ID: %d)\n", std::this_thread::get_id());
                    
                    while (m_running && m_counter < 10) {
                        m_counter++;
                        Printf("  Thread tick %d\n", m_counter.load());
                        std::this_thread::sleep_for(std::chrono::milliseconds(200));
                    }
                    
                    Printf("Test thread finished\n");
                });
            } catch (const std::exception& e) {
                Printf("ERROR: Failed to create thread: %s\n", e.what());
            }
        }
        
        void Stop() {
            Printf("Stopping test thread...\n");
            m_running = false;
            if (m_thread.joinable()) {
                m_thread.join();
                Printf("Thread joined successfully\n");
            }
        }
    };
    
    TestThread test;
    test.Start();
    
    // Wait for it to complete
    std::this_thread::sleep_for(std::chrono::seconds(3));
    
    test.Stop();
    
    Printf("\n=== Thread Test Results ===\n");
    if (test.m_counter >= 10) {
        Printf("SUCCESS: Basic threading works correctly\n");
        Printf("The issue is likely with WebSocketPP, not threading\n");
    } else {
        Printf("ERROR: Thread didn't complete (%d/10 ticks)\n", test.m_counter.load());
        Printf("There's a fundamental threading issue\n");
    }
}

// Test basic socket functionality
CCMD(ap_socktest)
{
    Printf("=== Basic Socket Test ===\n");
    
    #ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        Printf("WSAStartup failed\n");
        return;
    }
    #endif
    
    // Create a socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        Printf("Failed to create socket\n");
        #ifdef _WIN32
        WSACleanup();
        #endif
        return;
    }
    Printf("Socket created successfully\n");
    
    // Set timeout
    #ifdef _WIN32
    DWORD timeout = 1000; // 1 second
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout));
    #else
    struct timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    #endif
    
    // Try a simple recv (will timeout since not connected)
    char buffer[1024];
    int result = recv(sock, buffer, sizeof(buffer), 0);
    Printf("Recv returned: %d\n", result);
    
    #ifdef _WIN32
    if (result == SOCKET_ERROR) {
        Printf("Socket error: %d\n", WSAGetLastError());
    }
    closesocket(sock);
    WSACleanup();
    #else
    if (result < 0) {
        Printf("Socket error: %d\n", errno);
    }
    close(sock);
    #endif
    
    Printf("Socket test completed without crash\n");
}

// Test minimal socket connection
CCMD(ap_sockconnect)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_sockconnect <host> [port]\n");
        Printf("Example: ap_sockconnect localhost 38281\n");
        return;
    }
    
    std::string host = argv[1];
    int port = 38281;
    if (argv.argc() >= 3) {
        port = atoi(argv[2]);
    }
    
    Printf("=== Socket Connection Test ===\n");
    Printf("Testing connection to %s:%d\n", host.c_str(), port);
    
    #ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
    #endif
    
    // Create socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        Printf("Failed to create socket\n");
        #ifdef _WIN32
        WSACleanup();
        #endif
        return;
    }
    
    // Resolve host
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    
    // Try to parse as IP first
    #ifdef _WIN32
        // Use inet_addr for Windows compatibility
        unsigned long addr = inet_addr(host.c_str());
        if (addr != INADDR_NONE) {
            server_addr.sin_addr.s_addr = addr;
        } else {
            // Not an IP, try hostname resolution
            struct hostent* he = gethostbyname(host.c_str());
            if (he == nullptr) {
                Printf("Failed to resolve hostname\n");
                closesocket(sock);
                WSACleanup();
                return;
            }
            memcpy(&server_addr.sin_addr, he->h_addr_list[0], he->h_length);
        }
    #else
        if (inet_pton(AF_INET, host.c_str(), &server_addr.sin_addr) != 1) {
            // Not an IP, try hostname resolution
            struct hostent* he = gethostbyname(host.c_str());
            if (he == nullptr) {
                Printf("Failed to resolve hostname\n");
                close(sock);
                return;
            }
            memcpy(&server_addr.sin_addr, he->h_addr_list[0], he->h_length);
        }
    #endif
    
    // Try to connect
    Printf("Attempting connection...\n");
    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        #ifdef _WIN32
        Printf("Connection failed: %d\n", WSAGetLastError());
        closesocket(sock);
        WSACleanup();
        #else
        Printf("Connection failed: %d\n", errno);
        close(sock);
        #endif
        return;
    }
    
    Printf("SUCCESS: Connected to %s:%d\n", host.c_str(), port);
    
    // Try to receive some data
    char buffer[256];
    int received = recv(sock, buffer, sizeof(buffer) - 1, 0);
    if (received > 0) {
        buffer[received] = '\0';
        Printf("Received %d bytes\n", received);
    }
    
    #ifdef _WIN32
    closesocket(sock);
    WSACleanup();
    #else
    close(sock);
    #endif
    
    Printf("Socket connection test completed\n");
}

// Force crash for testing
CCMD(ap_crash)
{
    Printf("WARNING: This will intentionally crash for testing!\n");
    Printf("Crashing in 3...\n");
    std::this_thread::sleep_for(std::chrono::seconds(1));
    Printf("2...\n");
    std::this_thread::sleep_for(std::chrono::seconds(1));
    Printf("1...\n");
    std::this_thread::sleep_for(std::chrono::seconds(1));
    
    // Intentional null pointer dereference
    int* p = nullptr;
    *p = 42;
}

// Process messages - called from game loop
void AP_Tick() {
    if (g_archipelago) {
        g_archipelago->ProcessMessages();
    }
}