"""
Registrador de datos del lazo de control → archivo CSV.

Cada fila contiene: Timestamp, Time_h, Setpoint_psi, Pressure_psi, Valve_pct
"""

import csv
import os
from datetime import datetime
from typing import List, Tuple


class DataLogger:
    """Escribe datos del lazo de control a un archivo CSV y los mantiene
    en memoria para graficar al finalizar."""

    HEADER = ["Timestamp", "Time_h", "Setpoint_psi", "Pressure_psi", "Valve_pct"]

    def __init__(self, filepath: str):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        self._rows: List[Tuple[float, float, float, float]] = []
        self._file = open(filepath, "w", encoding="utf-8", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(self.HEADER)

    # ──────────────────────────────────────────────────
    def log(self, time_h: float, sp: float, pv: float, op: float) -> None:
        """Registra una fila de datos."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._writer.writerow([ts, f"{time_h:.6f}", f"{sp:.4f}", f"{pv:.4f}", f"{op:.4f}"])
        self._file.flush()
        self._rows.append((time_h, sp, pv, op))

    # ──────────────────────────────────────────────────
    def get_data(self) -> List[Tuple[float, float, float, float]]:
        """Retorna todos los datos registrados como lista de tuplas
        (time_h, sp, pv, op)."""
        return self._rows

    # ──────────────────────────────────────────────────
    def finalize(self) -> None:
        """Cierra el archivo CSV."""
        if not self._file.closed:
            self._file.close()
