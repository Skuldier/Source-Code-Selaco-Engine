// archipelago_ccmds.cpp - Clean version with reduced spam
// This version only logs important events

#include "c_dispatch.h"
#include "../common/engine/printf.h"
#include "archipelago_client.h"
#include <sstream>

using namespace Archipelago;



// Failsafe initialization
static void EnsureInit() {
    if (!g_archipelago) {
        Printf("\nARCHIPELAGO: Emergency init required!\n");
        Printf("  &g_archipelago = %p\n", (void*)&g_archipelago);
        Printf("  g_archipelago = %p\n", (void*)g_archipelago);
        AP_Init();
        if (!g_archipelago) {
            Printf("ARCHIPELAGO: Emergency init FAILED!\n");
        } else {
            Printf("ARCHIPELAGO: Emergency init succeeded\n");
        }
    }
}

// Emergency initialization function
static void EnsureArchipelagoInit() {
    if (!g_archipelago) {
        Printf("Warning: Archipelago not initialized, performing emergency init\n");
        AP_Init();
        if (!g_archipelago) {
            Printf("FATAL: Emergency init failed!\n");
        }
    }
}

// Connect to Archipelago server
CCMD(ap_connect)
{
    Printf("\n=== AP_CONNECT START ===\n");
    Printf("g_archipelago pointer: %p\n", (void*)g_archipelago);
    Printf("&g_archipelago address: %p\n", (void*)&g_archipelago);
    
    EnsureInit();
    
    if (argv.argc() < 2) {
        Printf("Usage: ap_connect <host> [port]\n");
        Printf("Example: ap_connect localhost 38281\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("FATAL: Still no client after EnsureInit!\n");
        return;
    }
    
    Printf("Client exists at %p, proceeding...\n", (void*)g_archipelago);
    
    std::string host = argv[1];
    int port = 38281;
    
    if (argv.argc() >= 3) {
        port = atoi(argv[2]);
    }
    
    if (g_archipelago->IsConnected()) {
        Printf("Already connected! Use ap_disconnect first.\n");
        return;
    }
    
    Printf("Archipelago: Connecting to %s:%d...\n", host.c_str(), port);
    
    try {
        if (g_archipelago->Connect(host, port)) {
            Printf("Archipelago: Connection successful!\n");
            Printf("Archipelago: Waiting for server response...\n");
        } else {
            Printf("Archipelago: Connection failed!\n");
        }
    } catch (const std::exception& e) {
        Printf("EXCEPTION during connect: %s\n", e.what());
    } catch (...) {
        Printf("UNKNOWN EXCEPTION during connect\n");
    }
    
    Printf("=== AP_CONNECT END ===\n\n");
}

// Disconnect from server
CCMD(ap_disconnect)
{
    EnsureInit();
    
    EnsureArchipelagoInit();
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    if (!g_archipelago->IsConnected()) {
        Printf("Not connected!\n");
        return;
    }
    
    g_archipelago->Disconnect();
    Printf("Disconnected from Archipelago server.\n");
}

// Status check
CCMD(ap_status)
{
    EnsureInit();
    
    EnsureArchipelagoInit();
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\n");
        return;
    }
    
    Printf("Archipelago Status:\n");
    Printf("  Connected: %s\n", g_archipelago->IsConnected() ? "Yes" : "No");
    Printf("  Status: %d\n", (int)g_archipelago->GetStatus());
    
    if (g_archipelago->IsConnected()) {
        Printf("  Host: %s:%d\n", 
               g_archipelago->GetHost().c_str(), 
               g_archipelago->GetPort());
        Printf("  Slot: %s (ID: %d)\n",
               g_archipelago->GetSlot().c_str(),
               g_archipelago->GetSlotId());
    }
}

// Send ping
CCMD(ap_ping)
{
    EnsureInit();
    
    EnsureArchipelagoInit();
    
    if (!g_archipelago || !g_archipelago->IsConnected()) {
        Printf("Not connected to Archipelago server!\n");
        return;
    }
    
    g_archipelago->SendPing();
    Printf("Ping sent.\n");
}

// Authenticate
CCMD(ap_auth)
{
    EnsureInit();
    
    EnsureArchipelagoInit();
    
    if (argv.argc() < 2) {
        Printf("Usage: ap_auth <slot_name> [password]\n");
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
    Printf("Authentication request sent for slot: %s\n", slot.c_str());
}

// Check locations
CCMD(ap_check)
{
    EnsureInit();
    
    EnsureArchipelagoInit();
    
    if (argv.argc() < 2) {
        Printf("Usage: ap_check <location_id>\n");
        return;
    }
    
    if (!g_archipelago || g_archipelago->GetStatus() != ConnectionStatus::InGame) {
        Printf("Not in game! Authenticate first with ap_auth\n");
        return;
    }
    
    int locationId = atoi(argv[1]);
    g_archipelago->SendLocationCheck(locationId);
    Printf("Sent location check for ID: %d\n", locationId);
}

// This function is called every frame by the engine
void AP_Tick() {
    // Note: Not calling EnsureInit here to avoid spam
    EnsureArchipelagoInit();
    
    if (!g_archipelago || !g_archipelago->IsConnected()) {
        return;
    }
    
    // Process messages silently (no logging)
    g_archipelago->ProcessMessages();
}