"""
ina_sensor.py
--------------
Módulo para leitura de tensão, corrente e potência usando o INA219.
Permite inversão de polaridade e filtragem simples (média móvel).

Autor: [Seu nome]
Data: [data de hoje]
"""

from time import sleep
from ina219 import INA219


class Ina219Sensor:
    """
    Classe encapsulando o sensor INA219 com boas práticas.
    """

    def __init__(self, i2c, addr=0x40, rshunt=0.1, invert_polarity=False):
        """
        Inicializa o sensor INA219.
        :param i2c: instância de machine.I2C
        :param addr: endereço I2C do sensor (default 0x40)
        :param rshunt: resistência do shunt em ohms
        :param invert_polarity: se True, inverte o sinal da corrente/potência
        """
        self._ina = INA219(i2c, addr)
        self._rshunt = rshunt
        self._invert = invert_polarity

        # Configuração padrão: 16V / 400mA para melhor resolução
        self._ina.set_calibration_16V_400mA()

    def read(self):
        """
        Realiza uma leitura completa do sensor.
        :return: dict com tensão, corrente, potência e Vshunt
        """
        vbus = self._ina.bus_voltage
        vshunt = self._ina.shunt_voltage
        current = self._ina.current

        if self._invert:
            vshunt *= -1
            current *= -1

        power = vbus * current

        return {
            "vbus": vbus,
            "vshunt": vshunt,
            "current": current,
            "power": power
        }

    def average(self, n=5, delay=0.05):
        """
        Faz média móvel de n leituras para reduzir ruído.
        :param n: número de amostras
        :param delay: intervalo entre amostras (s)
        :return: dict médio das grandezas
        """
        sums = {"vbus": 0, "vshunt": 0, "current": 0, "power": 0}

        for _ in range(n):
            data = self.read()
            for k in sums:
                sums[k] += data[k]
            sleep(delay)

        return {k: v / n for k, v in sums.items()}
