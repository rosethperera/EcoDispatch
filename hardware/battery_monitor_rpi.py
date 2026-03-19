#!/usr/bin/env python3
"""
EcoDispatch Hardware Demo - Raspberry Pi Implementation

This script demonstrates hardware integration for the EcoDispatch system,
including battery monitoring, relay control, and communication with
Arduino-based sensors.

Hardware Requirements:
- Raspberry Pi 4/Zero W
- Arduino with battery monitoring sketch
- INA219 current/voltage sensor (on Arduino)
- DS18B20 temperature sensor (on Arduino)
- Relay modules for load control
- GPIO connections for relays

Connections:
Raspberry Pi GPIO:
- GPIO 17 -> Relay 1 (Solar inverter control)
- GPIO 18 -> Relay 2 (Battery charger control)
- GPIO 27 -> Relay 3 (Grid connection control)
- GPIO 22 -> LED indicator
- GPIO 23 -> Buzzer for alerts

Serial:
- Raspberry Pi UART -> Arduino Serial
"""

import sys
import os
import time
import json
import serial
import logging
from datetime import datetime
import RPi.GPIO as GPIO
import smbus2
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Add EcoDispatch to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ecodispatch import EcoDispatch
from ecodispatch.data_integration import load_real_data

# Configuration
ARDUINO_SERIAL_PORT = '/dev/ttyACM0'  # Adjust based on your setup
ARDUINO_BAUD_RATE = 9600

# GPIO pin definitions
RELAY_SOLAR = 17
RELAY_BATTERY = 18
RELAY_GRID = 27
LED_STATUS = 22
BUZZER_ALERT = 23

# System parameters
BATTERY_LOW_THRESHOLD = 20.0  # SOC percentage
BATTERY_HIGH_THRESHOLD = 80.0
TEMPERATURE_HIGH_THRESHOLD = 40.0
UPDATE_INTERVAL = 5  # seconds

