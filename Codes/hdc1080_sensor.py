from machine import I2C, Pin
from time import sleep

class HDC1080:
    def __init__(self, i2c=None, addr=0x40):
        self.i2c = i2c or I2C(1, scl=Pin(5), sda=Pin(4), freq=100_000)
        self.addr = addr

    def reset(self):
        """Comando de reset interno do HDC1080."""
        self.i2c.writeto(self.addr, b'\xFE')
        sleep(0.05)

    def read(self):
        """Lê temperatura (°C) e umidade relativa (%) do HDC1080."""
        self.i2c.writeto(self.addr, b'\x00')
        sleep(0.02)  # tempo de conversão
        data = self.i2c.readfrom(self.addr, 4)
        raw_temp = (data[0] << 8) | data[1]
        raw_hum  = (data[2] << 8) | data[3]
        temperature = (raw_temp / 65536.0) * 165.0 - 40.0
        humidity    = (raw_hum  / 65536.0) * 100.0
        return temperature, humidity