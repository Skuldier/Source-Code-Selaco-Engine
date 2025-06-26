#!/usr/bin/env python3
"""
Comprehensive fix for all Archipelago integration issues in Selaco
This script:
1. Removes duplicate function definitions
2. Updates CMakeLists.txt with all necessary files
3. Fixes libwebsockets zlib configuration
4. Creates dummy zlib.h if needed
"""

import os
import re
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return backup_path
    return None

def fix_archipelago_client_cpp(file_path):
    """Remove duplicate AP_Init, AP_Shutdown, AP_Update functions"""
    if not os.path.exists(file_path):
        print(f"⚠️  Skipping {file_path} - file not found")
        return False
    
    print(f"📝 Fixing duplicate definitions in archipelago_client.cpp...")
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove the specific duplicate functions
    # Pattern to match the duplicate function definitions
    patterns_to_remove = [
        r'void\s+AP_Init\s*\(\s*\)\s*\{[^}]*\}',
        r'void\s+AP_Shutdown\s*\(\s*\)\s*\{[^}]*\}',
        r'void\s+AP_Update\s*\(\s*\)\s*\{[^}]*\}',
    ]
    
    for pattern in patterns_to_remove:
        # Find matches with proper brace counting
        matches = list(re.finditer(pattern, content, re.DOTALL))
        for match in reversed(matches):  # Process in reverse to maintain indices
            # Check if this is within the first part of the file (not in extern "C")
            before_text = content[:match.start()]
            if 'extern "C"' not in before_text or before_text.count('extern "C"') > before_text.count('}'):
                # This is the duplicate we want to remove
                print(f"  Removing duplicate: {match.group()[:50]}...")
                content = content[:match.start()] + content[match.end():]
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed archipelago_client.cpp")
    return True

