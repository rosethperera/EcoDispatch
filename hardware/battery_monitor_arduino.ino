/*
 * EcoDispatch Battery Monitor - Arduino Implementation
 *
 * This Arduino sketch monitors battery voltage, current, and temperature
 * for the EcoDispatch carbon-aware energy management system.
 *
 * Hardware Requirements:
 * - Arduino Uno/Nano/Mega
 * - INA219 current/voltage sensor
 * - DS18B20 temperature sensor
 * - Relay module for battery disconnect (optional)
 * - LCD display (optional)
 *
 * Connections:
 * INA219:
 *   SDA -> A4 (Uno) / 20 (Mega)
 *   SCL -> A5 (Uno) / 21 (Mega)
 *   VCC -> 5V
 *   GND -> GND
 *
 * DS18B20:
 *   Data -> Digital Pin 2
 *   VCC -> 5V
 *   GND -> GND
 *   4.7k resistor between Data and VCC
 *
 * Relay (optional):
 *   Signal -> Digital Pin 3
 */

#include <Wire.h>
#include <Adafruit_INA219.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <LiquidCrystal_I2C.h>

// Pin definitions
#define ONE_WIRE_BUS 2
#define RELAY_PIN 3
#define LED_PIN 13

// Constants
#define BATTERY_CAPACITY_AH 100.0  // Battery capacity in Ah
#define BATTERY_VOLTAGE_NOMINAL 48.0  // Nominal battery voltage in V
#define SOC_UPDATE_INTERVAL 1000  // SOC update interval in ms
#define SERIAL_UPDATE_INTERVAL 5000  // Serial output interval in ms

// Objects
Adafruit_INA219 ina219;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
LiquidCrystal_I2C lcd(0x27, 16, 2);  // LCD address and size

// Global variables
float batterySOC = 50.0;  // State of charge percentage
float batteryVoltage = 0.0;
float batteryCurrent = 0.0;
float batteryPower = 0.0;
float batteryTemperature = 25.0;
float coulombCount = 0.0;  // Ah counting

unsigned long lastSOCUpdate = 0;
unsigned long lastSerialUpdate = 0;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("EcoDispatch Battery Monitor Starting...");

  // Initialize pins
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);  // Relay normally closed
  digitalWrite(LED_PIN, LOW);

  // Initialize INA219
  if (!ina219.begin()) {
    Serial.println("Failed to find INA219 chip");
    while (1) { delay(10); }
  }
  Serial.println("INA219 initialized");

  // Initialize temperature sensor
  sensors.begin();
  Serial.println("Temperature sensor initialized");

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("EcoDispatch");
  lcd.setCursor(0, 1);
  lcd.print("Battery Monitor");

  delay(2000);
  lcd.clear();

  Serial.println("Setup complete");
}

void loop() {
  unsigned long currentTime = millis();

  // Read sensors
  readBatteryData();

  // Update SOC using Coulomb counting
  if (currentTime - lastSOCUpdate >= SOC_UPDATE_INTERVAL) {
    updateSOC();
    lastSOCUpdate = currentTime;
  }

  // Safety checks
  performSafetyChecks();

  // Update LCD display
  updateLCD();

  // Serial output for monitoring
  if (currentTime - lastSerialUpdate >= SERIAL_UPDATE_INTERVAL) {
    sendSerialData();
    lastSerialUpdate = currentTime;
  }

  delay(100);
}

void readBatteryData() {
  // Read voltage, current, and power from INA219
  batteryVoltage = ina219.getBusVoltage_V() + (ina219.getShuntVoltage_mV() / 1000);
  batteryCurrent = ina219.getCurrent_mA() / 1000.0;  // Convert to A
  batteryPower = ina219.getPower_mW() / 1000.0;  // Convert to W

  // Read temperature
  sensors.requestTemperatures();
  batteryTemperature = sensors.getTempCByIndex(0);

  // Handle invalid temperature readings
  if (batteryTemperature == DEVICE_DISCONNECTED_C) {
    batteryTemperature = 25.0;  // Default temperature
  }
}

void updateSOC() {
  // Coulomb counting for SOC estimation
  // SOC_new = SOC_old + (I * dt) / Capacity

  float dt_hours = (millis() - lastSOCUpdate) / 3600000.0;  // Convert to hours
  float deltaSOC = (batteryCurrent * dt_hours) / BATTERY_CAPACITY_AH * 100.0;

  batterySOC += deltaSOC;

  // Constrain SOC to realistic bounds
  batterySOC = constrain(batterySOC, 0.0, 100.0);

  // Update coulomb count
  coulombCount += batteryCurrent * dt_hours;
}

void performSafetyChecks() {
  // Low voltage protection
  if (batteryVoltage < 40.0) {  // 48V system, 40V cutoff
    digitalWrite(RELAY_PIN, LOW);  // Disconnect battery
    digitalWrite(LED_PIN, HIGH);   // Warning LED
    Serial.println("WARNING: Low battery voltage - disconnecting load");
  }
  else if (batteryVoltage > 54.0) {  // Overvoltage protection
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(LED_PIN, HIGH);
    Serial.println("WARNING: High battery voltage - disconnecting");
  }
  else {
    digitalWrite(RELAY_PIN, HIGH);  // Normal operation
    digitalWrite(LED_PIN, LOW);
  }

  // Temperature protection
  if (batteryTemperature > 45.0) {
    Serial.println("WARNING: High battery temperature");
    digitalWrite(LED_PIN, HIGH);
  }
  else if (batteryTemperature < 0.0) {
    Serial.println("WARNING: Low battery temperature");
    digitalWrite(LED_PIN, HIGH);
  }
}

void updateLCD() {
  lcd.setCursor(0, 0);
  lcd.print("SOC:");
  lcd.print(batterySOC, 1);
  lcd.print("% ");

  lcd.print("V:");
  lcd.print(batteryVoltage, 1);

  lcd.setCursor(0, 1);
  lcd.print("I:");
  lcd.print(batteryCurrent, 2);
  lcd.print("A ");

  lcd.print("T:");
  lcd.print(batteryTemperature, 1);
  lcd.print("C");
}

void sendSerialData() {
  // Send data in JSON-like format for easy parsing
  Serial.print("{");
  Serial.print("\"voltage\":"); Serial.print(batteryVoltage, 2);
  Serial.print(",\"current\":"); Serial.print(batteryCurrent, 3);
  Serial.print(",\"power\":"); Serial.print(batteryPower, 2);
  Serial.print(",\"soc\":"); Serial.print(batterySOC, 2);
  Serial.print(",\"temperature\":"); Serial.print(batteryTemperature, 1);
  Serial.print(",\"coulomb_count\":"); Serial.print(coulombCount, 3);
  Serial.println("}");
}

/*
 * Additional functions for EcoDispatch integration
 */

float getBatterySOC() {
  return batterySOC;
}

float getBatteryVoltage() {
  return batteryVoltage;
}

float getBatteryCurrent() {
  return batteryCurrent;
}

float getBatteryTemperature() {
  return batteryTemperature;
}

bool isBatterySafe() {
  return (batteryVoltage >= 40.0 && batteryVoltage <= 54.0 &&
          batteryTemperature >= 0.0 && batteryTemperature <= 45.0);
}

// Function to reset coulomb count (call after full charge/discharge calibration)
void resetCoulombCount() {
  coulombCount = 0.0;
  Serial.println("Coulomb count reset");
}