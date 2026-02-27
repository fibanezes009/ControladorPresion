"""
Configuración de conexión al PLC Allen-Bradley vía Ethernet/IP (pylogix).
"""

# ── Conexión ──────────────────────────────────────────────
PLC_IP   = "192.168.185.6"
PLC_SLOT = 0

# ── Tags de lectura / escritura ───────────────────────────
PRESSURE_TAG    = "SAL_PRESION"                                 # Lectura: presión (psi)
VALVE_WRITE_TAG = "Program:MainProgram.VAPOR_SANITIZACION_HMI"  # Escritura: apertura válvula (%)
