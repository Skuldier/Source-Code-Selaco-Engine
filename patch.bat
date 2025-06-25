@echo off
title Fix g_archipelago and Rebuild
color 0A

echo ============================================================
echo     FIX G_ARCHIPELAGO AND CLEAN REBUILD
echo ============================================================
echo.

cd /d C:\Users\Skuldier\Documents\Source-Code-Selaco-Engine

echo Step 1: Fixing archipelago_client.h...
echo.

REM Create the fixed header
(
echo // archipelago_client.h - Fixed version
echo #pragma once
echo.
echo #include "archipelago_protocol.h"
echo.
echo // Ensure g_archipelago is visible
echo namespace Archipelago {
echo     extern ArchipelagoClient* g_archipelago;
echo }
echo.
echo using Archipelago::g_archipelago;
echo.
echo // Function declarations
echo void AP_Init();
echo void AP_Shutdown();
echo void AP_Update();
echo bool AP_Connect(const char* host, int port = 38281);
echo void AP_Disconnect();
echo bool AP_IsConnected();
echo void AP_Authenticate(const char* slotName, const char* password = nullptr);
echo void AP_SendLocationCheck(int64_t locationId);
echo void AP_SendChat(const char* message);
echo const char* AP_GetSlotName();
echo int AP_GetSlotNumber();
echo bool AP_HasCheckedLocation(int64_t locationId);
) > src\archipelago\archipelago_client.h

echo Fixed archipelago_client.h
echo.

echo Step 2: Clean build directory...
if exist build (
    echo Deleting old build directory...
    rmdir /s /q build
    echo Deleted.
) else (
    echo No build directory found.
)

echo.
echo Step 3: Creating fresh build directory...
mkdir build
cd build

echo.
echo Step 4: Running CMake...
cmake -G "Visual Studio 17 2022" -A x64 ..

echo.
echo Step 5: Building project...
cmake --build . --config Debug

echo.
echo ============================================================
echo                    BUILD COMPLETE!
echo ============================================================
echo.
echo If there are still errors:
echo 1. Check the output above for specific issues
echo 2. Make sure all source files exist in src\archipelago\
echo 3. Try building in Visual Studio directly
echo.
pause