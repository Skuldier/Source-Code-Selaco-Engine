// archipelago_commands.cpp - Console commands for Archipelago
#include "archipelago_protocol.h"
#include "c_dispatch.h"
#include "../common/engine/printf.h"
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
    
    if (g_archipelago->getState() != APState::Disconnected) {
        Printf("Already connected or connecting! Use ap_disconnect first.\n");
        return;
    }
    
    if (g_archipelago->connect(host, port)) {
        Printf("Archipelago: Connection initiated to %s:%d\n", host.c_str(), port);
    } else {
        Printf("Archipelago: Failed to initiate connection\n");
    }
}

// Disconnect from server
CCMD(ap_disconnect)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    if (g_archipelago->getState() == APState::Disconnected) {
        Printf("Not connected!\n");
        return;
    }
    
    g_archipelago->disconnect();
    Printf("Disconnected from Archipelago server.\n");
}

// Authenticate with slot name
CCMD(ap_auth)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_auth <slot_name> [password]\n");
        Printf("Example: ap_auth Player1\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    if (g_archipelago->getState() != APState::Connected) {
        Printf("Not connected to server! Use ap_connect first.\n");
        return;
    }
    
    std::string slotName = argv[1];
    std::string password = "";
    
    if (argv.argc() >= 3) {
        password = argv[2];
    }
    
    g_archipelago->authenticate(slotName, password);
    Printf("Archipelago: Authenticating as '%s'\n", slotName.c_str());
}

// Check status
CCMD(ap_status)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    const char* stateStr = "Unknown";
    switch (g_archipelago->getState()) {
        case APState::Disconnected:
            stateStr = "Disconnected";
            break;
        case APState::Connecting:
            stateStr = "Connecting";
            break;
        case APState::Connected:
            stateStr = "Connected (not authenticated)";
            break;
        case APState::Authenticated:
            stateStr = "Authenticated";
            break;
        case APState::Error:
            stateStr = "Error";
            break;
    }
    
    Printf("Archipelago Status:\n");
    Printf("  State: %s\n", stateStr);
    
    if (g_archipelago->getState() == APState::Authenticated) {
        Printf("  Slot Name: %s\n", g_archipelago->getSlotName().c_str());
        Printf("  Slot Number: %d\n", g_archipelago->getSlotNumber());
    }
}

// Send a location check
CCMD(ap_check)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_check <location_id>\n");
        Printf("Example: ap_check 12345\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    if (g_archipelago->getState() != APState::Authenticated) {
        Printf("Not authenticated! Connect and authenticate first.\n");
        return;
    }
    
    int64_t locationId = atoll(argv[1]);
    g_archipelago->sendLocationCheck(locationId);
    Printf("Sent location check for ID %lld\n", locationId);
}

// Send chat message
CCMD(ap_say)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_say <message>\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    if (g_archipelago->getState() != APState::Authenticated) {
        Printf("Not authenticated! Connect and authenticate first.\n");
        return;
    }
    
    // Concatenate all arguments into message
    std::stringstream message;
    for (int i = 1; i < argv.argc(); i++) {
        if (i > 1) message << " ";
        message << argv[i];
    }
    
    g_archipelago->sendChat(message.str());
}

// Quick connect with authentication
CCMD(ap_quick)
{
    if (argv.argc() < 3) {
        Printf("Usage: ap_quick <host> <slot_name> [password]\n");
        Printf("Example: ap_quick localhost Player1\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    if (g_archipelago->getState() != APState::Disconnected) {
        Printf("Already connected! Use ap_disconnect first.\n");
        return;
    }
    
    std::string host = argv[1];
    std::string slotName = argv[2];
    std::string password = "";
    
    if (argv.argc() >= 4) {
        password = argv[3];
    }
    
    // Extract port if specified as host:port
    int port = 38281;
    size_t colonPos = host.find(':');
    if (colonPos != std::string::npos) {
        port = atoi(host.substr(colonPos + 1).c_str());
        host = host.substr(0, colonPos);
    }
    
    // Set authentication info before connecting
    g_archipelago->authenticate(slotName, password);
    
    if (g_archipelago->connect(host, port)) {
        Printf("Archipelago: Quick connect to %s:%d as '%s'\n", 
               host.c_str(), port, slotName.c_str());
    } else {
        Printf("Archipelago: Failed to initiate connection\n");
    }
}

// Debug command to test item callback
CCMD(ap_test_item)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    Printf("Testing item received callback...\n");
    
    // This would normally be called by the game when setting up the callback
    g_archipelago->setItemReceivedCallback([](int64_t itemId, int64_t locationId, int playerSlot) {
        Printf("TEST: Item received! ID=%lld, Location=%lld, Player=%d\n", 
               itemId, locationId, playerSlot);
    });
    
    Printf("Item callback set. Items will be logged when received.\n");
}