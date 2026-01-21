@echo off
echo Starting IoT Smart Office Emulators...
echo.

start "Temperature & Humidity Sensor" python emulators/temperature_humidity_sensor.py
timeout /t 2 /nobreak > nul

start "Occupancy Sensor" python emulators/button_actuator.py
timeout /t 2 /nobreak > nul

start "AC/Fan Controller" python emulators/relay_actuator.py
timeout /t 2 /nobreak > nul

echo All emulators started!
echo Please start the Data Manager and Main GUI applications separately.
echo.
echo To stop all applications, run: stop_all.bat
pause
