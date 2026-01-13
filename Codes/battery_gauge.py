# battery_gauge.py
import time

def lerp(x0, y0, x1, y1, x):
    if x <= x0: return y0
    if x >= x1: return y1
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)

class BatteryGauge:
    """
    SoC por coulomb counting + correcao por OCV (Li-ion 1S).
    - Inicializa o SoC pela OCV na 1a atualizacao (evita "queda" artificial).
    - So aplica OCV quando corrente de bateria for muito baixa (repouso).
    - DETECTA RESETS e ajusta automaticamente (compativel com timestamp_manager)
    """
    def __init__(self,
                 capacity_mAh=15000.0,
                 soc_init=None,             # None => auto pelo OCV na 1a medicao
                 v_full=3.75,
                 v_empty=2.90,
                 rest_current_thresh_C=0.02,  # repouso: |I| < C/50 (mais rigido)
                 blend_alpha=0.05):           # OCV puxa devagar
        self.capacity_mAh = capacity_mAh
        self.soc = soc_init
        self.v_full = v_full
        self.v_empty = v_empty
        self.C = capacity_mAh
        self.rest_thresh_mA = rest_current_thresh_C * self.C
        self.blend_alpha = blend_alpha
        self._last_t = None
        self._inited = False
        
        # NOVO: Para detectar saltos de tempo (resets)
        self._max_reasonable_dt = 10.0  # segundos (se dt > 10s, provavelmente resetou)

        # Curva OCV (aprox. Li-ion 1S @25C)
        self.ocv_points = [
            (4.00,  100.0),
            (3.95,  95.0),
            (3.90,  90.0),
            (3.85,  85.0),
            (3.80,  80.0),
            (3.75,  75.0),
            (3.70,  70.0),
            (3.60,  65.0),
            (3.50,  60.0),
            (3.40,  50.0),
            (3.30,  40.0),
            (3.20,  30.0),
            (3.10,  20.0),
            (3.05,  10.0),
            (2.95,   5.0),
            (2.90,   0.0),
        ]

    def _soc_from_ocv(self, v):
        pts = sorted(self.ocv_points, key=lambda p: p[0])
        for i in range(len(pts) - 1):
            v0, s0 = pts[i]
            v1, s1 = pts[i+1]
            if v0 <= v <= v1:
                return lerp(v0, s0, v1, s1, v)
        if v <= pts[0][0]: return pts[0][1]
        return pts[-1][1]

    def update(self, voltage_V, current_mA, now_s=None):
        # Tempo robusto
        t = now_s if now_s is not None else (time.ticks_ms() / 1000.0)

        # 1a passada: inicializar pelo OCV
        if not self._inited or self.soc is None:
            self.soc = self._soc_from_ocv(voltage_V)
            self._last_t = t
            self._inited = True
            return self.soc

        dt_s = t - (self._last_t or t)
        
        # NOVO: DETECTAR RESET DE TEMPO
        # Se dt_s for muito grande (>10s) ou negativo, provavelmente houve reset
        if dt_s < 0 or dt_s > self._max_reasonable_dt:
            print("AVISO - Battery gauge detectou salto de tempo!")
            print("  dt = {:.2f}s (esperado: ~1s)".format(dt_s))
            print("  Provavel causa: reset do sistema ou pause longo")
            print("  Reinicializando gauge pelo OCV...")
            
            # Reinicializar pelo OCV em vez de usar coulomb counting
            self.soc = self._soc_from_ocv(voltage_V)
            self._last_t = t
            return self.soc
        
        # Garantir dt positivo e razoavel
        dt_s = max(0.0, min(dt_s, self._max_reasonable_dt))
        self._last_t = t

        # Coulomb counting
        dQ_mAh = (current_mA * dt_s) / 3600.0      # mA*s -> mAh
        soc_cc = self.soc - 100.0 * (dQ_mAh / self.capacity_mAh)

        # Regras de ancoragem (tensao extrema)
        if voltage_V >= (self.v_full - 0.02):
            soc_cc = max(soc_cc, 99.0)
        if voltage_V <= (self.v_empty + 0.02):
            soc_cc = min(soc_cc, 1.0)

        # OCV apenas em repouso verdadeiro (corrente muito baixa)
        use_ocv = abs(current_mA) <= self.rest_thresh_mA
        if use_ocv:
            soc_ocv = self._soc_from_ocv(voltage_V)
            soc_new = (1.0 - self.blend_alpha) * soc_cc + self.blend_alpha * soc_ocv
        else:
            soc_new = soc_cc

        self.soc = max(0.0, min(100.0, soc_new))
        return self.soc