@echo off
echo Stopping IoT Smart Office System...
echo.

echo Killing application windows...

taskkill /FI "WINDOWTITLE eq Temperature & Humidity Sensor*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Occupancy Sensor*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AC/Fan Controller*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Data Manager*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Main GUI Dashboard*" /F >nul 2>&1

REM Alternative method - kill by process name if window title doesn't work
taskkill /IM python.exe /F >nul 2>&1

timeout /t 1 /nobreak > nul

echo.
echo All applications stopped!
echo.
pause
