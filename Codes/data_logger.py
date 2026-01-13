# data_logger.py
import os

class DataLogger:
    """
    Gerencia o registro de dados em arquivo CSV com rotacao automatica.
    Cria multiplos arquivos para evitar limites de memoria.
    """
    def __init__(self, base_filename="ina_log", max_lines=15000):
        """
        Inicializa o logger com rotacao automatica de arquivos.
        
        Args:
            base_filename: nome base dos arquivos (ex: "ina_log")
            max_lines: numero maximo de linhas por arquivo antes de rotacionar
        """
        self.base_filename = base_filename
        self.max_lines = max_lines
        self.current_file_index = 0
        self.line_count = 0
        
        # Encontrar o proximo arquivo disponivel
        while self._exists(self._get_filename()):
            self.current_file_index += 1
        
        self._create_new_file()
        self._print_disk_info()

    def _get_filename(self):
        """Retorna o nome do arquivo atual com indice."""
        return "{:s}_{:03d}.csv".format(self.base_filename, self.current_file_index)

    def _exists(self, filename):
        """Verifica se o arquivo ja existe na memoria."""
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def _print_disk_info(self):
        """Imprime informacoes sobre espaco em disco disponivel."""
        try:
            statvfs = os.statvfs('/')
            block_size = statvfs[0]
            total_blocks = statvfs[2]
            free_blocks = statvfs[3]
            
            total_kb = (block_size * total_blocks) / 1024
            free_kb = (block_size * free_blocks) / 1024
            used_kb = total_kb - free_kb
            
            print("Espaco total: {:.1f} KB".format(total_kb))
            print("Espaco usado: {:.1f} KB".format(used_kb))
            print("Espaco livre: {:.1f} KB".format(free_kb))
            
            # Estimar quantas linhas ainda cabem
            avg_line_size = 60  # bytes por linha
            lines_remaining = (free_kb * 1024) / avg_line_size
            hours_remaining = (lines_remaining * 1.2) / 3600  # assumindo ~1.2s/amostra
            
            print("Estimativa: ~{:.0f} linhas (~{:.1f}h)".format(lines_remaining, hours_remaining))
            
        except Exception as e:
            print("AVISO - Nao foi possivel verificar espaco: {}".format(e))

    def _create_new_file(self):
        """Cria novo arquivo CSV e grava o cabecalho inicial."""
        self.filename = self._get_filename()
        header = (
            "timestamp,"
            "Vbatt[V],"
            "Vload[V],"
            "Iload[mA],"
            "Ibatt_est[mA],"
            "SoC[%],"
            "Temp_int[C],"
            "Temp_ext[C],"
            "Humidity[%]\n"
        )
        try:
            with open(self.filename, "w") as f:
                f.write(header)
            self.line_count = 0
            print("Novo arquivo criado: {}".format(self.filename))
        except Exception as e:
            print("ERRO ao criar arquivo: {}".format(e))
            raise

    def append(self, data):
        """
        Adiciona uma linha de dados no CSV.
        Rotaciona arquivo automaticamente quando atinge max_lines.
        
        Args:
            data: dicionario com os dados a serem gravados
        """
        try:
            # VERIFICAR ESPACO EM DISCO ANTES DE GRAVAR
            if self.line_count % 100 == 0:  # Verificar a cada 100 linhas
                statvfs = os.statvfs('/')
                free_kb = (statvfs[0] * statvfs[3]) / 1024
                
                if free_kb < 50:  # Menos de 50KB livres
                    print("*** ERRO CRITICO: Espaco em disco MUITO baixo! ***")
                    print("*** Apenas {:.1f} KB livres ***".format(free_kb))
                    print("*** Sistema vai PARAR de gravar! ***")
                    print("*** Apague CSVs antigos URGENTE! ***")
                    return  # NAO gravar para nao travar o sistema
                elif free_kb < 200:
                    print("AVISO - Pouco espaco: {:.1f} KB".format(free_kb))
            
            # Verificar se precisa rotacionar arquivo
            if self.line_count >= self.max_lines:
                print("Rotacionando arquivo ({} linhas)...".format(self.line_count))
                self.current_file_index += 1
                self._create_new_file()
            
            with open(self.filename, "a") as f:
                line = (
                    "{:.2f},"
                    "{:.3f},"
                    "{:.3f},"
                    "{:.3f},"
                    "{:.3f},"
                    "{:.2f},"
                    "{:.2f},"
                    "{:.2f},"
                    "{:.2f}\n"
                ).format(
                    data['timestamp'],
                    data['Vbatt'],
                    data['Vload'],
                    data['Iload_mA'],
                    data['Ibatt_mA'],
                    data['SoC'],
                    data['Temp_int'],
                    data['Temp_ext'],
                    data['Humidity']
                )
                f.write(line)
            
            self.line_count += 1
            
        except OSError as e:
            # Erro de I/O - provavelmente disco cheio
            print("*** ERRO CRITICO ao gravar CSV: {} ***".format(e))
            print("*** Provavel causa: Disco cheio! ***")
            # Nao levanta excecao para nao parar o sistema
        except Exception as e:
            print("AVISO - Erro ao gravar CSV: {}".format(e))
            # Nao levanta excecao para nao parar o logging
    
    def get_stats(self):
        """Retorna estatisticas do logger."""
        return {
            "arquivo_atual": self.filename,
            "linhas_arquivo": self.line_count,
            "total_arquivos": self.current_file_index + 1,
            "linhas_totais": (self.current_file_index * self.max_lines) + self.line_count
        }