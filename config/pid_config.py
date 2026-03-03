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

# ── Rate limiter (dos zonas) ──────────────────────────────
# Cuando |error| >= ERROR_BAND  →  clip a ±MAX_DELTA_OP  (10 %)
#   Evita movimientos violentos de la válvula lejos del SP.
# Cuando |error| <  ERROR_BAND  →  PID libre, sin restricción.
#   Evita ciclos límite inducidos por recorte repetitivo cerca del SP.
MAX_DELTA_OP = 10.0     # Máx. cambio por muestra [%] (lejos de SP)
ERROR_BAND   = 5.0      # Umbral [psi]: RL activo si |error| >= este valor

# ── Anti-windup (back-calculation) ────────────────────────
# Constante de tiempo de tracking: controla qué tan rápido el anti-windup
# corrige la acumulación integral cuando el RL o la saturación recortan.
# Valor típico: Tt = Ti (moderado) o Tt = sqrt(Ti·Td) (agresivo).
TRACKING_TC  = TI       # Constante de tracking [h]  (Tt = Ti)

# ── Filtro derivativo ─────────────────────────────────────
# Coeficiente N del filtro de primer orden en el término derivativo.
# Limita la ganancia de alta frecuencia a Kc·N.
# Valores típicos: 5-20 (estándar industrial: 10).
DERIV_FILTER_N = 10     # Coeficiente del filtro derivativo

# ── Simulación ────────────────────────────────────────────
SIMULATION_DURATION_H = 2.0     # Duración de la simulación de prueba [h]