class HardwareController:
    """
    Hardware control interface for EcoDispatch demo.
    """

    def __init__(self):
        self.setup_gpio()
        self.setup_serial()
        self.setup_logging()

        # System state
        self.battery_soc = 50.0
        self.battery_voltage = 48.0
        self.battery_current = 0.0
        self.battery_temperature = 25.0
        self.grid_connected = True
        self.solar_active = True
        self.battery_charging = False

    def setup_gpio(self):
        """Initialize GPIO pins."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup relay pins as outputs
        GPIO.setup([RELAY_SOLAR, RELAY_BATTERY, RELAY_GRID], GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(LED_STATUS, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(BUZZER_ALERT, GPIO.OUT, initial=GPIO.LOW)

        logging.info("GPIO setup complete")

    def setup_serial(self):
        """Initialize serial communication with Arduino."""
        try:
            self.serial = serial.Serial(ARDUINO_SERIAL_PORT, ARDUINO_BAUD_RATE, timeout=1)
            time.sleep(2)  # Allow Arduino to reset
            logging.info("Serial communication established")
        except serial.SerialException as e:
            logging.error(f"Failed to open serial port: {e}")
            self.serial = None

    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ecodispatch_hardware.log'),
                logging.StreamHandler()
            ]
        )

    def read_battery_data(self):
        """Read battery data from Arduino."""
        if not self.serial:
            return False

        try:
            line = self.serial.readline().decode('utf-8').strip()
            if line.startswith('{') and line.endswith('}'):
                data = json.loads(line)
                self.battery_voltage = data.get('voltage', self.battery_voltage)
                self.battery_current = data.get('current', self.battery_current)
                self.battery_soc = data.get('soc', self.battery_soc)
                self.battery_temperature = data.get('temperature', self.battery_temperature)
                return True
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
            logging.debug(f"Error parsing Arduino data: {e}")

        return False

    def control_relays(self, grid_power, solar_power, battery_power):
        """
        Control relays based on dispatch decisions.

        Args:
            grid_power: Power from grid (kW)
            solar_power: Power from solar (kW)
            battery_power: Power from/to battery (kW, negative = charging)
        """
        # Grid connection
        if grid_power > 0:
            GPIO.output(RELAY_GRID, GPIO.HIGH)  # Connect grid
            self.grid_connected = True
        else:
            GPIO.output(RELAY_GRID, GPIO.LOW)   # Disconnect grid
            self.grid_connected = False

        # Solar inverter
        if solar_power > 0:
            GPIO.output(RELAY_SOLAR, GPIO.HIGH)  # Enable solar
            self.solar_active = True
        else:
            GPIO.output(RELAY_SOLAR, GPIO.LOW)   # Disable solar
            self.solar_active = False

        # Battery charger/discharger
        if battery_power < 0:  # Charging
            GPIO.output(RELAY_BATTERY, GPIO.HIGH)  # Enable charging
            self.battery_charging = True
        elif battery_power > 0:  # Discharging
            GPIO.output(RELAY_BATTERY, GPIO.LOW)   # Enable discharging
            self.battery_charging = False
        else:
            GPIO.output(RELAY_BATTERY, GPIO.LOW)   # Idle
            self.battery_charging = False

    def safety_checks(self):
        """Perform safety checks and alerts."""
        alerts = []

        # Battery SOC checks
        if self.battery_soc < BATTERY_LOW_THRESHOLD:
            alerts.append("LOW BATTERY")
            GPIO.output(BUZZER_ALERT, GPIO.HIGH)
        elif self.battery_soc > BATTERY_HIGH_THRESHOLD:
            alerts.append("HIGH BATTERY SOC")

        # Temperature checks
        if self.battery_temperature > TEMPERATURE_HIGH_THRESHOLD:
            alerts.append("HIGH TEMPERATURE")
            GPIO.output(BUZZER_ALERT, GPIO.HIGH)

        # Clear alerts if conditions are normal
        if not alerts:
            GPIO.output(BUZZER_ALERT, GPIO.LOW)

        # Status LED
        GPIO.output(LED_STATUS, GPIO.HIGH if self.grid_connected else GPIO.LOW)

        return alerts

    def get_system_status(self):
        """Get current system status."""
        return {
            'battery_soc': self.battery_soc,
            'battery_voltage': self.battery_voltage,
            'battery_current': self.battery_current,
            'battery_temperature': self.battery_temperature,
            'grid_connected': self.grid_connected,
            'solar_active': self.solar_active,
            'battery_charging': self.battery_charging,
            'timestamp': datetime.now().isoformat()
        }

    def cleanup(self):
        """Cleanup GPIO and serial connections."""
        if self.serial:
            self.serial.close()

        GPIO.output([RELAY_SOLAR, RELAY_BATTERY, RELAY_GRID, LED_STATUS, BUZZER_ALERT], GPIO.LOW)
        GPIO.cleanup()
        logging.info("Hardware cleanup complete")


def run_hardware_demo():
    """
    Main hardware demo function.
    """
    print("EcoDispatch Hardware Demo Starting...")
    print("Press Ctrl+C to exit")

    controller = HardwareController()

    try:
        # Load simulation data
        data = load_real_data(days=1)

        # Initialize simulation
        results = EcoDispatch.simulate(data, strategy='carbon_min')

        # Get dispatch decisions
        dispatch = results['dispatch']

        # Demo loop
        for i, (timestamp, row) in enumerate(dispatch.iterrows()):
            if i >= 24:  # Limit to 24 hours for demo
                break

            print(f"\n--- Hour {i+1}: {timestamp} ---")

            # Read hardware data
            if controller.read_battery_data():
                print(".1f"
                      ".2f"
                      ".1f")

            # Get dispatch decision for this hour
            grid_power = row['grid']
            solar_power = row['solar']
            battery_power = row['battery']

            print(".1f"
                  ".1f"
                  ".1f")

            # Control hardware
            controller.control_relays(grid_power, solar_power, battery_power)

            # Safety checks
            alerts = controller.safety_checks()
            if alerts:
                print(f"ALERTS: {', '.join(alerts)}")

            # Status
            status = controller.get_system_status()
            print(f"Grid: {'ON' if status['grid_connected'] else 'OFF'}, "
                  f"Solar: {'ON' if status['solar_active'] else 'OFF'}, "
                  f"Battery: {'CHARGING' if status['battery_charging'] else 'IDLE'}")

            time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        logging.error(f"Demo error: {e}")
    finally:
        controller.cleanup()
        print("Demo complete")


if __name__ == "__main__":
    run_hardware_demo()