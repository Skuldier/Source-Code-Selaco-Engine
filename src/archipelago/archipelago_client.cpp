// archipelago_client.cpp - C interface implementation for Archipelago
#include "archipelago_client.h"
#include "../common/engine/printf.h"

// C-style interface implementation
extern "C" {

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

} // extern "C"
