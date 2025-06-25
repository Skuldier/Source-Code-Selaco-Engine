// archipelago_client.h - Minimal header with declarations only
#pragma once

// Just function declarations - no includes to avoid circular dependencies
void AP_Init();
void AP_Shutdown();
void AP_Update();
bool AP_Connect(const char* host, int port = 38281);
void AP_Disconnect();
bool AP_IsConnected();
void AP_Authenticate(const char* slotName, const char* password = nullptr);
void AP_SendLocationCheck(int64_t locationId);
void AP_SendChat(const char* message);
const char* AP_GetSlotName();
int AP_GetSlotNumber();
bool AP_HasCheckedLocation(int64_t locationId);
