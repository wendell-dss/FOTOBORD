# main.py
"""
Sistema de monitoramento de bateria com RP2040
-----------------------------------------------
Versao FINAL otimizada com:
- Tratamento robusto de erros
- Rotacao automatica de arquivos
- Gerenciamento de memoria
- Watchdog para reinicio automatico
- Timestamp persistente entre resets
- Timing preciso (exatamente 1 amostra/segundo)
"""

from machine import I2C, Pin, ADC, WDT
from time import sleep, ticks_ms
from ina_sensor import Ina219Sensor
from data_logger import DataLogger
from battery_gauge import BatteryGauge
from rp2040_temp import Rp2040Temp
from hdc1080_sensor import HDC1080
from timestamp_manager import TimestampManager
import gc
from reset_log import ResetLogger

reset_logger = ResetLogger()

# =============================================================================
# CONFIGURACOES
# =============================================================================

LED_PIN = 25
VREF = 3.30
R1 = 470_000.0
R2 = 330_000.0
DIV_GAIN = (R1 + R2) / R2
CAL_FACTOR = 1.052
BOOST_ETA = 0.90
BATTERY_CAPACITY_MAH = 15000

# Intervalo entre leituras (segundos)
SAMPLE_INTERVAL = 60.0  # Exatamente 1 segundo entre amostras

# Intervalo para liberar memoria (numero de amostras)
GC_INTERVAL = 100

# Intervalo para mostrar estatisticas (numero de amostras)
STATS_INTERVAL = 500

# WATCHDOG: Timeout em milissegundos
WATCHDOG_TIMEOUT_MS = 60000

# Otimizacoes de leitura para timing preciso
INA_SAMPLES = 3  # Reduzido de 5 para 3 (mais rapido)
INA_DELAY = 0.01  # Reduzido de 0.02 para 0.01

# =============================================================================
# INICIALIZACAO
# =============================================================================

print("\n" + "="*60)
print("SISTEMA DE MONITORAMENTO - VERSAO FINAL OTIMIZADA")
print("="*60 + "\n")

# Watchdog
print("Inicializando Watchdog...")
try:
    wdt = WDT(timeout=WATCHDOG_TIMEOUT_MS)
    print("OK - Watchdog habilitado (timeout: {}ms)".format(WATCHDOG_TIMEOUT_MS))
except Exception as e:
    print("AVISO - Watchdog nao disponivel: {}".format(e))
    wdt = None

# LED de status
led = Pin(LED_PIN, Pin.OUT)
led.off()

# INA219
print("Inicializando INA219...")
try:
    i2c_ina = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
    ina = Ina219Sensor(i2c_ina, invert_polarity=True)
    print("OK - INA219")
except Exception as e:
    print("ERRO ao inicializar INA219: {}".format(e))
    if wdt:
        print("Aguardando watchdog reiniciar...")
        while True:
            sleep(1)
    raise

# HDC1080
print("Inicializando HDC1080...")
try:
    i2c_hdc = I2C(1, scl=Pin(15), sda=Pin(14), freq=100_000)
    hdc = HDC1080(i2c_hdc)
    print("OK - HDC1080")
except Exception as e:
    print("AVISO - HDC1080 nao disponivel: {}".format(e))
    hdc = None

# ADC bateria
print("Inicializando ADC da bateria...")
adc_batt = ADC(26)
print("OK - ADC")

# Sensor temperatura interno
print("Inicializando sensor interno...")
temp = Rp2040Temp(vref=VREF, offset_c=0.0)
print("OK - Sensor interno")

# Battery gauge
print("Inicializando battery gauge...")
gauge = BatteryGauge(capacity_mAh=BATTERY_CAPACITY_MAH)
gauge._inited = False
gauge.soc = None
print("OK - Battery gauge")

# Data logger
print("Inicializando data logger...")
logger = DataLogger("ina_log", max_lines=15000)
print("OK - Data logger")

# Timestamp manager
print("Inicializando timestamp manager...")
ts_manager = TimestampManager()
print("OK - Timestamp manager\n")

if wdt:
    wdt.feed()

# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

def read_vbatt():
    """Le tensao real da bateria."""
    raw = adc_batt.read_u16()
    v_adc = VREF * raw / 65535.0
    return v_adc * DIV_GAIN * CAL_FACTOR

def blink_error(times=3):
    """Pisca LED para indicar erro."""
    for _ in range(times):
        led.on()
        sleep(0.1)
        led.off()
        sleep(0.1)

def print_stats(sample_count, error_count, ts, wdt_feeds, avg_loop_time):
    """Imprime estatisticas do sistema."""
    stats = logger.get_stats()
    hours = ts / 3600
    
    print("\n" + "="*60)
    print("ESTATISTICAS DO SISTEMA")
    print("="*60)
    print("Tempo decorrido: {:.2f} horas ({:.2f} dias)".format(hours, hours/24))
    print("Amostras capturadas: {}".format(sample_count))
    print("Taxa real: {:.3f} Hz (esperado: 1.000 Hz)".format(1.0/avg_loop_time if avg_loop_time > 0 else 0))
    print("Tempo medio de loop: {:.3f}s".format(avg_loop_time))
    print("Arquivo atual: {}".format(stats['arquivo_atual']))
    print("Linhas no arquivo: {}/{}".format(stats['linhas_arquivo'], logger.max_lines))
    print("Total de arquivos: {}".format(stats['total_arquivos']))
    print("Total de linhas: {}".format(stats['linhas_totais']))
    print("Erros: {}".format(error_count))
    print("Memoria livre: {} bytes".format(gc.mem_free()))
    if wdt:
        print("Watchdog alimentado: {} vezes".format(wdt_feeds))
    print("="*60 + "\n")

