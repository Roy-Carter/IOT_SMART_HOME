@echo off
echo Starting IoT Smart Office System...
echo.

echo Starting Emulators...
start "Temperature & Humidity Sensor" python emulators/temperature_humidity_sensor.py
timeout /t 2 /nobreak > nul

start "Button Actuator" python emulators/button_actuator.py
timeout /t 2 /nobreak > nul

start "Relay Actuator" python emulators/relay_actuator.py
timeout /t 2 /nobreak > nul

timeout /t 3 /nobreak > nul

echo Starting Data Manager...
start "Data Manager" python data_manager/data_manager.py
timeout /t 2 /nobreak > nul

echo Starting Main GUI...
start "Main GUI Dashboard" python gui/main_gui.py

echo.
echo All applications started!
echo.
echo IMPORTANT:
echo 1. First, connect all emulators to the MQTT broker
echo 2. Then start the Data Manager and click "Start Data Collection"
echo 3. Finally, connect the Main GUI to view real-time data
echo.
pause
