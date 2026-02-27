"""
Lazo de control principal.

Orquesta la lectura de presión, cómputo PID y escritura de válvula,
independientemente de si la planta es real (PLC) o simulada.
"""

import math
import time
from src.pid_controller import PIDController
from src.plant_interface import PlantInterface
from utils.data_logger import DataLogger

# ── Validación de mediciones ──────────────────────────────
PV_MIN = -5.0     # Presión mínima plausible [psi]
PV_MAX = 50.0     # Presión máxima plausible [psi]
MAX_READ_RETRIES = 3   # Reintentos ante fallo de lectura


def run_control_loop(
    plant: PlantInterface,
    setpoint_fn,                # callable(step: int, time_h: float) -> float
    n_steps: int,
    sample_time_sec: float,
    logger: DataLogger,
    real_time: bool = True,
    verbose: bool = True,
    persist_state: bool = True,
) -> DataLogger:
    """Ejecuta el lazo PID cerrado.

    Parámetros
    ----------
    plant           : interfaz de lectura/escritura (PLC o simulada)
    setpoint_fn     : función que recibe (paso, tiempo_h) → set-point [psi]
    n_steps         : cantidad total de iteraciones
    sample_time_sec : periodo de muestreo [s]
    logger          : registrador de datos CSV
    real_time       : si True, espera sample_time_sec entre cada paso
    verbose         : imprime progreso en consola

    Retorna
    -------
    DataLogger  con todos los datos registrados
    """
    controller = PIDController()

    # Restaurar estado previo si existe (robustez ante reinicios)
    if persist_state:
        controller.load_state()

    try:
        for k in range(n_steps):
            time_h = k * sample_time_sec / 3600.0

            # 1. Obtener set-point
            sp = setpoint_fn(k, time_h)

            # 2. Leer presión (con reintentos)
            pv = None
            for attempt in range(1, MAX_READ_RETRIES + 1):
                try:
                    pv = plant.read_pressure()
                    break
                except RuntimeError as e:
                    if verbose:
                        print(f"\n[WARN] Lectura fallida (intento {attempt}/{MAX_READ_RETRIES}): {e}")
                    if attempt == MAX_READ_RETRIES:
                        print("\n[ERROR] Lecturas agotadas. Deteniendo lazo.")
                        raise
                    time.sleep(1)

            # 3. Validar medición de presión
            if pv is None or math.isnan(pv) or not (PV_MIN <= pv <= PV_MAX):
                print(f"\n[WARN] PV fuera de rango ({pv}). Manteniendo salida anterior.")
                continue

            # 4. Calcular acción de control
            op = controller.compute(sp, pv)

            # 5. Escribir apertura de válvula
            try:
                plant.write_valve(op)
            except RuntimeError as e:
                if verbose:
                    print(f"\n[WARN] Escritura fallida: {e}")

            # 6. Persistir estado del controlador
            if persist_state:
                controller.save_state()

            # 7. Registrar datos
            logger.log(time_h, sp, pv, op)

            # 8. Progreso en consola
            if verbose:
                print(
                    f"  [{k + 1:>4}/{n_steps}]  "
                    f"t={time_h:.4f} h  |  SP={sp:6.2f}  PV={pv:6.2f}  OP={op:6.2f}%",
                    end="\r",
                )

            # 9. Esperar periodo de muestreo
            if real_time:
                time.sleep(sample_time_sec)

    except KeyboardInterrupt:
        print("\n[INFO] Lazo de control detenido por el usuario (Ctrl+C).")
    except RuntimeError as e:
        print(f"\n[ERROR] Error crítico de comunicación: {e}")

    finally:
        if verbose:
            print()  # salto de línea tras \r
        plant.close()
        logger.finalize()

    return logger
