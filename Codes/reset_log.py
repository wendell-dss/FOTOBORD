"""
reset_log.py - Registro de causas de reset
-------------------------------------------
Registra a causa do reset do sistema de forma segura,
compatível com diferentes versões do MicroPython.
"""

import machine
from time import localtime

class ResetLogger:
    """Registra a causa do último reset do sistema."""
    
    def __init__(self, filename="reset_log.txt"):
        self.filename = filename
        self._log_reset()
    
    def get_reset_cause_name(self):
        """Retorna o nome da causa do reset de forma segura."""
        try:
            cause = machine.reset_cause()
            
            # Mapeamento dos códigos numéricos para nomes
            causes = {
                0: 'PWRON_RESET',      # Power-on reset
                1: 'HARD_RESET',       # Hard reset
                2: 'WDT_RESET',        # Watchdog reset
                3: 'DEEPSLEEP_RESET',  # Deep sleep reset
                4: 'SOFT_RESET',       # Soft reset (Ctrl+D)
            }
            
            return causes.get(cause, 'UNKNOWN({})'.format(cause))
        except Exception as e:
            return 'UNAVAILABLE (erro: {})'.format(e)
    
    def _log_reset(self):
        """Registra a causa do reset no arquivo."""
        try:
            cause_name = self.get_reset_cause_name()
            
            # Pega timestamp atual (pode não ser preciso se RTC não configurado)
            try:
                t = localtime()
                timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    t[0], t[1], t[2], t[3], t[4], t[5])
            except:
                timestamp = "N/A"
            
            # Escreve no arquivo
            with open(self.filename, 'a') as f:
                f.write("{} | Reset: {}\n".format(timestamp, cause_name))
            
            print("Reset registrado: {}".format(cause_name))
            
        except Exception as e:
            print("AVISO - Não foi possível registrar reset: {}".format(e))
    
    def read_log(self, max_lines=20):
        """Lê as últimas entradas do log de reset."""
        try:
            with open(self.filename, 'r') as f:
                lines = f.readlines()
            
            # Retorna as últimas max_lines linhas
            return lines[-max_lines:] if len(lines) > max_lines else lines
            
        except OSError:
            print("Arquivo de log não encontrado")
            return []
        except Exception as e:
            print("Erro ao ler log: {}".format(e))
            return []
    
    def clear_log(self):
        """Limpa o arquivo de log de reset."""
        try:
            with open(self.filename, 'w') as f:
                f.write("=== Log de Reset Limpo ===\n")
            print("Log de reset limpo")
        except Exception as e:
            print("Erro ao limpar log: {}".format(e))
    
    def print_log(self, max_lines=20):
        """Imprime as últimas entradas do log."""
        lines = self.read_log(max_lines)
        if lines:
            print("\n=== Últimos {} Resets ===".format(len(lines)))
            for line in lines:
                print(line.strip())
            print("=" * 40)
        else:
            print("Nenhum reset registrado")