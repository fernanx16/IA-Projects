import time
import RPi.GPIO as GPIO
from hx711 import HX711
from RPLCD.i2c import CharLCD
import board
import busio
import adafruit_mlx90614

# Pines
TRIG = 9
ECHO = 10
DT = 5
SCK = 6

# LCD I2C
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=16, rows=2, charmap='A00', auto_linebreaks=True)

# GPIO y sensores
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# HX711
hx = HX711(DT, SCK)
lcd.clear()
lcd.write_string("Calibrando peso...")
time.sleep(2)

hx.set_scale_ratio(25125)  # Ajustar con tu valor calibrado
hx.zero()

# MLX90614 (temperatura)
i2c = busio.I2C(board.SCL, board.SDA)
mlx = adafruit_mlx90614.MLX90614(i2c)

lcd.clear()
lcd.write_string("Listo")
time.sleep(2)
lcd.clear()

ALTURA_TOTAL = 209.0
ALTURA_MINIMA_VALIDA = 100.0

def medir_altura():
    GPIO.output(TRIG, False)
    time.sleep(0.002)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    tiempo = time.time()
    while GPIO.input(ECHO) == 0:
        start = time.time()
        if time.time() - tiempo > 0.1:
            return 0
    while GPIO.input(ECHO) == 1:
        end = time.time()
        if time.time() - tiempo > 0.1:
            return 0

    duracion = end - start
    distancia = duracion * 34300 / 2
    altura = ALTURA_TOTAL - distancia
    return altura if altura >= ALTURA_MINIMA_VALIDA else 0

try:
    while True:
        lcd.clear()
        lcd.write_string("Calculando...")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("5s espere...")

        pesos, temperaturas = [], []
        altura_maxima = 0

        inicio = time.time()
        while time.time() - inicio < 5:
            # Lecturas
            peso = hx.get_weight_mean(5)
            altura = medir_altura()
            temperatura = mlx.object_temperature

            # Guardar valores
            if peso > 0: pesos.append(peso)
            if altura > altura_maxima: altura_maxima = altura
            if temperatura > 0: temperaturas.append(temperatura)

            # Mostrar en vivo
            lcd.clear()
            lcd.write_string(f"P:{peso:.1f}kg A:{altura:.1f}")
            lcd.cursor_pos = (1, 0)
            lcd.write_string(f"T:{temperatura:.1f}C")
            time.sleep(0.5)

        # Calcular finales
        peso_final = sum(pesos)/len(pesos) if pesos else 0
        altura_final = altura_maxima
        altura_m = altura_final / 100 if altura_final > 0 else 0
        imc_final = peso_final / (altura_m**2) if altura_m > 0 else 0
        temp_final = sum(temperaturas)/len(temperaturas) if temperaturas else 0

        # Mostrar resultados finales
        lcd.clear()
        lcd.write_string(f"Peso:{peso_final:.1f}kg")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"Alt:{altura_final:.1f}cm")
        time.sleep(3)

        lcd.clear()
        lcd.write_string(f"IMC:{imc_final:.1f}")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"T:{temp_final:.1f}C")
        time.sleep(3)

except KeyboardInterrupt:
    lcd.clear()
    lcd.write_string("Apagando...")
    GPIO.cleanup()
