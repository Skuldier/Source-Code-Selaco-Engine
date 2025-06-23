// Console commands for Archipelago integration

#include "c_dispatch.h"
#include "c_console.h"
#include "archipelago_client.h"
#include <sstream>

using namespace Archipelago;

// Connect to Archipelago server
CCMD(ap_connect)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_connect <host> [port]\n");
        Printf("Example: ap_connect localhost 38281\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    std::string host = argv[1];
    int port = 38281;
    
    if (argv.argc() >= 3) {
        port = atoi(argv[2]);
    }
    
    if (g_archipelago->IsConnected()) {
        Printf("Already connected! Use ap_disconnect first.\n");
        return;
    }
    
    if (g_archipelago->Connect(host, port)) {
        Printf("Connected to Archipelago server at %s:%d\n", host.c_str(), port);
    } else {
        Printf("Failed to connect to %s:%d\n", host.c_str(), port);
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

// Show connection status
CCMD(ap_status)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    const char* statusStr = "Unknown";
    switch (g_archipelago->GetStatus()) {
        case ConnectionStatus::Disconnected:
            statusStr = "Disconnected";
            break;
        case ConnectionStatus::Connecting:
            statusStr = "Connecting";
            break;
        case ConnectionStatus::Connected:
            statusStr = "Connected (not authenticated)";
            break;
        case ConnectionStatus::InGame:
            statusStr = "In Game";
            break;
        case ConnectionStatus::Error:
            statusStr = "Error";
            break;
    }
    
    Printf("Archipelago Status: %s\n", statusStr);
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
        Printf("Archipelago debug messages enabled\n");
    } else {
        g_archipelago->SetMessageCallback(nullptr);
        Printf("Archipelago debug messages disabled\n");
    }
}