def update_cmake_lists(cmake_path):
    """Update CMakeLists.txt to include all Archipelago files"""
    if not os.path.exists(cmake_path):
        print(f"⚠️  Skipping CMakeLists.txt update - file not found")
        return False
    
    print(f"📝 Updating CMakeLists.txt...")
    backup_file(cmake_path)
    
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the archipelago_websocket library section
    pattern = r'(add_library\s*\(\s*archipelago_websocket\s+STATIC\s*\n)(.*?)(\))'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # Ensure all files are listed
        required_files = [
            'archipelago/lws_client.cpp',
            'archipelago/archipelago_protocol.cpp',
            'archipelago/archipelago_commands.cpp',
            'archipelago/archipelago_client.cpp'
        ]
        
        files_section = match.group(2)
        new_files_lines = []
        
        for file in required_files:
            if file not in files_section:
                print(f"  Adding missing file: {file}")
            new_files_lines.append(f"    {file}")
        
        new_files_section = '\n'.join(new_files_lines) + '\n'
        new_content = content[:match.start()] + match.group(1) + new_files_section + match.group(3) + content[match.end():]
        
        # Also ensure zlib is disabled in libwebsockets config
        new_content = re.sub(
            r'set\(LWS_WITH_BUNDLED_ZLIB\s+\w+\s+CACHE\s+BOOL[^)]+\)',
            'set(LWS_WITH_BUNDLED_ZLIB OFF CACHE BOOL "" FORCE)',
            new_content
        )
        
        # Add missing zlib configuration if not present
        if 'LWS_WITH_ZLIB OFF' not in new_content:
            # Find where to insert it (after LWS_WITH_BUNDLED_ZLIB)
            bundled_zlib_match = re.search(r'set\(LWS_WITH_BUNDLED_ZLIB[^)]+\)', new_content)
            if bundled_zlib_match:
                insert_pos = bundled_zlib_match.end()
                new_content = (new_content[:insert_pos] + 
                             '\nset(LWS_WITH_ZLIB OFF CACHE BOOL "" FORCE)' +
                             '\nset(LWS_WITH_ZIP_FOPS OFF CACHE BOOL "" FORCE)' +
                             new_content[insert_pos:])
        
        with open(cmake_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Updated CMakeLists.txt")
        return True
    else:
        print("⚠️  Could not find archipelago_websocket section in CMakeLists.txt")
        return False

def create_dummy_zlib_h(archipelago_dir):
    """Create a dummy zlib.h for libwebsockets when compression is disabled"""
    zlib_path = os.path.join(archipelago_dir, 'zlib.h')
    
    if os.path.exists(zlib_path):
        print(f"✅ zlib.h already exists at {zlib_path}")
        return True
    
    print(f"📝 Creating dummy zlib.h...")
    
    zlib_content = '''/* Minimal dummy zlib.h to satisfy libwebsockets when compression is disabled */
#ifndef ZLIB_H
#define ZLIB_H

/* Basic defines that libwebsockets might check for */
#define ZLIB_VERSION "1.2.11"
#define ZLIB_VERNUM 0x12b0

/* Return codes */
#define Z_OK            0
#define Z_STREAM_END    1
#define Z_NEED_DICT     2
#define Z_ERRNO        (-1)
#define Z_STREAM_ERROR (-2)
#define Z_DATA_ERROR   (-3)
#define Z_MEM_ERROR    (-4)
#define Z_BUF_ERROR    (-5)

/* Compression levels */
#define Z_NO_COMPRESSION         0
#define Z_BEST_SPEED             1
#define Z_BEST_COMPRESSION       9
#define Z_DEFAULT_COMPRESSION  (-1)

/* Dummy structures */
typedef struct z_stream_s {
    void *opaque;
    int data_type;
    unsigned long adler;
    unsigned long reserved;
} z_stream;

typedef z_stream *z_streamp;

/* We don't actually implement these, just declare them */
extern int inflateInit(z_streamp strm);
extern int inflate(z_streamp strm, int flush);
extern int inflateEnd(z_streamp strm);
extern int deflateInit(z_streamp strm, int level);
extern int deflate(z_streamp strm, int flush);
extern int deflateEnd(z_streamp strm);

#endif /* ZLIB_H */
'''
    
    with open(zlib_path, 'w', encoding='utf-8') as f:
        f.write(zlib_content)
    
    print(f"✅ Created dummy zlib.h at {zlib_path}")
    return True

def check_all_files_exist(src_dir):
    """Check that all required Archipelago files exist"""
    print("\n📂 Checking required files...")
    
    required_files = [
        "archipelago/lws_client.h",
        "archipelago/lws_client.cpp",
        "archipelago/archipelago_protocol.h",
        "archipelago/archipelago_protocol.cpp",
        "archipelago/archipelago_client.h",
        "archipelago/archipelago_client.cpp",
        "archipelago/archipelago_commands.cpp"
    ]
    
    all_present = True
    for file in required_files:
        file_path = os.path.join(src_dir, file)
        if os.path.exists(file_path):
            print(f"  ✅ Found: {file}")
        else:
            print(f"  ❌ Missing: {file}")
            all_present = False
    
    return all_present

def main():
    """Main function to apply all fixes"""
    import sys
    
    if len(sys.argv) < 2:
        root_dir = r"C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine"
        print(f"Using default path: {root_dir}")
    else:
        root_dir = sys.argv[1]
    
    print("🔧 Comprehensive Archipelago Integration Fix")
    print("=" * 50)
    
    # Define paths
    src_dir = os.path.join(root_dir, "src")
    archipelago_dir = os.path.join(src_dir, "archipelago")
    archipelago_client_cpp = os.path.join(archipelago_dir, "archipelago_client.cpp")
    cmake_path = os.path.join(src_dir, "CMakeLists.txt")
    
    # Apply fixes
    success = True
    
    # 1. Fix duplicate definitions
    if not fix_archipelago_client_cpp(archipelago_client_cpp):
        success = False
    
    # 2. Update CMakeLists.txt
    if not update_cmake_lists(cmake_path):
        success = False
    
    # 3. Create dummy zlib.h
    if not create_dummy_zlib_h(archipelago_dir):
        success = False
    
    # 4. Check all files exist
    if not check_all_files_exist(src_dir):
        success = False
    
    print("\n" + "=" * 50)
    
    if success:
        print("✅ All fixes applied successfully!")
        print("\n🔨 Next steps:")
        print("  1. Clean rebuild is recommended:")
        print(f"     cd {root_dir}")
        print("     rmdir /s /q build")
        print("     mkdir build")
        print("     cd build")
        print("     cmake -G \"Visual Studio 17 2022\" -A x64 ..")
        print("     cmake --build . --config Release")
        print("\n✅ The duplicate definition error should now be fixed!")
        print("\n📝 Test with these console commands in game:")
        print("  ap_connect localhost 38281")
        print("  ap_auth Player1")
        print("  ap_status")
    else:
        print("⚠️  Some issues were encountered. Please check the output above.")

if __name__ == "__main__":
    main()