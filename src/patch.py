#!/usr/bin/env python3
"""
Comprehensive diagnostic and fix tool for Archipelago integration in Selaco
"""

import os
import sys
import re

def check_files_exist(archipelago_dir):
    """Check if all required Archipelago files exist"""
    required_files = [
        "lws_client.h",
        "lws_client.cpp",
        "archipelago_protocol.h",
        "archipelago_protocol.cpp",
        "archipelago_commands.cpp"
    ]
    
    print("🔍 Checking Archipelago source files...")
    print(f"   Directory: {archipelago_dir}")
    print()
    
    all_exist = True
    for file in required_files:
        file_path = os.path.join(archipelago_dir, file)
        if os.path.exists(file_path):
            print(f"   ✅ {file} - Found")
        else:
            print(f"   ❌ {file} - MISSING!")
            all_exist = False
    
    # List actual files in directory
    if os.path.exists(archipelago_dir):
        print("\n📁 Actual files in archipelago directory:")
        for file in os.listdir(archipelago_dir):
            if os.path.isfile(os.path.join(archipelago_dir, file)):
                print(f"   - {file}")
    else:
        print(f"\n❌ Directory does not exist: {archipelago_dir}")
        all_exist = False
    
    return all_exist

def analyze_cmake_file(cmake_path):
    """Analyze the CMakeLists.txt for issues"""
    print("\n🔍 Analyzing CMakeLists.txt...")
    
    if not os.path.exists(cmake_path):
        print(f"   ❌ CMakeLists.txt not found at: {cmake_path}")
        return None
    
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find Archipelago section
    archipelago_start = content.find("# ARCHIPELAGO WEBSOCKET SUPPORT")
    if archipelago_start == -1:
        print("   ❌ Archipelago section not found in CMakeLists.txt")
        return None
    
    # Extract the add_library command
    add_lib_match = re.search(r'add_library\s*\(\s*archipelago_websocket[^)]+\)', content[archipelago_start:], re.DOTALL)
    if add_lib_match:
        add_lib_text = add_lib_match.group(0)
        print(f"   📄 Found add_library command:")
        print("   " + "\n   ".join(add_lib_text.split('\n')))
        
        # Check if paths have 'src/' prefix
        if 'src/archipelago/' in add_lib_text:
            print("\n   ⚠️  Issue found: Paths have 'src/' prefix")
            print("   This causes CMake to look in src/src/archipelago/")
            return "fix_paths"
    
    return "ok"

def fix_cmake_paths(cmake_path):
    """Fix the source file paths in CMakeLists.txt"""
    print("\n🔧 Fixing paths in CMakeLists.txt...")
    
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    backup_path = cmake_path + ".backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   📋 Created backup: {backup_path}")
    
    # Fix the paths in add_library
    original_content = content
    
    # Fix source file paths
    content = re.sub(
        r'add_library\s*\(\s*archipelago_websocket\s+STATIC\s+src/archipelago/(\w+\.cpp)',
        r'add_library(archipelago_websocket STATIC\n    archipelago/\1',
        content
    )
    
    # Fix additional source files
    content = content.replace('src/archipelago/lws_client.cpp', 'archipelago/lws_client.cpp')
    content = content.replace('src/archipelago/archipelago_protocol.cpp', 'archipelago/archipelago_protocol.cpp')
    content = content.replace('src/archipelago/archipelago_commands.cpp', 'archipelago/archipelago_commands.cpp')
    
    # Fix include directory
    content = content.replace('${CMAKE_CURRENT_SOURCE_DIR}/src/archipelago', '${CMAKE_CURRENT_SOURCE_DIR}/archipelago')
    
    if content != original_content:
        with open(cmake_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ Fixed paths in CMakeLists.txt")
        return True
    else:
        print("   ℹ️  No changes needed")
        return False

def main():
    root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
    
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    
    print("🚀 Archipelago Integration Diagnostic Tool")
    print("=" * 60)
    print(f"📁 Selaco source directory: {root_dir}")
    
    # Check paths
    archipelago_dir = os.path.join(root_dir, "src", "archipelago")
    cmake_path = os.path.join(root_dir, "src", "CMakeLists.txt")
    
    # Step 1: Check if files exist
    files_ok = check_files_exist(archipelago_dir)
    
    # Step 2: Analyze CMake file
    cmake_status = analyze_cmake_file(cmake_path)
    
    # Step 3: Apply fixes if needed
    if cmake_status == "fix_paths":
        if fix_cmake_paths(cmake_path):
            print("\n✅ Successfully fixed CMake configuration!")
    
    # Final recommendations
    print("\n📋 Next Steps:")
    print("=" * 60)
    
    if not files_ok:
        print("1. ❌ First, ensure all required source files are in:")
        print(f"   {archipelago_dir}")
        print("   You need: lws_client.cpp/h, archipelago_protocol.cpp/h, archipelago_commands.cpp")
    else:
        print("1. ✅ All source files are present")
    
    print("\n2. Clean your build directory:")
    print("   cd C:\\Users\\Skuldier\\Documents\\Source-Code-Selaco-Engine")
    print("   rmdir /s /q build")
    print("   mkdir build")
    print("   cd build")
    
    print('\n3. Run CMake again:')
    print('   cmake -G "Visual Studio 17 2022" -A x64 ..')
    
    print("\n4. If you still get errors, check:")
    print("   - That you're running CMake from the build directory")
    print("   - That Visual Studio 2022 is installed with C++ support")
    print("   - That you have Git installed (for FetchContent)")
    
    print("\n💡 Tip: If CMake still fails, try running this script again")
    print("   to see if there are any remaining issues.")

if __name__ == "__main__":
    main()