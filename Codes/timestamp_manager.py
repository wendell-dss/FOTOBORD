# timestamp_manager.py
"""
Gerencia timestamp persistente entre resets do RP2040.
Salva o ultimo timestamp em arquivo para continuar de onde parou.
"""

import os
from time import ticks_ms

class TimestampManager:
    """Gerencia timestamp contínuo mesmo após resets."""
    
    TIMESTAMP_FILE = "last_timestamp.txt"
    
    def __init__(self):
        """Inicializa o gerenciador de timestamp."""
        self.start_ticks = ticks_ms()
        self.offset = self._load_last_timestamp()
        
        if self.offset > 0:
            print("AVISO - Sistema foi resetado!")
            print("  Ultimo timestamp: {:.2f}s ({:.2f}h)".format(
                self.offset, self.offset/3600))
            print("  Continuando a partir de: {:.2f}s".format(self.offset))
    
    def _load_last_timestamp(self):
        """Carrega o último timestamp salvo."""
        try:
            if self._file_exists(self.TIMESTAMP_FILE):
                with open(self.TIMESTAMP_FILE, "r") as f:
                    content = f.read().strip()
                    if content:
                        return float(content)
        except Exception as e:
            print("AVISO - Erro ao ler timestamp anterior: {}".format(e))
        
        return 0.0
    
    def _file_exists(self, filename):
        """Verifica se arquivo existe."""
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
    
    def get_timestamp(self):
        """
        Retorna timestamp atual em segundos.
        Continua de onde parou se houve reset.
        """
        elapsed = (ticks_ms() - self.start_ticks) / 1000.0
        return self.offset + elapsed
    
    def save_checkpoint(self, current_timestamp):
        """
        Salva checkpoint do timestamp atual.
        Chame periodicamente para não perder muito tempo em caso de reset.
        """
        try:
            with open(self.TIMESTAMP_FILE, "w") as f:
                f.write("{:.2f}".format(current_timestamp))
        except Exception as e:
            print("AVISO - Erro ao salvar checkpoint: {}".format(e))
    
    def reset(self):
        """
        Reseta o timestamp para zero.
        Use apenas se quiser começar uma nova medição do zero.
        """
        try:
            if self._file_exists(self.TIMESTAMP_FILE):
                os.remove(self.TIMESTAMP_FILE)
            self.offset = 0.0
            self.start_ticks = ticks_ms()
            print("Timestamp resetado para zero")
        except Exception as e:
            print("ERRO ao resetar timestamp: {}".format(e))