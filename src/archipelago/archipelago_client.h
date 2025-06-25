// archipelago_client.h - Main interface for Selaco to Archipelago
#pragma once

#include "archipelago_protocol.h"

// Global Archipelago client instance
extern Archipelago::ArchipelagoClient* g_archipelago;

// C-style interface functions for game integration
extern "C" {
    // Initialize the Archipelago client
    void AP_Init();
    
    // Shutdown and cleanup
    void AP_Shutdown();
    
    // Update/poll the client (call from game loop)
    void AP_Update();
    
    // Connection functions
    bool AP_Connect(const char* host, int port = 38281);
    void AP_Disconnect();
    bool AP_IsConnected();
    
    // Authentication
    void AP_Authenticate(const char* slotName, const char* password = nullptr);
    
    // Game actions
    void AP_SendLocationCheck(int64_t locationId);
    void AP_SendChat(const char* message);
    
    // State queries
    const char* AP_GetSlotName();
    int AP_GetSlotNumber();
    bool AP_HasCheckedLocation(int64_t locationId);
}

// Helper macros for easy integration
#define ARCHIPELAGO_INIT() AP_Init()
#define ARCHIPELAGO_SHUTDOWN() AP_Shutdown()
#define ARCHIPELAGO_UPDATE() AP_Update()
