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
D     = 7           # Retraso discreto       [muestras]  = round(THETA / TS)

# ── Sintonización PID (criterio IAE – seguimiento de SP) ─
KC = 4.9574         # Ganancia proporcional  [%/psi]
TI = 0.0581         # Tiempo integral        [h]
TD = 0.0073         # Tiempo derivativo      [h]

# ── Restricciones del actuador ────────────────────────────
OP_MIN       = 0.0      # Cierre total      [%]
OP_MAX       = 100.0    # Apertura total    [%]
MAX_DELTA_OP = 5.0      # Máx. cambio por muestra (rate limiter) [%]

# ── Simulación ────────────────────────────────────────────
SIMULATION_DURATION_H = 2.0     # Duración de la simulación de prueba [h]
