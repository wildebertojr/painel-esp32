# Pinagem da estação meteorológica (ESP32)

| Sensor / módulo | Grandeza | Pino da ESP32 | Observações |
|---|---|---|---|
| DHT22 | Temperatura e umidade | GPIO4 | Sinal digital |
| BMP280 | Pressão atmosférica | GPIO21 (SDA) / GPIO22 (SCL) | I2C, endereço 0x76; CSB em 3,3 V e SDO em GND |
| Módulo LDR | Luminosidade (0 a 1000, relativa) | GPIO35 | Saída analógica (AO), ADC1 |
| Módulo MQ-135 | Índice de gases (0 a 100, relativo) | GPIO34 | AO passa por divisor de tensão 20 kΩ + 10 kΩ (≈ 1,67 V); aquecimento de 180 s |
| Pluviômetro WH-SP-RG | Chuva (mm) e intensidade (mm/h) | GPIO13 | Interrupção na borda de descida, debounce de 100 ms, 0,2794 mm por pulso |

## Campos do canal ThingSpeak

| Campo | Grandeza | Unidade |
|---|---|---|
| field1 | Temperatura | °C |
| field2 | Umidade | % |
| field3 | Pressão (absoluta) | hPa |
| field4 | Luz (relativa) | 0 a 1000 |
| field5 | Gases (relativo) | 0 a 100 |
| field6 | Chuva acumulada | mm |
| field7 | Intensidade da chuva | mm/h |

Envio a cada 20 s por HTTPS GET em `https://api.thingspeak.com/update`.
