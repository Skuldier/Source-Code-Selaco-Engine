// Test program to verify Archipelago connection
// Compile this separately to test your connection logic

#include <iostream>
#include "../common/engine/printf.h"
#include "archipelago_client.h"

// Test console commands
void TestConnection() {
    using namespace Archipelago;
    
    // Initialize the client
    AP_Init();
    
    if (!g_archipelago) {
        Printf("ERROR: Failed to initialize Archipelago client!\n");
        return;
    }
    
    // Test 1: Connect to a server
    Printf("\n=== TEST 1: Connecting to archipelago.gg:58697 ===\n");
    bool connected = g_archipelago->Connect("archipelago.gg", 58697);
    
    if (!connected) {
        Printf("ERROR: Failed to initiate connection\n");
        return;
    }
    
    // Give it time to connect
    Printf("Waiting for connection...\n");
    for (int i = 0; i < 50; i++) { // 5 seconds timeout
        g_archipelago->ProcessMessages();
        
        if (g_archipelago->GetStatus() == ConnectionStatus::Connected) {
            Printf("SUCCESS: Connected to server!\n");
            break;
        } else if (g_archipelago->GetStatus() == ConnectionStatus::Error) {
            Printf("ERROR: Connection failed!\n");
            return;
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    // Test 2: Authenticate with a slot
    if (g_archipelago->GetStatus() == ConnectionStatus::Connected) {
        Printf("\n=== TEST 2: Authenticating as 'TestSlot' ===\n");
        g_archipelago->Authenticate("TestSlot", "");
        
        // Process authentication
        for (int i = 0; i < 30; i++) { // 3 seconds timeout
            g_archipelago->ProcessMessages();
            
            if (g_archipelago->GetStatus() == ConnectionStatus::InGame) {
                Printf("SUCCESS: Authenticated successfully!\n");
                break;
            } else if (g_archipelago->GetStatus() == ConnectionStatus::Error) {
                Printf("ERROR: Authentication failed!\n");
                break;
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
    
    // Test 3: Send a ping
    if (g_archipelago->GetStatus() == ConnectionStatus::InGame) {
        Printf("\n=== TEST 3: Sending ping ===\n");
        g_archipelago->SendPing();
        
        // Wait for response
        for (int i = 0; i < 20; i++) {
            g_archipelago->ProcessMessages();
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
    
    // Cleanup
    Printf("\n=== Disconnecting ===\n");
    g_archipelago->Disconnect();
    AP_Shutdown();
    
    Printf("\n=== Connection test complete ===\n");
}

int main() {
    TestConnection();
    return 0;
}