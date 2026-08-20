# Real-Time Medical Triage System (Biometric Hardware Acquisition)

This subproject implements an automated embedded medical triage unit running on a **Raspberry Pi 3**[cite: 3]. The system continuously reads biometric parameters from physical hardware sensors to calculate patient metrics in real time and output diagnostic results onto an I2C display[cite: 3].

---

## Technical Overview

The system collects three key physical parameters—**Weight**, **Height**, and **Body Temperature**—to automatically derive the Body Mass Index (BMI)[cite: 3].

### Hardware & Sensor Architecture
* **Weight Sensing (HX711 + Load Cell):** Utilizes an HX711 24-bit ADC amplifier connected via GPIO pins `DT (GPIO 5)` and `SCK (GPIO 6)`[cite: 3]. Employs custom calibration ratios (`scale_ratio = 25125`) and automatic zeroing on boot[cite: 3].
* **Height Measurement (Ultrasonic Sensor HC-SR04):** Driven by GPIO `TRIG (GPIO 9)` and `ECHO (GPIO 10)`[cite: 3]. Distance is calculated based on ultrasonic pulse duration ($d = \frac{t \cdot 34300}{2}$), subtracted from a total baseline frame height of $209.0\text{ cm}$ with a valid threshold filtering ($>100.0\text{ cm}$)[cite: 3].
* **Contactless Temperature (MLX90614):** Reads object surface temperature using non-contact infrared thermal measurement over the I2C bus (`SDA`/`SCL`) via Adafruit libraries[cite: 3].
* **Display Interface (16x2 LCD via PCF8574 I2C Expander):** Connected to address `0x27` on I2C port 1[cite: 3]. Displays live sensor streaming and final processed readings[cite: 3].

---

## Acquisition & Diagnostic Workflow

1. **Initialization & Calibration:** On boot, the scale zeros out tare weight and initializes the I2C bus and GPIO modes[cite: 3].
2. **Continuous Windowed Sampling (5-Second Interval):**
   * Collects continuous streaming data over a 5-second sampling window[cite: 3].
   * Filters out zero-readings and dynamically computes running averages for weight and infrared temperature[cite: 3].
   * Tracks peak height measurement during the sampling period[cite: 3].
   * Displays live continuous feedback on the LCD during measurement[cite: 3].
3. **Derived Health Metrics Computation:**
   * Calculates mean weight ($kg$) and mean temperature ($^\circ C$)[cite: 3].
   * Computes **Body Mass Index (BMI)** using peak height transformed to meters:
     $$\text{BMI} = \frac{\text{Weight (kg)}}{\text{Height (m)}^2}$$
4. **Diagnostic Output Cycle:** Alternates diagnostic displays between weight/height and BMI/temperature on the LCD screen[cite: 3].
5. **Safe Shutdown:** Captures `KeyboardInterrupt` to clear the LCD screen and execute proper GPIO pin cleanup (`GPIO.cleanup()`)[cite: 3].

---

## File Structure

* `medical-triage-system.py`: Main python hardware loop handling GPIO interrupts, sensor readings, mathematical calculations, and I2C LCD output[cite: 3].

## Hardware Wiring Summary

| Component | Interface / Pin Type | Raspberry Pi GPIO Pin |
| :--- | :--- | :--- |
| **HX711 DT** | Digital In | GPIO 5[cite: 3] |
| **HX711 SCK** | Digital Out | GPIO 6[cite: 3] |
| **HC-SR04 TRIG** | Digital Out | GPIO 9[cite: 3] |
| **HC-SR04 ECHO** | Digital In | GPIO 10[cite: 3] |
| **MLX90614 SDA / SCL** | I2C Bus | Board SDA / SCL[cite: 3] |
| **16x2 LCD (PCF8574)** | I2C Bus | Address `0x27`[cite: 3] |

---

## How to Run

Ensure physical sensor connections and required dependencies are installed (`RPi.GPIO`, `hx711`, `RPLCD`, `adafruit-circuitpython-mlx90614`), then run[cite: 3]:

```bash
python medical-triage-system.py
