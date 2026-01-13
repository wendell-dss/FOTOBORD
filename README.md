# Sistema de Monitoramento de Bateria com RP2040

[![MicroPython](https://img.shields.io/badge/MicroPython-1.20+-blue.svg)](https://micropython.org/)
[![Hardware](https://img.shields.io/badge/Hardware-RP2040-green.svg)](https://www.raspberrypi.com/documentation/microcontrollers/rp2040.html)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema embarcado para monitoramento contínuo de baterias em aplicações IoT com energia solar, desenvolvido para o projeto de monitoramento agrícola com armadilhas inteligentes para pragas (Spodoptera frugiperda).

## 📋 Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Hardware Necessário](#hardware-necessário)
- [Instalação](#instalação)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Configuração](#configuração)
- [Uso](#uso)
- [Formato dos Dados](#formato-dos-dados)
- [Troubleshooting](#troubleshooting)
- [Características Técnicas](#características-técnicas)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

## 🎯 Sobre o Projeto

Este sistema faz parte de uma solução IoT para monitoramento agrícola inteligente, focado em armadilhas para captura de *Spodoptera frugiperda* (lagarta-do-cartucho) em plantações. O firmware do RP2040 é responsável por:

- Monitorar tensão, corrente e estado de carga (SoC) da bateria
- Registrar temperatura e umidade do ambiente
- Gerenciar energia do sistema alimentado por painel solar
- Garantir operação contínua com detecção e recuperação automática de falhas
- Armazenar dados persistentes mesmo após resets do sistema

### Sistema Completo

O sistema embarcado integra-se a uma infraestrutura maior:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA COMPLETO DE CAMPO                     │
├─────────────────────────────────────────────────────────────────┤
│  Painel Solar → Regulador → Bateria → MPPT → RP2040 (este FW)  │
│                                          ↓                        │
│                                    Câmera + Sensores            │
│                                          ↓                        │
│                                    Mini-Computador              │
│                                          ↓                        │
│                              Processamento de Imagens           │
│                                          ↓                        │
│                                      Servidor                    │
└─────────────────────────────────────────────────────────────────┘
```

## 🏗️ Arquitetura do Sistema

### Diagrama de Camadas

```
┌────────────────────────────────────────────────────────────────┐
│              CAMADA DE CONTROLE PRINCIPAL                       │
│                      main.py                                    │
│              (Orquestrador do sistema)                          │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│         CAMADA DE INTERFACE COM SENSORES                        │
├──────────────────┬────────────────────┬────────────────────────┤
│  ina_sensor.py   │ hdc1080_sensor.py  │   rp2040_temp.py      │
│  (INA219 I2C)    │ (Temp + Umidade)   │  (Sensor Interno)     │
│       ↓          │                    │                        │
│  ina219.py       │                    │                        │
│  (Driver)        │                    │                        │
└──────────────────┴────────────────────┴────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│        CAMADA DE PROCESSAMENTO DE DADOS                         │
├──────────────────┬────────────────────┬────────────────────────┤
│ battery_gauge.py │timestamp_manager.py│   reset_log.py        │
│ (Coulomb Count)  │ (Tempo persistente)│  (Diagnóstico)        │
└──────────────────┴────────────────────┴────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│           CAMADA DE ARMAZENAMENTO                               │
├──────────────────────────────┬─────────────────────────────────┤
│      data_logger.py          │   Arquivos Persistentes         │
│  (Rotação automática CSV)    │  • last_timestamp.txt          │
│  → ina_log_000.csv           │  • reset_log.txt               │
│  → ina_log_001.csv           │                                 │
│  → ...                       │                                 │
└──────────────────────────────┴─────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                  CAMADA DE HARDWARE                             │
├──────────┬──────────┬──────────────┬──────────────────────────┤
│  INA219  │ HDC1080  │ ADC Bateria  │    Temp Interno          │
│ I2C 0x40 │ I2C 0x40 │   ADC26      │       ADC4               │
│ GPIO 8,9 │GPIO 14,15│ Div R1/R2    │   RP2040 built-in        │
└──────────┴──────────┴──────────────┴──────────────────────────┘
```

## 🔧 Hardware Necessário

### Componentes Principais

| Componente | Especificação | Função |
|------------|---------------|--------|
| **Microcontrolador** | RP2040 (Raspberry Pi Pico) | Controle e aquisição de dados |
| **Sensor de Corrente** | INA219 (I2C @ 0x40) | Medição de tensão e corrente |
| **Sensor Temp/Umidade** | HDC1080 (I2C @ 0x40) | Monitoramento ambiental |
| **Bateria** | Li-ion 1S 15000mAh (3.0-4.2V) | Armazenamento de energia |
| **Divisor Resistivo** | R1=470kΩ, R2=330kΩ | Medição de tensão da bateria |
| **Painel Solar** | Conforme necessidade | Fonte primária de energia |
| **MPPT** | Regulador de tensão | Otimização da carga solar |

### Pinagem do RP2040

```python
# I2C para INA219
SDA_INA = GPIO 8
SCL_INA = GPIO 9

# I2C para HDC1080  
SDA_HDC = GPIO 14
SCL_HDC = GPIO 15

# ADC
ADC_BATERIA = GPIO 26 (ADC0)
TEMP_INTERNO = ADC4 (interno do RP2040)

# Status
LED = GPIO 25
```

### Esquemático Simplificado

```
Bateria (3.0-4.2V)
    │
    ├──[R1=470kΩ]──┬──[R2=330kΩ]──GND
    │              │
    │          GPIO26 (ADC)
    │
    ├── INA219 ── Load (MPPT/Sistema)
    │
    └── RP2040 ── HDC1080 ── Ambiente
```

## 📦 Instalação

### 1. Instalar Thonny IDE

O Thonny é a forma mais simples de programar o Raspberry Pi Pico com MicroPython.

**Windows/Linux/macOS:**
- Download: [https://thonny.org/](https://thonny.org/)
- Instale normalmente seguindo o assistente

### 2. Instalar MicroPython no Raspberry Pi Pico

**Método 1 - Via Thonny (Recomendado):**

1. Conecte o Raspberry Pi Pico ao computador **segurando o botão BOOTSEL**
2. O Pico aparecerá como um drive USB chamado "RPI-RP2"
3. Abra o Thonny
4. Clique no canto inferior direito onde diz "Python" e selecione **"MicroPython (Raspberry Pi Pico)"**
5. Se aparecer uma mensagem oferecendo instalar o MicroPython, clique em **"Install"**
6. Aguarde a instalação (o Pico reiniciará automaticamente)

**Método 2 - Manual:**

1. Baixe o firmware: [https://micropython.org/download/rp2-pico/](https://micropython.org/download/rp2-pico/)
2. Segure BOOTSEL e conecte o Pico via USB
3. Copie o arquivo `.uf2` para o drive "RPI-RP2"
4. O Pico reiniciará automaticamente com MicroPython

### 3. Baixar o Projeto

```bash
git clone https://github.com/seu-usuario/battery-monitor-rp2040.git
cd battery-monitor-rp2040
```

Ou baixe o ZIP direto do GitHub e extraia.

### 4. Transferir Arquivos para o Pico via Thonny

1. Abra o Thonny
2. Certifique-se que o Pico está conectado e reconhecido (canto inferior direito)
3. No menu: **View → Files** (ou Ctrl+F3)
4. Você verá dois painéis:
   - **Este computador** (lado esquerdo)
   - **Raspberry Pi Pico** (lado direito)

5. Navegue até a pasta do projeto no lado esquerdo
6. Selecione **todos os arquivos .py**:
   - `main.py`
   - `ina219.py`
   - `ina_sensor.py`
   - `hdc1080_sensor.py`
   - `rp2040_temp.py`
   - `battery_gauge.py`
   - `timestamp_manager.py`
   - `data_logger.py`
   - `reset_log.py`

7. Clique com botão direito → **"Upload to /"**
8. Aguarde a transferência completar

**Estrutura esperada no Pico:**
```
/ (raiz do Pico)
├── main.py
├── ina219.py
├── ina_sensor.py
├── hdc1080_sensor.py
├── rp2040_temp.py
├── battery_gauge.py
├── timestamp_manager.py
├── data_logger.py
└── reset_log.py
```

### 5. Verificar Instalação

1. No Thonny, clique no botão **"Stop/Restart backend"** (ícone vermelho)
2. O Pico reiniciará e executará `main.py` automaticamente
3. Você verá a saída no console inferior do Thonny

**Teste rápido no Shell do Thonny:**

```python
>>> from machine import Pin
>>> led = Pin(25, Pin.OUT)
>>> led.on()   # LED deve acender
>>> led.off()  # LED deve apagar
```

### Métodos Alternativos (Avançado)

Se preferir usar linha de comando:

**Via ampy:**
```bash
pip install adafruit-ampy
ampy --port /dev/ttyACM0 put *.py
```

**Via rshell:**
```bash
pip install rshell
rshell -p /dev/ttyACM0
> cp *.py /pyboard/
```

**Via mpremote (mais recente):**
```bash
pip install mpremote
mpremote connect /dev/ttyACM0 fs cp *.py :
```

## 📁 Estrutura de Arquivos

```
battery-monitor-rp2040/
│
├── main.py                    # Loop principal e orquestração
├── ina219.py                  # Driver baixo nível INA219 (MIT License)
├── ina_sensor.py              # Wrapper do INA219 com média móvel
├── hdc1080_sensor.py          # Driver HDC1080
├── rp2040_temp.py             # Sensor de temperatura interno
├── battery_gauge.py           # Algoritmo de coulomb counting + OCV
├── timestamp_manager.py       # Gerenciamento de tempo persistente
├── data_logger.py             # Sistema de logging com rotação
├── reset_log.py               # Registro de causas de reset
│
├── README.md                  # Este arquivo
├── LICENSE                    # Licença MIT
└── examples/                  # Exemplos de uso
    ├── calibrate_adc.py       # Calibração do ADC da bateria
    ├── test_sensors.py        # Teste individual dos sensores
    └── analyze_logs.py        # Script Python para análise dos CSVs
```

## ⚙️ Configuração

### Parâmetros Principais (main.py)

```python
# Intervalo de amostragem
SAMPLE_INTERVAL = 60.0        # segundos (1 amostra/segundo)

# Capacidade da bateria
BATTERY_CAPACITY_MAH = 15000  # mAh

# Calibração do divisor resistivo
R1 = 470_000.0                # Ohms
R2 = 330_000.0                # Ohms
CAL_FACTOR = 1.052            # Fator de correção (ajustar com voltímetro)

# Eficiência do boost converter
BOOST_ETA = 0.90              # 90%

# Watchdog
WATCHDOG_TIMEOUT_MS = 60000   # 60 segundos

# Gerenciamento de memória
GC_INTERVAL = 100             # Liberar RAM a cada 100 amostras
STATS_INTERVAL = 500          # Mostrar estatísticas a cada 500 amostras
```

### Calibração do ADC da Bateria

```python
# 1. Medir tensão real da bateria com voltímetro de precisão
# 2. Executar o sistema e verificar a leitura
# 3. Calcular fator de correção:
CAL_FACTOR = Tensao_Real / Tensao_Medida

# Exemplo:
# Voltímetro: 3.756V
# Sistema lê: 3.572V
# CAL_FACTOR = 3.756 / 3.572 = 1.052
```

### Ajuste da Curva OCV (battery_gauge.py)

```python
# Curva de tensão de circuito aberto (OCV) para Li-ion 1S
# Ajustar conforme as características da bateria usada
self.ocv_points = [
    (4.00,  100.0),  # (Tensão [V], SoC [%])
    (3.95,  95.0),
    (3.90,  90.0),
    # ... adicionar mais pontos conforme necessário
    (2.90,   0.0),
]
```

## 🚀 Uso

### Iniciar o Sistema via Thonny

1. **Abra o Thonny** e conecte o Raspberry Pi Pico
2. Certifique-se que está em **"MicroPython (Raspberry Pi Pico)"** (canto inferior direito)
3. Clique no botão **"Stop/Restart backend"** (ícone vermelho com X)
4. O arquivo `main.py` será executado automaticamente
5. A saída aparecerá no console inferior do Thonny

**Atalhos úteis no Thonny:**
- **F5** - Executar o script atual
- **Ctrl+F2** - Stop/Restart (reiniciar sistema)
- **Ctrl+D** - Soft reset (no Shell)

### Monitoramento em Tempo Real

O console do Thonny mostrará a saída contínua:

```
============================================================
SISTEMA DE MONITORAMENTO - VERSAO FINAL OTIMIZADA
============================================================

Inicializando Watchdog...
OK - Watchdog habilitado (timeout: 60000ms)
Inicializando INA219...
OK - INA219
Inicializando HDC1080...
OK - HDC1080
...
```

### Executar Sem o Thonny (Standalone)

Após transferir os arquivos, o Pico executará `main.py` automaticamente ao ser energizado:

1. Desconecte o Pico do computador
2. Conecte a uma fonte de alimentação externa (USB ou bateria)
3. O sistema iniciará automaticamente
4. Dados serão salvos nos arquivos CSV na memória interna

### Baixar Dados Coletados via Thonny

1. No Thonny: **View → Files** (Ctrl+F3)
2. No painel **"Raspberry Pi Pico"** (direita), você verá:
   ```
   ├── main.py
   ├── ina_log_000.csv  ← Dados coletados
   ├── ina_log_001.csv
   ├── last_timestamp.txt
   └── reset_log.txt
   ```
3. **Clique com botão direito** nos arquivos CSV → **"Download to..."**
4. Escolha a pasta no seu computador para salvar

### Visualizar Dados em Tempo Real (Thonny)

No Shell do Thonny, você pode interagir com o sistema:

```python
# Parar o sistema temporariamente
>>> # Pressione Ctrl+C no console

# Ver estatísticas do logger
>>> logger.get_stats()
{'arquivo_atual': 'ina_log_000.csv', 'linhas_arquivo': 1523, ...}

# Ver últimos resets
>>> reset_logger.print_log()

# Continuar a execução
>>> # Pressione Ctrl+D ou clique em "Run"
```

### Saída Esperada

```
============================================================
SISTEMA DE MONITORAMENTO - VERSAO FINAL OTIMIZADA
============================================================

Inicializando Watchdog...
OK - Watchdog habilitado (timeout: 60000ms)
Inicializando INA219...
OK - INA219
Inicializando HDC1080...
OK - HDC1080
Inicializando ADC da bateria...
OK - ADC
Inicializando sensor interno...
OK - Sensor interno
Inicializando battery gauge...
OK - Battery gauge
Inicializando data logger...
Espaco total: 1024.0 KB
Espaco usado: 256.3 KB
Espaco livre: 767.7 KB
Estimativa: ~12800 linhas (~4.3h)
Novo arquivo criado: ina_log_000.csv
OK - Data logger
Inicializando timestamp manager...
OK - Timestamp manager

timestamp | Vbatt[V] | Vload[V] | Iload[mA] | Ibatt_est[mA] | SoC[%] | Temp_int[C] | Temp_ext[C] | Hum[%] | Loop[s]
----------------------------------------------------------------------------------------------------------------------------------
    0.00 |   3.756 |   5.012 |   123.456 |      165.432 |  87.34 |      27.45 |      25.67 |  65.43 | 0.234
    1.00 |   3.754 |   5.010 |   122.987 |      164.891 |  87.32 |      27.46 |      25.68 |  65.44 | 0.235
```

### Parar o Sistema

```python
# Ctrl+C no terminal serial
# O sistema salvará automaticamente o último timestamp

# Ou via código:
# 1. Pressionar Ctrl+C
# 2. Sistema imprime estatísticas finais
# 3. Salva checkpoint do timestamp
```

## 📊 Formato dos Dados

### Arquivo CSV (ina_log_XXX.csv)

```csv
timestamp,Vbatt[V],Vload[V],Iload[mA],Ibatt_est[mA],SoC[%],Temp_int[C],Temp_ext[C],Humidity[%]
0.00,3.756,5.012,123.456,165.432,87.34,27.45,25.67,65.43
1.00,3.754,5.010,122.987,164.891,87.32,27.46,25.68,65.44
```

| Campo | Unidade | Descrição |
|-------|---------|-----------|
| `timestamp` | segundos | Tempo desde o início da medição |
| `Vbatt[V]` | Volts | Tensão da bateria |
| `Vload[V]` | Volts | Tensão na carga (saída do boost) |
| `Iload[mA]` | miliamperes | Corrente consumida pela carga |
| `Ibatt_est[mA]` | miliamperes | Corrente estimada da bateria |
| `SoC[%]` | porcentagem | Estado de carga da bateria (0-100%) |
| `Temp_int[C]` | Celsius | Temperatura interna do RP2040 |
| `Temp_ext[C]` | Celsius | Temperatura ambiente (HDC1080) |
| `Humidity[%]` | porcentagem | Umidade relativa do ar |

### Rotação Automática de Arquivos

- Cada arquivo CSV armazena até **15.000 linhas** (~4 horas @ 1 Hz)
- Novos arquivos são criados automaticamente: `ina_log_000.csv`, `ina_log_001.csv`, etc.
- Sistema alerta quando espaço em disco está baixo (<50KB)

### Arquivos Auxiliares

#### last_timestamp.txt
```
3600.45
```
Armazena o último timestamp em segundos. Permite continuar a contagem após resets.

#### reset_log.txt
```
2025-01-19 10:23:45 | Reset: WDT_RESET
2025-01-19 14:56:12 | Reset: SOFT_RESET
```
Registra todas as causas de reset do sistema para diagnóstico.

## 🔍 Troubleshooting

### Problema: Sistema não inicia

**Sintomas:** LED não pisca, sem saída no console do Thonny

**Soluções:**

1. **Verificar porta no Thonny:**
   - Canto inferior direito → Clique em "MicroPython (Raspberry Pi Pico)"
   - Verifique se a porta COM/USB correta está selecionada
   - Tente "Configure interpreter..." → Detectar porta automaticamente

2. **Reinstalar MicroPython:**
   - Clique em "Configure interpreter..."
   - Clique em "Install or update MicroPython"
   - Siga o assistente

3. **Verificar alimentação:**
   - LED verde do Pico deve estar aceso (indica alimentação OK)
   - Tensão USB deve ser ~5V
   - Se usando bateria: mínimo 2.7V

4. **Teste básico no Shell do Thonny:**
   ```python
   >>> from machine import Pin
   >>> led = Pin(25, Pin.OUT)
   >>> led.on()  # LED deve acender
   >>> led.off() # LED deve apagar
   ```

5. **Verificar arquivos transferidos:**
   - View → Files (Ctrl+F3)
   - Confirme que `main.py` está na raiz do Pico
   - Arquivo não pode ter erros de sintaxe

### Problema: Erro de I2C

**Sintomas:** 
```
AVISO - Erro I2C em INA219: [Errno 5] EIO
```

**Soluções:**

1. **Verificar conexões físicas:**
   - SDA e SCL bem conectados
   - Alimentação 3.3V nos sensores
   - GND comum entre Pico e sensores

2. **Testar endereços I2C no Shell do Thonny:**
   ```python
   >>> from machine import I2C, Pin
   >>> i2c0 = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)
   >>> print(i2c0.scan())  # INA219
   [64]  # Deve retornar [64] para endereço 0x40
   
   >>> i2c1 = I2C(1, scl=Pin(15), sda=Pin(14), freq=100000)
   >>> print(i2c1.scan())  # HDC1080
   [64]  # Deve retornar [64] para endereço 0x40
   ```

3. **Verificar se há conflito de endereços:**
   - INA219 e HDC1080 usam **barramentos I2C diferentes**
   - INA219: I2C0 (GPIO 8, 9)
   - HDC1080: I2C1 (GPIO 14, 15)

4. **Adicionar pull-ups (se necessário):**
   - Resistores de 4.7kΩ entre SDA/SCL e 3.3V
   - Geralmente não necessário para distâncias curtas (<30cm)

5. **Reduzir frequência I2C:**
   - Em `main.py`, alterar:
   ```python
   # De:
   i2c_ina = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
   # Para:
   i2c_ina = I2C(0, sda=Pin(8), scl=Pin(9), freq=100000)
   ```

### Problema: Leituras erradas da bateria

**Sintomas:** Tensão muito diferente do voltímetro

**Soluções:**
1. Recalibrar `CAL_FACTOR` em `main.py`
2. Verificar divisor resistivo (R1/R2)
3. Medir VREF com multímetro:

```python
from machine import ADC
adc = ADC(26)
# Aplicar 3.3V no GPIO26
# Deve ler próximo de 65535
```

### Problema: Disco cheio

**Sintomas:** 
```
*** ERRO CRITICO: Espaco em disco MUITO baixo! ***
```

**Soluções via Thonny:**

1. **Visualizar espaço usado:**
   - View → Files (Ctrl+F3)
   - Veja o tamanho dos arquivos no painel direito

2. **Deletar CSVs antigos:**
   - **Método 1 (Interface):**
     - Clique com botão direito no arquivo
     - "Delete"
   
   - **Método 2 (Shell):**
     ```python
     >>> import os
     >>> os.listdir()  # Ver todos os arquivos
     >>> os.remove('ina_log_000.csv')  # Deletar arquivo específico
     ```

3. **Antes de deletar, fazer backup:**
   - Clique com botão direito → "Download to..."
   - Salve no seu computador
   - Depois delete do Pico

4. **Deletar múltiplos arquivos (Shell):**
   ```python
   >>> import os
   >>> for f in os.listdir():
   ...     if f.startswith('ina_log_') and f.endswith('.csv'):
   ...         os.remove(f)
   ...         print(f'Deletado: {f}')
   ```

5. **Verificar espaço disponível:**
   ```python
   >>> import os
   >>> st = os.statvfs('/')
   >>> free_kb = (st[0] * st[3]) / 1024
   >>> print(f'Espaço livre: {free_kb:.1f} KB')
   ```

### Problema: Watchdog reinicia o sistema

**Sintomas:** Resets frequentes, `reset_log.txt` mostra `WDT_RESET`

**Soluções:**
1. Aumentar `WATCHDOG_TIMEOUT_MS`
2. Verificar travamentos no código
3. Adicionar mais `wdt.feed()` se loops demorarem muito

### Problema: SoC incorreto

**Sintomas:** Estado de carga não corresponde à tensão

**Soluções:**
1. Ajustar curva OCV em `battery_gauge.py`
2. Calibrar com bateria totalmente carregada (4.2V = 100%)
3. Verificar parâmetros:

```python
# battery_gauge.py
capacity_mAh=15000,           # Capacidade real da bateria
rest_current_thresh_C=0.02,   # Threshold de repouso
blend_alpha=0.05              # Velocidade de correção OCV
```

## 📈 Características Técnicas

### Desempenho

- **Taxa de amostragem:** 1 Hz (exatamente 1 amostra/segundo)
- **Tempo de loop típico:** ~0.23s
- **Resolução de corrente:** 0.05 mA (INA219 @ 16V/400mA)
- **Resolução de tensão:** 4 mV (INA219)
- **Precisão de temperatura:** ±0.2°C (HDC1080)
- **Precisão de umidade:** ±2% RH (HDC1080)

### Consumo de Energia

- **RP2040 ativo:** ~30 mA @ 3.3V
- **INA219:** ~1 mA
- **HDC1080:** ~90 µA (modo ativo)
- **Total estimado:** ~32-35 mA

### Limites Operacionais

| Parâmetro | Mínimo | Típico | Máximo | Unidade |
|-----------|--------|--------|--------|---------|
| Tensão bateria | 2.7 | 3.7 | 4.2 | V |
| Corrente carga | 0 | 150 | 400 | mA |
| Temperatura operação | -10 | 25 | 60 | °C |
| Umidade relativa | 0 | 50 | 95 | % |

### Robustez

- ✅ **Watchdog timer:** Reinício automático em caso de travamento
- ✅ **Detecção de resets:** Sistema continua operação após falhas
- ✅ **Timestamp persistente:** Não perde contagem de tempo
- ✅ **Rotação de logs:** Evita overflow de memória
- ✅ **Gerenciamento de memória:** Garbage collection automático
- ✅ **Tratamento de erros I2C:** Continua operando com sensores faltando
- ✅ **Verificação de espaço:** Alerta antes de disco encher

## 🧪 Validação e Testes

### Teste de Bancada Recomendado

```python
# 1. Teste de sensores individuais
python examples/test_sensors.py

# 2. Calibração do ADC
python examples/calibrate_adc.py

# 3. Teste de carga/descarga
# - Carregar bateria até 4.2V
# - Executar sistema
# - Verificar SoC = 100%
# - Descarregar com carga conhecida
# - Verificar coulomb counting
```

### Análise de Dados

```python
# Script Python para análise offline (PC)
import pandas as pd
import matplotlib.pyplot as plt

# Ler CSV
df = pd.read_csv('ina_log_000.csv')

# Plotar SoC vs Tempo
plt.plot(df['timestamp']/3600, df['SoC[%]'])
plt.xlabel('Tempo (horas)')
plt.ylabel('Estado de Carga (%)')
plt.title('Descarga da Bateria')
plt.grid(True)
plt.show()

# Calcular energia consumida
energia_Wh = (df['Ibatt_est[mA]'] * df['Vbatt[V]'] / 1000).sum() / 3600
print(f'Energia total: {energia_Wh:.2f} Wh')
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Diretrizes

- Manter compatibilidade com MicroPython 1.20+
- Documentar novas funções com docstrings
- Adicionar exemplos de uso
- Testar em hardware real antes de submeter

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

O driver `ina219.py` é baseado no trabalho de Dean Miller (Adafruit Industries) e mantém a licença MIT original.

## 👥 Autores

- **Wendell dos Santos Silva** - *Desenvolvimento inicial* - Universidade Federal do Ceará (UFC)

## 🙏 Agradecimentos

- Adafruit Industries pelo driver INA219
- Comunidade MicroPython
- Projeto de pesquisa em agricultura de precisão - UFC
- Prof. Dra. Atslands Rego da Rocha
- Prof. Dra Deborah Maria Vieira Magalhães

## 📞 Contato

- **Projeto:** Sistema de Monitoramento Agrícola Inteligente
- **Instituição:** Universidade Federal do Ceará
- **Email:** wendellsantos@alu.ufc.br

---

**Nota:** Este sistema é parte de um projeto maior de IoT para agricultura de precisão. Para mais informações sobre o sistema completo (câmera, processamento de imagens, servidor), consulte a documentação principal do projeto.
