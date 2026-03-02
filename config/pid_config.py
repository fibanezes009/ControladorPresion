"""
Parámetros del controlador PID y modelo de planta.

Identificados experimentalmente en AjusteFT_PID.ipynb a partir de
la respuesta escalón de la válvula neumática de vapor → presión.
"""

# ── Muestreo ──────────────────────────────────────────────
SAMPLE_TIME_SEC = 10            # Periodo de muestreo [s]
TS = SAMPLE_TIME_SEC / 3600     # Periodo de muestreo [h]

# ── Modelo de planta (FOPDT discreto) ────────────────────
K     = 0.6086      # Ganancia estática      [psi/%]
TAU   = 0.0995      # Constante de tiempo    [h]
THETA = 0.0200      # Tiempo muerto          [h]
# Retraso discreto: d = round(THETA / TS) = 7 muestras
# (calculado automáticamente en SimulatedPlantInterface)

# ── Sintonización PID (criterio IAE – seguimiento de SP) ─
KC = 4.9574         # Ganancia proporcional  [%/psi]
TI = 0.0581         # Tiempo integral        [h]
TD = 0.0073         # Tiempo derivativo      [h]

# ── Restricciones del actuador ────────────────────────────
OP_MIN       = 0.0      # Cierre total      [%]
OP_MAX       = 100.0    # Apertura total    [%]
MAX_DELTA_OP = 5.0      # Máx. cambio por muestra (rate limiter) [%]

# ── Rate limiter dinámico ─────────────────────────────────
# Cuando |error| < ERROR_BAND, el rate limit se reduce proporcionalmente:
#   effective_limit = MAX_DELTA_OP × max(|error|/ERROR_BAND, MIN_RL_FRAC)
# Ejemplo: error=0.5 psi → limit = 5 × max(0.5/2, 0.1) = 1.25%
ERROR_BAND   = 2.0      # Banda de error para escalado [psi]
MIN_RL_FRAC  = 0.10     # Fracción mínima del rate limiter (10%)

# ── Simulación ────────────────────────────────────────────
SIMULATION_DURATION_H = 2.0     # Duración de la simulación de prueba [h]
