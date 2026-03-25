# EcoDispatch Hardware Demo

This directory contains prototype hardware experiments that show how EcoDispatch concepts could connect to battery telemetry and relay control. These files should be treated as demo and exploration code, not as a validated deployment package.

## Arduino Implementation

### `battery_monitor_arduino.ino`

Arduino sketch for battery monitoring and protection.

**Features:**
- Battery voltage, current, and temperature monitoring
- State of charge (SOC) estimation using Coulomb counting
- Safety protection (over/under voltage, temperature)
- Relay control for battery disconnect
- LCD display for status
- Serial communication with Raspberry Pi

**Hardware Requirements:**
- Arduino Uno/Nano/Mega
- INA219 current/voltage sensor
- DS18B20 temperature sensor
- Relay module (optional)
- LCD display (optional)

**Connections:**
```
INA219:
  SDA -> A4 (Uno) / 20 (Mega)
  SCL -> A5 (Uno) / 21 (Mega)
  VCC -> 5V
  GND -> GND

DS18B20:
  Data -> Digital Pin 2
  VCC -> 5V
  GND -> GND
  4.7kΩ resistor between Data and VCC

Relay (optional):
  Signal -> Digital Pin 3

LCD (optional):
  I2C connection (SDA=A4, SCL=A5)
```

**Serial Output Format:**
```json
{
  "voltage": 48.5,
  "current": 2.3,
  "power": 111.55,
  "soc": 67.8,
  "temperature": 28.4,
  "coulomb_count": 15.7
}
```

## Raspberry Pi Implementation

### `battery_monitor_rpi.py`

Python script for Raspberry Pi hardware control and EcoDispatch integration.

**Features:**
- Serial communication with Arduino
- GPIO control for relays and indicators
- Demo relay control based on EcoDispatch-derived power decisions
- Safety monitoring and alerts
- Integration with EcoDispatch simulation outputs

**Hardware Requirements:**
- Raspberry Pi 4/Zero W
- Arduino with battery monitoring sketch
- Relay modules for load control
- LED and buzzer for status/alerts

**GPIO Connections:**
```
GPIO 17 -> Relay 1 (Solar inverter control)
GPIO 18 -> Relay 2 (Battery charger control)
GPIO 27 -> Relay 3 (Grid connection control)
GPIO 22 -> LED status indicator
GPIO 23 -> Buzzer for alerts
```

**Setup Instructions:**

1. **Install Dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-rpi.gpio
   pip3 install adafruit-circuitpython-ads1x15
   ```

2. **Enable Serial:**
   ```bash
   sudo raspi-config
   # Interfacing Options -> Serial -> Enable
   ```

3. **Run the Demo:**
   ```bash
   python3 battery_monitor_rpi.py
   ```

## Integration with EcoDispatch

The hardware demo shows one possible prototype workflow:

1. Run an EcoDispatch simulation strategy locally
2. Read battery telemetry from the Arduino sketch
3. Map simulated power decisions to simple relay-control actions
4. Monitor basic safety conditions and provide alerts
5. Log data for debugging and inspection

This is a concept demonstration. It does not establish that the control loop is ready for direct operation on a real energy system.

## Safety Features

- **Battery Protection:** Automatic disconnect on over/under voltage
- **Temperature Monitoring:** Alerts for high/low temperatures
- **SOC Limits:** Prevents overcharge/discharge
- **Emergency Stop:** Manual override capability

## Data Logging

All sensor data and control actions are logged to `ecodispatch_hardware.log` for analysis and debugging.

## Future Enhancements

- Real carbon intensity API integration
- Wireless communication (WiFi/Bluetooth)
- Multiple battery bank support
- Advanced BMS integration
- Web interface for remote monitoring
- Stronger validation between simulated dispatch outputs and physical hardware behavior
