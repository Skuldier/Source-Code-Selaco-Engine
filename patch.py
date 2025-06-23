#!/usr/bin/env python3
"""
Patch script to update archipelago_ccmds.cpp with new commands
This script should be run from the Selaco source root directory
"""

import os
import shutil
from datetime import datetime

def patch_archipelago_ccmds():
    # Path to the file we need to patch
    file_path = "src/archipelago/archipelago_ccmds.cpp"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        print("Make sure you run this script from the Selaco source root directory")
        return False
    
    # Create backup
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Define the new ap_connect command
    new_ap_connect = '''// Connect to Archipelago server (non-blocking)
CCMD(ap_connect)
{
    if (argv.argc() < 2) {
        Printf("Usage: ap_connect <host> [port]\\n");
        Printf("Example: ap_connect localhost 38281\\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\\n");
        return;
    }
    
    // Check current status
    auto status = g_archipelago->GetConnectionStatus();
    if (status == ConnectionStatus::Connecting) {
        Printf("Already attempting to connect...\\n");
        return;
    } else if (status == ConnectionStatus::Connected || status == ConnectionStatus::InGame) {
        Printf("Already connected! Use ap_disconnect first.\\n");
        return;
    }
    
    std::string host = argv[1];
    int port = 38281;
    
    if (argv.argc() >= 3) {
        port = atoi(argv[2]);
    }
    
    Printf("Archipelago: Starting connection to %s:%d...\\n", host.c_str(), port);
    if (g_archipelago->Connect(host, port)) {
        Printf("Archipelago: Connection attempt initiated. Use 'ap_status' to check progress.\\n");
    } else {
        Printf("Archipelago: Failed to start connection attempt.\\n");
    }
}'''

    # Define the new ap_status command
    new_ap_status = '''// Check connection status
CCMD(ap_status)
{
    if (!g_archipelago) {
        Printf("Archipelago client not initialized!\\n");
        return;
    }
    
    auto status = g_archipelago->GetConnectionStatus();
    switch (status) {
        case ConnectionStatus::Disconnected:
            Printf("Archipelago: Disconnected\\n");
            break;
        case ConnectionStatus::Connecting:
            Printf("Archipelago: Connecting... (please wait)\\n");
            break;
        case ConnectionStatus::Connected:
            Printf("Archipelago: Connected (not authenticated)\\n");
            break;
        case ConnectionStatus::InGame:
            Printf("Archipelago: Connected and authenticated\\n");
            break;
        case ConnectionStatus::Error:
            Printf("Archipelago: Error state - use ap_disconnect to reset\\n");
            break;
    }
}'''

    # Define the AP_Tick function to add at the end
    ap_tick_function = '''
// Also update the tick function to process messages
// This should be called from the game's main loop
void AP_Tick() {
    if (g_archipelago) {
        g_archipelago->ProcessMessages();
    }
}'''

    # Replace the old ap_connect command
    # Find the start of the old ap_connect
    connect_start = content.find("// Connect to Archipelago server")
    if connect_start == -1:
        print("Error: Could not find ap_connect command!")
        return False
    
    # Find the end of the ap_connect command (next CCMD or end of function)
    connect_end = content.find("// Disconnect from server", connect_start)
    if connect_end == -1:
        print("Error: Could not find end of ap_connect command!")
        return False
    
    # Replace the ap_connect command
    new_content = content[:connect_start] + new_ap_connect + "\\n\\n" + content[connect_end:]
    
    # Now replace the ap_status command
    # Find the old ap_status
    status_start = new_content.find("// Show connection status")
    if status_start == -1:
        print("Error: Could not find ap_status command!")
        return False
    
    # Find the end of ap_status (next CCMD or end)
    status_end = new_content.find("// Test location check", status_start)
    if status_end == -1:
        # Try to find another delimiter
        status_end = new_content.find("CCMD(ap_check)", status_start)
        if status_end == -1:
            print("Error: Could not find end of ap_status command!")
            return False
    
    # Replace the ap_status command
    new_content = new_content[:status_start] + new_ap_status + "\\n\\n" + new_content[status_end:]
    
    # Add AP_Tick function at the end of the file (before the last closing brace if there is one)
    # Remove any trailing whitespace first
    new_content = new_content.rstrip()
    
    # Add the AP_Tick function
    new_content += ap_tick_function
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully patched {file_path}")
    print("\\nChanges made:")
    print("1. Updated ap_connect command with non-blocking connection support")
    print("2. Updated ap_status command with detailed connection states")
    print("3. Added AP_Tick() function for message processing")
    print("\\nIMPORTANT: You need to call AP_Tick() from the game's main loop!")
    
    return True

if __name__ == "__main__":
    success = patch_archipelago_ccmds()
    if not success:
        print("\\nPatch failed! Check the error messages above.")
        exit(1)
    else:
        print("\\nPatch completed successfully!")
        exit(0)