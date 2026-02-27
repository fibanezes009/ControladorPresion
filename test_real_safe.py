"""
Prueba segura del PID contra el PLC real.

  - Set-point fijo y bajo (5 psi)
  - Solo 30 pasos (5 minutos)
  - Límite de apertura de válvula (30 %)
  - Al terminar (o Ctrl+C), cierra la válvula a 0 %

Uso:
    python test_real_safe.py
"""

import time
import matplotlib.pyplot as plt
from pylogix import PLC

from config.plc_config import PLC_IP, PRESSURE_TAG, VALVE_WRITE_TAG
from config.pid_config import SAMPLE_TIME_SEC
from src.pid_controller import PIDController
from utils.data_logger import DataLogger

# ── Parámetros de la prueba segura ────────────────────────
SETPOINT_PSI = 5.0          # Presión objetivo baja y segura
N_STEPS      = 30           # 30 pasos × 10 s = 5 minutos
VALVE_LIMIT  = 30.0         # Protección: máximo 30 % de apertura


def main() -> None:
    print("=" * 55)
    print(" PRUEBA SEGURA — PID vs PLC Real")
    print("=" * 55)
    print(f" Set-point      : {SETPOINT_PSI} psi")
    print(f" Pasos          : {N_STEPS}  ({N_STEPS * SAMPLE_TIME_SEC / 60:.0f} min)")
    print(f" Límite válvula : {VALVE_LIMIT} %")
    print(f" PLC IP         : {PLC_IP}")
    print("=" * 55)
    input(" Presiona ENTER para iniciar (Ctrl+C para abortar)... ")

    pid    = PIDController()
    logger = DataLogger("data/test_real_safe_log.csv")
    data: list[tuple[float, float, float, float]] = []

    try:
        for step in range(N_STEPS):
            t_h = step * SAMPLE_TIME_SEC / 3600.0

            # 1. LEER presión del PLC
            with PLC() as comm:
                comm.IPAddress = PLC_IP
                ret = comm.Read(PRESSURE_TAG)
                if ret.Status != "Success":
                    print(f"\n[ERROR] Lectura fallida: {ret.Status}")
                    break
                pv = float(ret.Value)

            # 2. CALCULAR acción del PID
            op = pid.compute(SETPOINT_PSI, pv)

            # 3. PROTECCIÓN: limitar apertura máxima
            op = min(op, VALVE_LIMIT)

            # 4. ESCRIBIR válvula en el PLC
            with PLC() as comm:
                comm.IPAddress = PLC_IP
                ret_w = comm.Write(VALVE_WRITE_TAG, op)
                if ret_w.Status != "Success":
                    print(f"\n[ERROR] Escritura fallida: {ret_w.Status}")
                    break

            # 5. Registrar
            data.append((t_h, SETPOINT_PSI, pv, op))
            logger.log(t_h, SETPOINT_PSI, pv, op)
            print(
                f"  Paso {step + 1:3d}/{N_STEPS} | t={t_h:.4f} h | "
                f"SP={SETPOINT_PSI:.1f} | PV={pv:.2f} | OP={op:.2f} %"
            )

            # 6. Esperar
            time.sleep(SAMPLE_TIME_SEC)

    except KeyboardInterrupt:
        print("\n[WARN] Interrumpido por el usuario.")

    finally:
        # ── SEGURIDAD: Cerrar válvula al terminar ─────────
        print("\n[SEGURIDAD] Cerrando válvula a 0 % ...")
        try:
            with PLC() as comm:
                comm.IPAddress = PLC_IP
                comm.Write(VALVE_WRITE_TAG, 0.0)
            print("[SEGURIDAD] Válvula cerrada.")
        except Exception as e:
            print(f"[SEGURIDAD] ⚠ No se pudo cerrar la válvula: {e}")

        logger.finalize()

    # ── Graficar resultado ────────────────────────────────
    if data:
        time_h = [r[0] for r in data]
        sp     = [r[1] for r in data]
        pv     = [r[2] for r in data]
        op     = [r[3] for r in data]

        plt.style.use("ggplot")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

        ax1.step(time_h, sp, "r--", where="post", label="Set-point")
        ax1.step(time_h, pv, "b-",  where="post", label="Presión (PV)")
        ax1.set_ylabel("Presión (psi)")
        ax1.set_title("Prueba Segura — PID Real")
        ax1.legend()

        ax2.step(time_h, op, "g-", where="post", label="Válvula (OP)")
        ax2.set_ylabel("Apertura (%)")
        ax2.set_xlabel("Tiempo (h)")
        ax2.legend()

        plt.tight_layout()
        plt.savefig("data/test_real_safe_result.png", dpi=150)
        print("[INFO] Gráfico guardado en: data/test_real_safe_result.png")
        plt.show()


if __name__ == "__main__":
    main()
