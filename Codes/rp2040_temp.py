from machine import ADC

class Rp2040Temp:
    def __init__(self, vref=3.30, offset_c=0.0):
        self.adc = ADC(4)
        self.vref = vref
        self.offset_c = offset_c

    def read_c(self):
        v = self.adc.read_u16() * self.vref / 65535.0
        t = 27.0 - (v - 0.706) / 0.001721
        return t + self.offset_c

    def calibrate_to(self, ambient_c, samples=20):
        s = 0.0
        for _ in range(samples):
            v = self.adc.read_u16() * self.vref / 65535.0
            t = 27.0 - (v - 0.706) / 0.001721
            s += t
        avg = s / samples
        self.offset_c = ambient_c - avg
        return self.offset_c
