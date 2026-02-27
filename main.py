"""
Controlador PID de presión — Conexión con PLC real.

Lee SAL_PRESION del PLC cada 10 s, ejecuta el PID discreto
y escribe la apertura de válvula en VAPOR_SANITIZACION_HMI.

Uso:
    python main.py
    (Ctrl+C para detener; los datos quedan en data/plc_control_log.csv)
"""

from config.plc_config import PLC_IP, PLC_SLOT, PRESSURE_TAG, VALVE_WRITE_TAG
from config.pid_config import SAMPLE_TIME_SEC, SIMULATION_DURATION_H, TS
from src.plant_interface import RealPLCInterface
from src.control_loop import run_control_loop
from utils.data_logger import DataLogger


# ── Perfil de set-point (mismo que en AjusteFT_PID.ipynb) ──
def setpoint_fn(step: int, time_h: float) -> float:
    if time_h < 0.5:
        return 15.0
    elif time_h < 1.0:
        return 20.0
    elif time_h < 1.5:
        return 10.0
    else:
        return 2.5


def main():
    n_steps = int(SIMULATION_DURATION_H / TS)

    print("=" * 55)
    print(" Controlador PID de Presión — PLC Real")
    print("=" * 55)
    print(f" PLC           : {PLC_IP}")
    print(f" Tag lectura   : {PRESSURE_TAG}")
    print(f" Tag escritura : {VALVE_WRITE_TAG}")
    print(f" Muestreo      : {SAMPLE_TIME_SEC} s")
    print(f" Pasos totales : {n_steps}")
    print(f" Duración      : {SIMULATION_DURATION_H} h")
    print("=" * 55)
    print(" Presiona Ctrl+C para detener.\n")

    plant = RealPLCInterface(PLC_IP, PLC_SLOT, PRESSURE_TAG, VALVE_WRITE_TAG)
    logger = DataLogger("data/plc_control_log.csv")

    run_control_loop(
        plant=plant,
        setpoint_fn=setpoint_fn,
        n_steps=n_steps,
        sample_time_sec=SAMPLE_TIME_SEC,
        logger=logger,
        real_time=True,
    )

    print(f"\n[INFO] Datos guardados en: data/plc_control_log.csv")


if __name__ == "__main__":
    main()
