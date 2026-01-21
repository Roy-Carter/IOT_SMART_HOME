@echo off
echo Stopping IoT Smart Office System...
echo.

echo Killing application windows...

taskkill /FI "WINDOWTITLE eq Temperature & Humidity Sensor*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Occupancy Sensor*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq AC/Fan Controller*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq IoT Smart Office - Data Manager*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq IoT Smart Office - Main Dashboard*" /F /T >nul 2>&1

timeout /t 1 /nobreak > nul

echo.
echo All applications stopped!
echo.
exit /B
