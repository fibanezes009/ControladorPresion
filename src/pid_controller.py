"""
Controlador PID discreto incremental con:
  - Acción derivativa sobre la PV (anti derivative-kick)
  - Rate-limiter en la salida
  - Saturación absoluta del actuador

Parámetros cargados desde config/pid_config.py.
"""

import json
import os

import numpy as np
from config.pid_config import KC, TI, TD, TS, OP_MIN, OP_MAX, MAX_DELTA_OP

STATE_FILE = "data/pid_state.json"


class PIDController:
    """PID discreto en forma de velocidad (incremental)."""

    def __init__(
        self,
        Kc: float = KC,
        Ti: float = TI,
        Td: float = TD,
        Ts: float = TS,
        op_min: float = OP_MIN,
        op_max: float = OP_MAX,
        max_delta_op: float = MAX_DELTA_OP,
    ):
        self.Kc = Kc
        self.Ti = Ti
        self.Td = Td
        self.Ts = Ts
        self.op_min = op_min
        self.op_max = op_max
        self.max_delta_op = max_delta_op

        # ── Estado interno ─────────────────────────────
        self._e_prev: float = 0.0       # error anterior  e[k-1]
        self._pv_prev1: float = 0.0     # PV anterior     pv[k-1]
        self._pv_prev2: float = 0.0     # PV hace 2 pasos pv[k-2]
        self._op_prev: float = 0.0      # salida anterior op[k-1]
        self._k: int = 0                # contador de pasos

    # ──────────────────────────────────────────────────
    def compute(self, sp: float, pv: float) -> float:
        """Calcula la nueva salida del controlador dado el set-point
        y la medición actual de presión.

        Parámetros
        ----------
        sp : float   Set-point [psi]
        pv : float   Variable de proceso (presión medida) [psi]

        Retorna
        -------
        float   Apertura de válvula [%]
        """
        self._k += 1
        e = sp - pv

        # ── Proporcional sobre el error ──
        delta_P = self.Kc * (e - self._e_prev)

        # ── Integral sobre el error ──
        delta_I = (self.Kc * self.Ts / self.Ti) * e

        # ── Derivativo sobre la PV (anti-kick) ──
        if self._k >= 2:
            delta_D = (self.Kc * self.Td / self.Ts) * (
                -pv + 2.0 * self._pv_prev1 - self._pv_prev2
            )
        else:
            delta_D = 0.0

        # ── Incremento total ──
        delta_op = delta_P + delta_I + delta_D

        # ── Rate limiter ──
        delta_op = float(np.clip(delta_op, -self.max_delta_op, self.max_delta_op))

        # ── Salida saturada ──
        op = float(np.clip(self._op_prev + delta_op, self.op_min, self.op_max))

        # ── Actualizar historia ──
        self._e_prev = e
        self._pv_prev2 = self._pv_prev1
        self._pv_prev1 = pv
        self._op_prev = op

        return op

    # ──────────────────────────────────────────────────
    def save_state(self, path: str = STATE_FILE) -> None:
        """Persiste las variables del pasado a disco (JSON)."""
        state = {
            "e_prev": self._e_prev,
            "pv_prev1": self._pv_prev1,
            "pv_prev2": self._pv_prev2,
            "op_prev": self._op_prev,
            "k": self._k,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    # ──────────────────────────────────────────────────
    def load_state(self, path: str = STATE_FILE) -> bool:
        """Restaura las variables del pasado desde disco.

        Retorna True si se restauró exitosamente, False si no había archivo."""
        if not os.path.exists(path):
            print("[PID] Sin estado previo. Iniciando desde cero.")
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._e_prev   = float(state.get("e_prev", 0.0))
            self._pv_prev1 = float(state.get("pv_prev1", 0.0))
            self._pv_prev2 = float(state.get("pv_prev2", 0.0))
            self._op_prev  = float(state.get("op_prev", 0.0))
            self._k        = int(state.get("k", 0))
            print(f"[PID] Estado restaurado: OP={self._op_prev:.2f}%, "
                  f"PV_prev={self._pv_prev1:.2f}, paso={self._k}")
            return True
        except Exception as e:
            print(f"[PID] Error al restaurar estado: {e}. Iniciando desde cero.")
            return False

    # ──────────────────────────────────────────────────
    def reset(self) -> None:
        """Reinicia el estado interno del controlador."""
        self._e_prev = 0.0
        self._pv_prev1 = 0.0
        self._pv_prev2 = 0.0
        self._op_prev = 0.0
        self._k = 0
