#!/usr/bin/env python3
"""
Full diagnostic patch to identify why g_archipelago is null despite AP_Init being called.
"""

import os
import sys
from datetime import datetime

def patch_client_cpp(filepath):
    """Add comprehensive diagnostics to archipelago_client.cpp"""
    
    print(f"Patching {filepath} with diagnostics...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Replace AP_Init with diagnostic version
    diagnostic_init = '''void AP_Init() {
    Printf("\\n=====================================\\n");
    Printf("ARCHIPELAGO: AP_Init() called\\n");
    Printf("  Function address: %p\\n", (void*)&AP_Init);
    Printf("  g_archipelago before: %p\\n", (void*)g_archipelago);
    Printf("  &g_archipelago: %p\\n", (void*)&g_archipelago);
    
    if (!g_archipelago) {
        Printf("ARCHIPELAGO: Creating new client...\\n");
        try {
            g_archipelago = new ArchipelagoClient();
            Printf("ARCHIPELAGO: Client created at %p\\n", (void*)g_archipelago);
            
            // Verify it's really there
            if (g_archipelago) {
                Printf("ARCHIPELAGO: Verification - client exists\\n");
                Printf("ARCHIPELAGO: Client status: %d\\n", (int)g_archipelago->GetStatus());
            } else {
                Printf("ARCHIPELAGO: ERROR - Client is null after creation!\\n");
            }
        } catch (const std::exception& e) {
            Printf("ARCHIPELAGO: EXCEPTION: %s\\n", e.what());
            g_archipelago = nullptr;
        } catch (...) {
            Printf("ARCHIPELAGO: UNKNOWN EXCEPTION\\n");
            g_archipelago = nullptr;
        }
    } else {
        Printf("ARCHIPELAGO: Client already exists\\n");
    }
    
    Printf("  g_archipelago after: %p\\n", (void*)g_archipelago);
    Printf("=====================================\\n\\n");
}'''

    # Replace AP_Init
    import re
    pattern = r'void AP_Init\(\)\s*\{[^}]+\}'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, diagnostic_init, content, flags=re.DOTALL)
    else:
        print("Warning: Could not find AP_Init to replace")
    
    # Add destructor logging
    destructor_diagnostic = '''ArchipelagoClient::~ArchipelagoClient() {
    Printf("ARCHIPELAGO: Destructor called for client at %p\\n", (void*)this);
    Disconnect();
}'''
    
    pattern = r'ArchipelagoClient::~ArchipelagoClient\(\)\s*\{[^}]+\}'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, destructor_diagnostic, content, flags=re.DOTALL)
    
    # Add static init check
    static_check = '''
// Global instance with diagnostics
ArchipelagoClient* g_archipelago = nullptr;

// Static initialization checker
static struct ArchipelagoInitChecker {
    ArchipelagoInitChecker() {
        Printf("\\nARCHIPELAGO: Module static init\\n");
        Printf("  g_archipelago at startup: %p\\n", (void*)g_archipelago);
    }
    ~ArchipelagoInitChecker() {
        Printf("ARCHIPELAGO: Module static destructor\\n");
        Printf("  g_archipelago at shutdown: %p\\n", (void*)g_archipelago);
    }
} g_initChecker;
'''
    
    # Replace the global instance declaration
    pattern = r'// Global instance\s*\nArchipelagoClient\* g_archipelago = nullptr;'
    if re.search(pattern, content):
        content = re.sub(pattern, static_check, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def patch_ccmds_cpp(filepath):
    """Add diagnostics and failsafe to ccmds"""
    
    print(f"Patching {filepath} with diagnostics...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Add failsafe function
    failsafe = '''
// Failsafe initialization
static void EnsureInit() {
    if (!g_archipelago) {
        Printf("\\nARCHIPELAGO: Emergency init required!\\n");
        Printf("  &g_archipelago = %p\\n", (void*)&g_archipelago);
        Printf("  g_archipelago = %p\\n", (void*)g_archipelago);
        AP_Init();
        if (!g_archipelago) {
            Printf("ARCHIPELAGO: Emergency init FAILED!\\n");
        } else {
            Printf("ARCHIPELAGO: Emergency init succeeded\\n");
        }
    }
}
'''
    
    # Insert after using namespace
    import re
    pattern = r'(using namespace Archipelago;\s*\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\1' + failsafe + '\n', content)
    
    # Update ap_connect with comprehensive diagnostics
    new_connect = '''CCMD(ap_connect)
{
    Printf("\\n=== AP_CONNECT START ===\\n");
    Printf("g_archipelago pointer: %p\\n", (void*)g_archipelago);
    Printf("&g_archipelago address: %p\\n", (void*)&g_archipelago);
    
    EnsureInit();
    
    if (argv.argc() < 2) {
        Printf("Usage: ap_connect <host> [port]\\n");
        Printf("Example: ap_connect localhost 38281\\n");
        return;
    }
    
    if (!g_archipelago) {
        Printf("FATAL: Still no client after EnsureInit!\\n");
        return;
    }
    
    Printf("Client exists at %p, proceeding...\\n", (void*)g_archipelago);
    
    std::string host = argv[1];
    int port = 38281;
    
    if (argv.argc() >= 3) {
        port = atoi(argv[2]);
    }
    
    if (g_archipelago->IsConnected()) {
        Printf("Already connected! Use ap_disconnect first.\\n");
        return;
    }
    
    Printf("Archipelago: Connecting to %s:%d...\\n", host.c_str(), port);
    
    try {
        if (g_archipelago->Connect(host, port)) {
            Printf("Archipelago: Connection successful!\\n");
            Printf("Archipelago: Waiting for server response...\\n");
        } else {
            Printf("Archipelago: Connection failed!\\n");
        }
    } catch (const std::exception& e) {
        Printf("EXCEPTION during connect: %s\\n", e.what());
    } catch (...) {
        Printf("UNKNOWN EXCEPTION during connect\\n");
    }
    
    Printf("=== AP_CONNECT END ===\\n\\n");
}'''
    
    # Replace ap_connect
    pattern = r'CCMD\(ap_connect\)\s*\{[^}]+\{[^}]+\}[^}]+\}'
    if re.search(pattern, content, re.DOTALL):
        # Find and replace the entire CCMD
        start = content.find('CCMD(ap_connect)')
        if start != -1:
            # Count braces to find the end
            brace_count = 0
            pos = content.find('{', start)
            end = pos
            while pos < len(content) and brace_count >= 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = pos + 1
                        break
                pos += 1
            
            content = content[:start] + new_connect + content[end:]
    
    # Add EnsureInit to other commands
    commands = ['ap_status', 'ap_disconnect', 'ap_ping', 'ap_auth', 'ap_check']
    for cmd in commands:
        pattern = rf'(CCMD\({cmd}\)\s*\{{\s*\n)'
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1    EnsureInit();\n    \n', content)
    
    # Update AP_Tick
    pattern = r'(void AP_Tick\(\)\s*\{\s*\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\1    // Note: Not calling EnsureInit here to avoid spam\n', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    if len(sys.argv) > 1:
        src_dir = sys.argv[1]
    else:
        src_dir = "src"
    
    print("=== FULL ARCHIPELAGO DIAGNOSTIC PATCH ===\n")
    
    client_cpp = os.path.join(src_dir, "archipelago", "archipelago_client.cpp")
    ccmds_cpp = os.path.join(src_dir, "archipelago", "archipelago_ccmds.cpp")
    
    success = True
    
    if os.path.exists(client_cpp):
        if not patch_client_cpp(client_cpp):
            success = False
    else:
        print(f"Error: {client_cpp} not found!")
        success = False
    
    if os.path.exists(ccmds_cpp):
        if not patch_ccmds_cpp(ccmds_cpp):
            success = False
    else:
        print(f"Error: {ccmds_cpp} not found!")
        success = False
    
    if success:
        print("\n=== PATCHES APPLIED ===")
        print("\nThis diagnostic patch adds:")
        print("1. Detailed logging in AP_Init()")
        print("2. Static initialization checking")
        print("3. Emergency initialization in commands")
        print("4. Exception handling and reporting")
        print("\nRebuild the project:")
        print("  cd build")
        print("  cmake --build . --config Release")
        print("\nWhen you run Selaco, look for:")
        print("- 'ARCHIPELAGO: Module static init'")
        print("- 'ARCHIPELAGO: AP_Init() called'")
        print("- Any error messages or exceptions")
        print("\nThen try 'ap_connect localhost' and check the diagnostic output.")

if __name__ == "__main__":
    main()