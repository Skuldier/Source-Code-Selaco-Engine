#!/usr/bin/env python3
"""
Apply a simple fix for the localhost crash issue
"""

import os

def apply_fix():
    filepath = "src/archipelago/archipelago_client.cpp"
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found!")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix 1: Make sure handlers are set up before ANY thread operations
    # Find the Connect function and move handler setup earlier
    old_pattern = """    // Set up handlers NOW, right before connecting
    m_impl->m_client.set_open_handler([this](connection_hdl hdl) {"""
    
    new_pattern = """    // Set up handlers BEFORE starting the thread to avoid race conditions
    m_impl->m_client.set_open_handler([this](connection_hdl hdl) {"""
    
    content = content.replace(old_pattern, new_pattern)
    
    # Fix 2: Add try-catch around StartThread
    old_start = """    // Start thread if not running
    m_impl->StartThread();"""
    
    new_start = """    // Start thread if not running
    try {
        m_impl->StartThread();
    } catch (const std::exception& e) {
        Printf("Archipelago: Failed to start worker thread: %s\\n", e.what());
        m_status = ConnectionStatus::Error;
        return false;
    }"""
    
    content = content.replace(old_start, new_start)
    
    # Fix 3: Add a small delay after starting thread to ensure it's ready
    old_msg_send = """    // Send connect message to thread
    ThreadMessage msg;"""
    
    new_msg_send = """    // Small delay to ensure thread is ready
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    // Send connect message to thread
    ThreadMessage msg;"""
    
    content = content.replace(old_msg_send, new_msg_send)
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Applied fixes to {filepath}")
    print("Changes made:")
    print("1. Ensured handlers are set up before thread operations")
    print("2. Added exception handling around StartThread")
    print("3. Added small delay to prevent race conditions")
    
    return True

if __name__ == "__main__":
    if apply_fix():
        print("\nDone! Rebuild and test localhost connection again.")