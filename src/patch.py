#!/usr/bin/env python3
"""
Fix ASIO threading issue in archipelago_client.cpp
Run this from the src directory
"""

import os
import sys

def fix_asio_threading():
    client_file = "archipelago/archipelago_client.cpp"
    
    if not os.path.exists(client_file):
        print(f"Error: {client_file} not found. Run this from the src directory.")
        sys.exit(1)
    
    # Read the current file
    with open(client_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Make sure ASIO thread starts BEFORE creating connection
    # Find the Start() call and move it earlier
    old_pattern = """    try {
        // Start the ASIO thread if not already running
        m_impl->Start();
        
        // Create a new connection"""
    
    new_pattern = """    try {
        // Start the ASIO thread FIRST - this is critical!
        m_impl->Start();
        
        // Give ASIO thread time to initialize
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Create a new connection"""
    
    content = content.replace(old_pattern, new_pattern)
    
    # Fix 2: Improve the Start() method to ensure io_service is ready
    old_start = """    void Start() {
        if (!m_running) {
            m_running = true;
            m_asio_thread = std::thread([this]() {
                Printf("Archipelago: ASIO thread started\\n");
                try {
                    m_client.run();
                } catch (const std::exception& e) {
                    Printf("Archipelago: ASIO thread error: %s\\n", e.what());
                }
                Printf("Archipelago: ASIO thread ended\\n");
            });
        }
    }"""
    
    new_start = """    void Start() {
        if (!m_running) {
            m_running = true;
            
            // Reset the io_service in case it was stopped before
            m_client.reset();
            
            m_asio_thread = std::thread([this]() {
                Printf("Archipelago: ASIO thread started\\n");
                try {
                    // Keep the io_service running even if there's no work
                    asio::io_service::work work(m_client.get_io_service());
                    m_client.run();
                } catch (const std::exception& e) {
                    Printf("Archipelago: ASIO thread error: %s\\n", e.what());
                }
                Printf("Archipelago: ASIO thread ended\\n");
            });
            
            // Wait a bit to ensure thread is running
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }"""
    
    content = content.replace(old_start, new_start)
    
    # Fix 3: Add io_service work to keep it alive
    # Add include for asio work
    includes_section = """// Standard library includes
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>
#include <atomic>
#include <condition_variable>
#include <queue>"""
    
    new_includes = """// Standard library includes
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>
#include <atomic>
#include <condition_variable>
#include <queue>
#include <asio/io_service.hpp>"""
    
    content = content.replace(includes_section, new_includes)
    
    # Fix 4: Change how we stop the io_service
    old_stop = """    void Stop() {
        if (m_running) {
            m_running = false;
            m_client.stop();
            if (m_asio_thread.joinable()) {
                m_asio_thread.join();
            }
        }
    }"""
    
    new_stop = """    void Stop() {
        if (m_running) {
            m_running = false;
            
            // Stop the io_service gracefully
            m_client.get_io_service().stop();
            
            if (m_asio_thread.joinable()) {
                m_asio_thread.join();
            }
        }
    }"""
    
    content = content.replace(old_stop, new_stop)
    
    # Fix 5: Add more debug output to see thread state
    thread_start = """            m_asio_thread = std::thread([this]() {
                Printf("Archipelago: ASIO thread started\\n");"""
    
    debug_thread_start = """            m_asio_thread = std::thread([this]() {
                Printf("Archipelago: ASIO thread started (ID: %d)\\n", std::this_thread::get_id());"""
    
    content = content.replace(thread_start, debug_thread_start)
    
    # Write the fixed file
    with open(client_file, 'w') as f:
        f.write(content)
    
    print(f"Successfully fixed ASIO threading in {client_file}")
    print("\nKey fixes applied:")
    print("1. ASIO thread starts before connection attempt")
    print("2. Added io_service::work to keep it running")
    print("3. Added delays to ensure thread initialization")
    print("4. Improved thread stop mechanism")
    print("\nPlease rebuild and try connecting again.")

if __name__ == "__main__":
    fix_asio_threading()