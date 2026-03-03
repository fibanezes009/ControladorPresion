"""
Controlador PID discreto incremental con:
  - Acción derivativa sobre la PV (anti derivative-kick)
  - Filtro de primer orden en el derivativo (N configurable)
  - Anti-windup por back-calculation (compensa saturación)
  - Rate-limiter de DOS ZONAS:
      · |error| >= ERROR_BAND → clip a ±MAX_DELTA_OP (10 %)
      · |error| <  ERROR_BAND → PID libre (sin restricción)
  - Saturación absoluta del actuador (0-100 %)

Parámetros cargados desde config/pid_config.py.
"""

import json
import os

import numpy as np
from config.pid_config import (KC, TI, TD, TS, OP_MIN, OP_MAX,
                                MAX_DELTA_OP, ERROR_BAND,
                                TRACKING_TC, DERIV_FILTER_N)

STATE_FILE = "data/pid_state.json"


class PIDController:
    """PID discreto en forma de velocidad (incremental) con anti-windup
    y filtro derivativo."""

    def __init__(
        self,
        Kc: float = KC,
        Ti: float = TI,
        Td: float = TD,
        Ts: float = TS,
        op_min: float = OP_MIN,
        op_max: float = OP_MAX,
        max_delta_op: float = MAX_DELTA_OP,
        error_band: float = ERROR_BAND,
        tracking_tc: float = TRACKING_TC,
        deriv_filter_n: int = DERIV_FILTER_N,
    ):
        self.Kc = Kc
        self.Ti = Ti
        self.Td = Td
        self.Ts = Ts
        self.op_min = op_min
        self.op_max = op_max
        self.max_delta_op = max_delta_op
        self.error_band = error_band
        self.tracking_tc = tracking_tc if tracking_tc > 0 else Ti
        self.deriv_filter_n = deriv_filter_n

        # ── Estado interno ─────────────────────────────
        self._e_prev: float = 0.0          # error anterior  e[k-1]
        self._pv_prev1: float = 0.0        # PV anterior     pv[k-1]
        self._D_filtered: float = 0.0      # derivativo filtrado (posición)
        self._op_prev: float = 0.0         # salida anterior  op[k-1]
        self._sat_error: float = 0.0       # (u_actual - u_deseado) de paso anterior
        self._k: int = 0                   # contador de pasos

        # ── Diagnóstico (último cálculo) ───────────────
        self.last_delta_raw: float = 0.0      # delta PID sin recortar
        self.last_delta_applied: float = 0.0  # delta tras rate limiter
        self.last_rate_limited: bool = False   # True si fue recortado
        self.last_effective_limit: float = max_delta_op  # límite efectivo usado

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

        # ── Integral sobre el error + corrección anti-windup ──
        # Back-calculation: el término (Ts/Tt)*sat_error reduce la
        # acumulación integral cuando el RL o la saturación recortaron
        # el paso anterior.
        delta_I_base = (self.Kc * self.Ts / self.Ti) * e
        aw_correction = (self.Ts / self.tracking_tc) * self._sat_error
        delta_I = delta_I_base + aw_correction

        # ── Derivativo filtrado sobre la PV (anti-kick) ──
        # Filtro de primer orden: D[k] = c1·D[k-1] + c2·(PV[k-1] - PV[k])
        # En forma de velocidad: delta_D = D[k] - D[k-1]
        if self._k >= 2:
            N = self.deriv_filter_n
            denom = self.Td + N * self.Ts
            c1 = self.Td / denom
            c2 = self.Kc * self.Td * N / denom
            D_new = c1 * self._D_filtered + c2 * (self._pv_prev1 - pv)
            delta_D = D_new - self._D_filtered
            self._D_filtered = D_new
        else:
            delta_D = 0.0

        # ── Incremento total ──
        delta_raw = delta_P + delta_I + delta_D

        # ── Rate limiter (dos zonas) ──
        # Lejos del SP (|error| >= error_band): clip a ±max_delta_op (10 %)
        #   → previene movimientos violentos de la válvula.
        # Cerca del SP (|error| < error_band): PID sin restricción.
        #   → evita ciclos límite por recorte repetitivo.
        if abs(e) >= self.error_band:
            limit = self.max_delta_op
            delta_op = float(np.clip(delta_raw, -limit, limit))
        else:
            limit = float('inf')
            delta_op = float(delta_raw)

        # ── Diagnóstico ──
        self.last_delta_raw = float(delta_raw)
        self.last_delta_applied = delta_op
        self.last_rate_limited = (limit < float('inf')) and (abs(delta_raw) > self.max_delta_op + 1e-8)
        self.last_effective_limit = self.max_delta_op if limit < float('inf') else 999.0

        # ── Salida saturada ──
        op = float(np.clip(self._op_prev + delta_op, self.op_min, self.op_max))

        # ── Anti-windup: error de saturación para el siguiente paso ──
        # sat_error = (lo que se aplicó) - (lo que se quería)
        # Negativo cuando se recortó en dirección positiva;
        # Positivo cuando se recortó en dirección negativa.
        actual_delta = op - self._op_prev
        self._sat_error = actual_delta - delta_raw

        # ── Actualizar historia ──
        self._e_prev = e
        self._pv_prev1 = pv
        self._op_prev = op

        return op

    # ──────────────────────────────────────────────────
    def save_state(self, path: str = STATE_FILE) -> None:
        """Persiste las variables del pasado a disco (JSON)."""
        state = {
            "e_prev": self._e_prev,
            "pv_prev1": self._pv_prev1,
            "D_filtered": self._D_filtered,
            "op_prev": self._op_prev,
            "sat_error": self._sat_error,
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
            self._e_prev      = float(state.get("e_prev", 0.0))
            self._pv_prev1    = float(state.get("pv_prev1", 0.0))
            self._D_filtered  = float(state.get("D_filtered", 0.0))
            self._op_prev     = float(state.get("op_prev", 0.0))
            self._sat_error   = float(state.get("sat_error", 0.0))
            self._k           = int(state.get("k", 0))
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
        self._D_filtered = 0.0
        self._op_prev = 0.0
        self._sat_error = 0.0
        self._k = 0
