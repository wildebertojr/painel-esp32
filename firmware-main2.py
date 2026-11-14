
# ESTACAO METEOROLOGICA COM ESP32 (MicroPython) -> ThingSpeak
#
# Sensores e pinos:
#   DHT22       : OUT no GPIO 4   -> temperatura e umidade
#   BMP280      : SDA 21, SCL 22  -> pressao (I2C, 0x76, SDO no GND)
#   LDR         : AO no GPIO 35   -> luminosidade (escala relativa)
#   MQ-135      : AO no GPIO 34   -> qualidade do ar (via divisor 20k + 10k)
#
# Campos do canal no ThingSpeak:
#   field1 = Temperatura (C)
#   field2 = Umidade (%)
#   field3 = Pressao (hPa)
#   field4 = Luz (0 a 1000)
#   field5 = Gases (0 a 100)

import time
import struct
import network
import dht
from machine import Pin, ADC, I2C

try:
    import urequests as requests
except ImportError:
    import requests


# ====== 1. CONFIGURE AQUI ======
SSID = ""
SENHA = ""
THINGSPEAK_WRITE_KEY = ""

INTERVALO_ENVIO_S = 20
LDR_INVERTIDO = False
AQUECIMENTO_MQ_S = 180
# ===============================


# ====== 2. PINOS ======
PIN_DHT = 4
PIN_LDR = 35
PIN_MQ135 = 34
PIN_SDA = 21
PIN_SCL = 22
# ======================


# ====== DRIVER BMP280 (I2C) ======
class BMP280:
    def __init__(self, i2c, addr=0x76):
        self.i2c = i2c
        self.addr = addr
        chip = i2c.readfrom_mem(addr, 0xD0, 1)[0]

        if chip not in (0x56, 0x57, 0x58, 0x60):
            raise OSError("chip desconhecido")

        c = i2c.readfrom_mem(addr, 0x88, 24)

        (self.T1, self.T2, self.T3,
         self.P1, self.P2, self.P3, self.P4, self.P5,
         self.P6, self.P7, self.P8, self.P9) = struct.unpack("<HhhHhhhhhhhh", c)

        i2c.writeto_mem(addr, 0xF5, b"\x10")
        i2c.writeto_mem(addr, 0xF4, b"\x57")
        time.sleep_ms(100)

    def temperatura_pressao(self):
        d = self.i2c.readfrom_mem(self.addr, 0xF7, 6)

        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)

        v1 = (adc_t / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((adc_t / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        t_fine = v1 + v2
        temp = t_fine / 5120.0

        v1 = t_fine / 2.0 - 64000.0
        v2 = v1 * v1 * self.P6 / 32768.0
        v2 = v2 + v1 * self.P5 * 2.0
        v2 = v2 / 4.0 + self.P4 * 65536.0
        v1 = (self.P3 * v1 * v1 / 524288.0 + self.P2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self.P1

        if v1 == 0:
            return temp, None

        p = 1048576.0 - adc_p
        p = (p - v2 / 4096.0) * 6250.0 / v1

        v1 = self.P9 * p * p / 2147483648.0
        v2 = p * self.P8 / 32768.0
        p = p + (v1 + v2 + self.P7) / 16.0

        return temp, p


# ====== LEITURA DOS SENSORES ======
def media_adc(adc, n=10):
    soma = 0

    for _ in range(n):
        soma += adc.read_u16() >> 4
        time.sleep_ms(5)

    return soma / n


def ler_luz(adc):
    bruto = media_adc(adc)
    luz = int(bruto / 4095 * 1000)

    return 1000 - luz if LDR_INVERTIDO else luz


def ler_gas(adc):
    # MQ-135: indice relativo de 0 a 100 (nao e ppm calibrado).
    # Divisor 20k + 10k: o pino recebe 1/3 da tensao do AO.

    bruto = media_adc(adc)
    v_pino = bruto / 4095 * 3.3
    v_ao = v_pino * 3.0

    indice = v_ao / 5.0 * 100.0

    return max(0, min(100, round(indice)))


def ler_dht(sensor):
    try:
        sensor.measure()
        return sensor.temperature(), sensor.humidity()

    except OSError:
        return None, None


def iniciar_bmp(i2c):
    for addr in (0x76, 0x77):
        try:
            bmp = BMP280(i2c, addr)
            print("BMP280 iniciado no endereco", hex(addr))
            return bmp

        except OSError:
            pass

    print("Erro: BMP280 nao encontrado. Verifique SDO no GND, CSB em 3,3V e cabos SDA/SCL.")

    return None


def ler_pressao(bmp):
    if bmp is None:
        return None

    try:
        _, p = bmp.temperatura_pressao()

        return None if p is None else p / 100.0

    except OSError:
        return None


# ====== WI-FI ======
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Conectando ao WiFi", end="")

        wlan.connect(SSID, SENHA)
        t0 = time.ticks_ms()

        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                print("\nTempo esgotado, tentando de novo")

                wlan.disconnect()
                wlan.connect(SSID, SENHA)
                t0 = time.ticks_ms()

            print(".", end="")
            time.sleep(0.5)

    print("\nConectado! IP:", wlan.ifconfig()[0])

    return wlan


# ====== PROGRAMA PRINCIPAL ======
def main():

    sensor_dht = dht.DHT22(Pin(PIN_DHT))

    adc_ldr = ADC(Pin(PIN_LDR))
    adc_ldr.atten(ADC.ATTN_11DB)

    adc_mq = ADC(Pin(PIN_MQ135))
    adc_mq.atten(ADC.ATTN_11DB)

    i2c = I2C(0, sda=Pin(PIN_SDA), scl=Pin(PIN_SCL), freq=100000)

    bmp = iniciar_bmp(i2c)

    wlan = conectar_wifi()

    inicio = time.ticks_ms()

    time.sleep(2)

    while True:

        if not wlan.isconnected():
            wlan = conectar_wifi()

        temp, umid = ler_dht(sensor_dht)
        pres = ler_pressao(bmp)
        luz = ler_luz(adc_ldr)
        gas = ler_gas(adc_mq)

        mq_pronto = time.ticks_diff(
            time.ticks_ms(), inicio
        ) >= AQUECIMENTO_MQ_S * 1000

        if temp is None:
            print("AVISO: DHT22 sem leitura (confira os fios e o GPIO 4)")

        if pres is None:
            print("AVISO: BMP280 sem leitura (confira SDA 21 e SCL 22)")

        if not mq_pronto:
            print("MQ-135 aquecendo (gases so serao enviados apos 3 minutos)")

        # Envia somente os campos com leitura valida
        url = "https://api.thingspeak.com/update?api_key=" + THINGSPEAK_WRITE_KEY

        if temp is not None:
            url += "&field1=%.1f&field2=%.1f" % (temp, umid)

        if pres is not None:
            url += "&field3=%.1f" % pres

        url += "&field4=%d" % luz

        if mq_pronto:
            url += "&field5=%d" % gas

        print(
            "Enviado -> T=%s | U=%s | P=%s | Luz=%d | Gas=%d" % (
                "%.1f" % temp if temp is not None else "--",
                "%.1f" % umid if umid is not None else "--",
                "%.1f" % pres if pres is not None else "--",
                luz,
                gas
            )
        )

        try:
            r = requests.get(url)

            print(
                "HTTP", r.status_code,
                "| ThingSpeak respondeu:", r.text,
                "(0 = falhou)"
            )

            r.close()

        except Exception as e:
            print("Erro ao enviar:", e)

        time.sleep(INTERVALO_ENVIO_S)


main()
