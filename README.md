# Controlador PID de Presión — Biorreactor

Controlador PID discreto de presión para un biorreactor industrial, comunicado vía Ethernet/IP con un PLC Allen-Bradley (CompactLogix/ControlLogix) usando **pylogix**.

## Descripción

El sistema lee la presión del reactor (`SAL_PRESION`) cada 10 segundos, ejecuta un algoritmo PID incremental con restricciones de actuador, y escribe la apertura de la válvula neumática de vapor (`VAPOR_SANITIZACION_HMI`) de vuelta al PLC.

### Modelo de planta identificado (FOPDT discreto)

| Parámetro | Valor | Unidad |
|---|---|---|
| Ganancia (K) | 0.6086 | psi/% |
| Constante de tiempo (τ) | 0.0995 | h |
| Tiempo muerto (θ) | 0.0200 | h |
| Retraso discreto (d) | 7 | muestras |

### Parámetros PID (sintonización IAE – set-point tracking)

| Parámetro | Valor | Unidad |
|---|---|---|
| Kc | 4.9574 | %/psi |
| Ti | 0.0581 | h |
| Td | 0.0073 | h |

## Estructura del proyecto

```
ControladorPresion/
├── config/                    # Configuración centralizada
│   ├── plc_config.py          # IP del PLC, tags de lectura/escritura
│   └── pid_config.py          # Parámetros del modelo, PID y restricciones
├── src/                       # Lógica de control
│   ├── plant_interface.py     # Interfaces: RealPLCInterface / SimulatedPlantInterface
│   ├── pid_controller.py      # Clase PIDController (incremental, anti-kick, rate limiter)
│   └── control_loop.py        # Orquestador del lazo cerrado
├── utils/                     # Utilidades
│   └── data_logger.py         # Logger CSV y buffer en memoria para graficar
├── data/                      # Archivos de salida (logs, gráficos)
├── Dev_notebooks/             # Archivos de desarrollo y datos experimentales
│   ├── AjusteFT_PID.ipynb     # Identificación de planta y sintonización PID
│   ├── Communication2.py      # Script original de comunicación con PLC
│   ├── SIP1.csv               # Datos experimentales de respuesta escalón 1
│   └── SIP2.csv               # Datos experimentales de respuesta escalón 2
├── main.py                    # Punto de entrada → PLC real
├── test_simulation.py         # Punto de entrada → planta simulada + gráfico
├── pyproject.toml             # Metadatos y dependencias del proyecto
├── requirements.txt           # Dependencias (pip install -r)
└── README.md
```

## Instalación

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno (Windows)
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# O con uv:
uv sync
```

## Uso

### Control con PLC real

```bash
python main.py
```

Lee `SAL_PRESION` y escribe `VAPOR_SANITIZACION_HMI` cada 10 s.  
Datos registrados en `data/plc_control_log.csv`. Detener con `Ctrl+C`.

### Test con planta simulada

```bash
# Ejecución instantánea (sin esperas) — para verificar el controlador
python test_simulation.py --fast

# Ejecución en tiempo real (10 s/paso, ~2 h de duración)
python test_simulation.py
```

Genera `data/test_simulation_log.csv` y `data/test_simulation_result.png`.

## Perfil de set-point de prueba

| Intervalo | Set-point (psi) |
|---|---|
| [0.0, 0.5) h | 15.0 |
| [0.5, 1.0) h | 20.0 |
| [1.0, 1.5) h | 10.0 |
| [1.5, 2.0] h | 2.5 |

## Características del controlador

- **Algoritmo PID incremental** (forma de velocidad)
- **Derivada sobre PV** (anti derivative-kick)
- **Rate limiter**: máximo 5 %/muestra en la válvula
- **Saturación**: apertura limitada entre 0 % y 100 %

## Dependencias principales

- `pylogix` — Comunicación Ethernet/IP con PLCs Allen-Bradley
- `numpy` — Cálculos numéricos
- `scipy` — Identificación del modelo de planta (curve_fit)
- `pandas` — Manejo de datos tabulares
- `matplotlib` — Visualización de resultados
