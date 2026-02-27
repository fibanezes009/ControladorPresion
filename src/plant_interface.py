"""
Interfaces de comunicación con la planta (PLC real y planta simulada).

Ambas implementaciones exponen la misma API para que el lazo de control
sea agnóstico al origen de los datos.
"""

from abc import ABC, abstractmethod
import numpy as np


class PlantInterface(ABC):
    """Contrato que debe cumplir cualquier fuente de datos de presión y
    sumidero de comando de válvula."""

    @abstractmethod
    def read_pressure(self) -> float:
        """Retorna la presión actual [psi]."""
        ...

    @abstractmethod
    def write_valve(self, value: float) -> None:
        """Envía el porcentaje de apertura de válvula [%]."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Libera recursos de comunicación."""
        ...


# ─────────────────────────────────────────────────────────
#  Implementación REAL — PLC Allen-Bradley vía pylogix
# ─────────────────────────────────────────────────────────
class RealPLCInterface(PlantInterface):
    """Lectura/escritura directa al PLC mediante Ethernet/IP (pylogix)."""

    def __init__(self, ip: str, slot: int, pressure_tag: str, valve_tag: str):
        from pylogix import PLC
        self._comm = PLC()
        self._comm.IPAddress = ip
        self._comm.ProcessorSlot = slot
        self._pressure_tag = pressure_tag
        self._valve_tag = valve_tag

    def read_pressure(self) -> float:
        result = self._comm.Read(self._pressure_tag)
        if getattr(result, "Status", None) == "Success":
            return float(result.Value)
        raise RuntimeError(
            f"Error de lectura PLC en '{self._pressure_tag}': {result.Status}"
        )

    def write_valve(self, value: float) -> None:
        result = self._comm.Write(self._valve_tag, float(value))
        if getattr(result, "Status", None) != "Success":
            raise RuntimeError(
                f"Error de escritura PLC en '{self._valve_tag}': {getattr(result, 'Status', 'Unknown')}"
            )

    def shutdown_valve(self) -> None:
        """Cierra la válvula a 0 % como medida de seguridad."""
        try:
            self._comm.Write(self._valve_tag, 0.0)
            print("[SEGURIDAD] Válvula cerrada a 0 %.")
        except Exception as e:
            print(f"[SEGURIDAD] ⚠ No se pudo cerrar la válvula: {e}")

    def close(self) -> None:
        self.shutdown_valve()
        self._comm.Close()


# ─────────────────────────────────────────────────────────
#  Implementación SIMULADA — Modelo FOPDT discreto
# ─────────────────────────────────────────────────────────
class SimulatedPlantInterface(PlantInterface):
    """Planta virtual basada en el modelo discreto identificado:

        y[k] = a·y[k-1] + b·u[k-d-1]

    donde  a = exp(-Ts/τ),  b = K·(1-a),  d = round(θ/Ts).
    """

    def __init__(self, K: float, tau: float, theta: float, Ts: float):
        self.a = np.exp(-Ts / tau)
        self.b = K * (1.0 - self.a)
        self.d = int(np.round(theta / Ts))   # retraso entero [muestras]

        self._pv: float = 0.0                # presión actual
        self._op_history: list[float] = []   # historial de comandos de válvula
        self._step: int = 0

    def read_pressure(self) -> float:
        return self._pv

    def write_valve(self, value: float) -> None:
        self._op_history.append(float(value))
        idx = self._step - self.d - 1
        u_delayed = self._op_history[idx] if idx >= 0 else 0.0
        self._pv = self.a * self._pv + self.b * u_delayed
        self._step += 1

    def close(self) -> None:
        pass  # nada que liberar
