"""
Test del controlador PID con planta simulada (modelo FOPDT discreto).

Ejecuta el mismo perfil de set-point usado en AjusteFT_PID.ipynb:

    [0.0, 0.5) h  →  15   psi
    [0.5, 1.0) h  →  20   psi
    [1.0, 1.5) h  →  10   psi
    [1.5, 2.0] h  →   2.5 psi

Cada paso se ejecuta cada 10 s (tiempo real) o de forma instantánea
con la bandera --fast.

Al finalizar (o al presionar Ctrl+C), genera el gráfico de comparación
SP vs PV y apertura de válvula, idéntico al del notebook.

Uso:
    python test_simulation.py           # Tiempo real (≈ 2 h)
    python test_simulation.py --fast    # Sin esperas  (instantáneo)
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config.pid_config import (
    K, TAU, THETA, TS,
    SAMPLE_TIME_SEC, SIMULATION_DURATION_H,
)
from src.plant_interface import SimulatedPlantInterface
from src.control_loop import run_control_loop
from utils.data_logger import DataLogger


# ─────────────────────────────────────────────────────────
#  Perfil de set-point en forma de DataFrame
# ─────────────────────────────────────────────────────────
def build_setpoint_dataframe() -> pd.DataFrame:
    """Construye un DataFrame con las columnas (time_h, setpoint_psi)
    usando el mismo perfil escalonado del notebook."""
    t = np.arange(0, SIMULATION_DURATION_H, TS)
    sp = np.zeros_like(t)
    sp[t < 0.5] = 15.0
    sp[(t >= 0.5) & (t < 1.0)] = 20.0
    sp[(t >= 1.0) & (t < 1.5)] = 10.0
    sp[t >= 1.5] = 2.5
    return pd.DataFrame({"time_h": t, "setpoint_psi": sp})


# ─────────────────────────────────────────────────────────
#  Gráfico de resultados
# ─────────────────────────────────────────────────────────
def plot_results(data, title="PID Discreto (IAE) con Límites de Válvula y Anti-Kick"):
    """Genera el mismo gráfico doble (SP/PV + válvula) que el notebook."""
    if not data:
        print("[WARN] No hay datos para graficar.")
        return

    time_h = [r[0] for r in data]
    sp     = [r[1] for r in data]
    pv     = [r[2] for r in data]
    op     = [r[3] for r in data]

    plt.style.use("ggplot")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    # ── Presión vs Set-point ──
    ax1.step(time_h, sp, "r--", where="post", label="Set-point")
    ax1.step(time_h, pv, "b-",  where="post", label="Presión (PV)")
    ax1.set_ylabel("Pressure (psi)")
    ax1.set_title(title)
    ax1.legend()

    # ── Apertura de válvula ──
    ax2.step(time_h, op, "g-", where="post", label="Válvula Neumática (OP)")
    ax2.set_ylabel("Apertura (%)")
    ax2.set_xlabel("Time (h)")
    ax2.legend()

    plt.tight_layout()
    plt.savefig("data/test_simulation_result.png", dpi=150)
    print("[INFO] Gráfico guardado en: data/test_simulation_result.png")
    plt.show()


# ─────────────────────────────────────────────────────────
#  Punto de entrada
# ─────────────────────────────────────────────────────────
def main():
    fast_mode = "--fast" in sys.argv

    # 1. Construir perfil de set-point
    df = build_setpoint_dataframe()
    n_steps = len(df)
    sp_array = df["setpoint_psi"].values

    # 2. Información en consola
    print("=" * 55)
    print(" Test de Simulación — Controlador PID de Presión")
    print("=" * 55)
    print(f" Modo          : {'RÁPIDO (sin esperas)' if fast_mode else 'TIEMPO REAL (10 s/paso)'}")
    print(f" Pasos totales : {n_steps}")
    print(f" Duración sim. : {SIMULATION_DURATION_H} h")
    if not fast_mode:
        print(f" Duración real : {n_steps * SAMPLE_TIME_SEC / 3600:.1f} h")
    print(f" Set-point     : 15 → 20 → 10 → 2.5 psi")
    print("=" * 55)
    print(" Presiona Ctrl+C para detener y generar gráfico.\n")

    # 3. Crear planta simulada y logger
    plant  = SimulatedPlantInterface(K, TAU, THETA, TS)
    logger = DataLogger("data/test_simulation_log.csv")

    # 4. Función de set-point (indexa el DataFrame)
    def setpoint_fn(step: int, time_h: float) -> float:
        if step < len(sp_array):
            return float(sp_array[step])
        return float(sp_array[-1])

    # 5. Ejecutar lazo de control
    logger = run_control_loop(
        plant=plant,
        setpoint_fn=setpoint_fn,
        n_steps=n_steps,
        sample_time_sec=SAMPLE_TIME_SEC,
        logger=logger,
        real_time=not fast_mode,
        persist_state=False,        # Simulación: no persistir estado a disco
    )

    # 6. Resultados
    print(f"\n[INFO] Datos guardados en : data/test_simulation_log.csv")
    print(f"[INFO] Total de muestras : {len(logger.get_data())}")
    plot_results(logger.get_data())


if __name__ == "__main__":
    main()