def safe_i2c_read(sensor_func, sensor_name, default_value):
    """Le sensor I2C com protecao."""
    try:
        if wdt:
            wdt.feed()
        result = sensor_func()
        return result
    except OSError as e:
        print("AVISO - Erro I2C em {}: {}".format(sensor_name, e))
        return default_value
    except Exception as e:
        print("AVISO - Erro em {}: {}".format(sensor_name, e))
        return default_value

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

print("timestamp | Vbatt[V] | Vload[V] | Iload[mA] | Ibatt_est[mA] | SoC[%] | Temp_int[C] | Temp_ext[C] | Hum[%] | Loop[s]")
print("-" * 130)

# Contadores
error_count = 0
sample_count = 0
consecutive_errors = 0
wdt_feeds = 0
MAX_CONSECUTIVE_ERRORS = 10

# Timing
loop_times = []
MAX_LOOP_TIMES = 50  # Manter ultimos 50 loops para calcular media

while True:
    loop_start = ticks_ms()
    
    try:
        # Alimentar watchdog
        if wdt:
            wdt.feed()
            wdt_feeds += 1
        
        led.on()
        
        # --- Leituras do INA (otimizado: 3 amostras x 0.01s) ---
        def read_ina():
            return ina.average(n=INA_SAMPLES, delay=INA_DELAY)
        
        d = safe_i2c_read(read_ina, "INA219", 
                         {'vbus': 0.0, 'current': 0.0, 'vshunt': 0.0, 'power': 0.0})
        
        Vload = d['vbus']
        Iload_mA = d['current']

        # --- Leitura da bateria ---
        Vbatt = read_vbatt()

        # --- Corrente da bateria estimada ---
        if Vbatt < 2.5:
            Ibatt_mA = 0.0
        else:
            Ibatt_mA = (Vload * Iload_mA) / (BOOST_ETA * Vbatt)

        # --- Tempo e temperatura interna ---
        ts = ts_manager.get_timestamp()
        TempC_int = temp.read_c()

        # --- HDC1080 ---
        if hdc is not None:
            def read_hdc():
                return hdc.read()
            
            result = safe_i2c_read(read_hdc, "HDC1080", (float('nan'), float('nan')))
            TempC_ext, Humidity = result
        else:
            TempC_ext, Humidity = float('nan'), float('nan')

        # --- Estado de carga ---
        SoC = gauge.update(voltage_V=Vbatt, current_mA=Ibatt_mA, now_s=ts)

        # --- Gravacao ---
        row = {
            "timestamp": ts,
            "Vbatt": Vbatt,
            "Vload": Vload,
            "Iload_mA": Iload_mA,
            "Ibatt_mA": Ibatt_mA,
            "SoC": SoC,
            "Temp_int": TempC_int,
            "Temp_ext": TempC_ext,
            "Humidity": Humidity
        }

        logger.append(row)
        sample_count += 1
        consecutive_errors = 0
        
        # Calcular tempo do loop
        loop_time = (ticks_ms() - loop_start) / 1000.0
        loop_times.append(loop_time)
        if len(loop_times) > MAX_LOOP_TIMES:
            loop_times.pop(0)
        avg_loop_time = sum(loop_times) / len(loop_times)
        
        # --- Exibicao ---
        print("{:8.2f} | {:7.3f} | {:7.3f} | {:9.3f} | {:11.3f} | {:6.2f} | {:10.2f} | {:10.2f} | {:6.2f} | {:5.3f}".format(
            ts, Vbatt, Vload, Iload_mA, Ibatt_mA, SoC, TempC_int, TempC_ext, Humidity, loop_time))
        
        # Avisar se loop demorou muito
        if loop_time > 1.5:
            print("AVISO - Loop demorou {:.2f}s (esperado: <1.0s)".format(loop_time))

        # --- Gerenciamento de memoria ---
        if sample_count % GC_INTERVAL == 0:
            gc.collect()
            if wdt:
                wdt.feed()
            ts_manager.save_checkpoint(ts)
            print("GC: {} bytes | Checkpoint: {:.2f}h | Loop medio: {:.3f}s".format(
                gc.mem_free(), ts/3600, avg_loop_time))
        
        # --- Estatisticas periodicas ---
        if sample_count % STATS_INTERVAL == 0:
            print_stats(sample_count, error_count, ts, wdt_feeds, avg_loop_time)
            if wdt:
                wdt.feed()
        
        led.off()
        
        # --- SLEEP AJUSTADO PARA TIMING PRECISO ---
        # Calcular quanto tempo ja passou no loop
        elapsed = (ticks_ms() - loop_start) / 1000.0
        
        # Calcular quanto tempo falta para completar SAMPLE_INTERVAL
        sleep_time = SAMPLE_INTERVAL - elapsed
        
        # Garantir sleep minimo de 0.05s
        sleep_time = max(0.05, sleep_time)
        
        if wdt:
            wdt.feed()
        
        sleep(sleep_time)
        
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuario")
        ts_manager.save_checkpoint(ts_manager.get_timestamp())
        print_stats(sample_count, error_count, ts_manager.get_timestamp(), wdt_feeds, avg_loop_time)
        break
        
    except Exception as e:
        error_count += 1
        consecutive_errors += 1
        
        print("\nERRO #{} (consecutivos: {}): {}".format(error_count, consecutive_errors, e))
        
        if wdt:
            wdt.feed()
        
        blink_error()
        
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            print("ERRO CRITICO: {} erros consecutivos!".format(MAX_CONSECUTIVE_ERRORS))
            
            if wdt:
                print("Watchdog vai reiniciar o sistema...")
                while True:
                    blink_error(1)
                    sleep(1)
            else:
                blink_error(10)
                sleep(10)
                consecutive_errors = 0
        else:
            sleep(2)
        
        continue

print("\nSistema finalizado.")