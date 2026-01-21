@echo off
echo Starting IoT Smart Office Emulators...
echo.

start "Temperature & Humidity Sensor" python emulators/temperature_humidity_sensor.py
timeout /t 2 /nobreak > nul

start "Button Actuator" python emulators/button_actuator.py
timeout /t 2 /nobreak > nul

start "Relay Actuator" python emulators/relay_actuator.py
timeout /t 2 /nobreak > nul

echo All emulators started!
echo Please start the Data Manager and Main GUI applications separately.
pause
