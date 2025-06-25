// archipelago_client.cpp - Complete implementation with all fixes
#include <string>
#include <cstdint>

// Include protocol header first to get all type definitions
#include "archipelago_protocol.h"

// Include our header
#include "archipelago_client.h"

// Include printf
#include "../common/engine/printf.h"

// Import everything from Archipelago namespace
using namespace Archipelago;

// Define the missing AP_ functions that aren't in protocol.cpp
void AP_Init() {
    if (!g_archipelago) {
        g_archipelago = new ArchipelagoClient();
        Printf("Archipelago: Client initialized\n");
    }
}

void AP_Shutdown() {
    if (g_archipelago) {
        delete g_archipelago;
        g_archipelago = nullptr;
        Printf("Archipelago: Client shutdown\n");
    }
}

void AP_Update() {
    if (g_archipelago) {
        g_archipelago->update();
    }
}

// C interface functions
bool AP_Connect(const char* host, int port) {
    if (!g_archipelago) {
        Printf("AP_Connect: Client not initialized!\n");
        return false;
    }
    return g_archipelago->connect(host, port);
}

void AP_Disconnect() {
    if (g_archipelago) {
        g_archipelago->disconnect();
    }
}

bool AP_IsConnected() {
    return g_archipelago && g_archipelago->isConnected();
}

void AP_Authenticate(const char* slotName, const char* password) {
    if (!g_archipelago) {
        Printf("AP_Authenticate: Client not initialized!\n");
        return;
    }
    
    std::string pass = password ? password : "";
    g_archipelago->authenticate(slotName, pass);
}

void AP_SendLocationCheck(int64_t locationId) {
    if (!g_archipelago) {
        return;
    }
    g_archipelago->sendLocationCheck(locationId);
}

void AP_SendChat(const char* message) {
    if (!g_archipelago || !message) {
        return;
    }
    g_archipelago->sendChat(message);
}

const char* AP_GetSlotName() {
    if (!g_archipelago) {
        return "";
    }
    return g_archipelago->getSlotName().c_str();
}

int AP_GetSlotNumber() {
    if (!g_archipelago) {
        return -1;
    }
    return g_archipelago->getSlotNumber();
}

bool AP_HasCheckedLocation(int64_t locationId) {
    if (!g_archipelago) {
        return false;
    }
    return g_archipelago->hasCheckedLocation(locationId);
}
