@echo off
echo Starting IoT Smart Office System...
echo.

echo Starting Emulators...
start "Temperature & Humidity Sensor" python emulators/temperature_humidity_sensor.py
timeout /t 2 /nobreak > nul

start "Occupancy Sensor" python emulators/button_actuator.py
timeout /t 2 /nobreak > nul

start "AC/Fan Controller" python emulators/relay_actuator.py
timeout /t 2 /nobreak > nul

echo Starting Data Manager...
start "Data Manager" python data_manager/data_manager.py
timeout /t 2 /nobreak > nul

echo Starting Main GUI...
start "Main GUI Dashboard" python gui/main_gui.py

echo All applications started!
echo To stop all applications, run: stop_all.bat
