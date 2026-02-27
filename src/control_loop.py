"""
Lazo de control principal.

Orquesta la lectura de presión, cómputo PID y escritura de válvula,
independientemente de si la planta es real (PLC) o simulada.
"""

import time
from src.pid_controller import PIDController
from src.plant_interface import PlantInterface
from utils.data_logger import DataLogger


def run_control_loop(
    plant: PlantInterface,
    setpoint_fn,                # callable(step: int, time_h: float) -> float
    n_steps: int,
    sample_time_sec: float,
    logger: DataLogger,
    real_time: bool = True,
    verbose: bool = True,
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

    try:
        for k in range(n_steps):
            time_h = k * sample_time_sec / 3600.0

            # 1. Obtener set-point
            sp = setpoint_fn(k, time_h)

            # 2. Leer presión
            pv = plant.read_pressure()

            # 3. Calcular acción de control
            op = controller.compute(sp, pv)

            # 4. Escribir apertura de válvula
            plant.write_valve(op)

            # 5. Registrar datos
            logger.log(time_h, sp, pv, op)

            # 6. Progreso en consola
            if verbose:
                print(
                    f"  [{k + 1:>4}/{n_steps}]  "
                    f"t={time_h:.4f} h  |  SP={sp:6.2f}  PV={pv:6.2f}  OP={op:6.2f}%",
                    end="\r",
                )

            # 7. Esperar periodo de muestreo
            if real_time:
                time.sleep(sample_time_sec)

    except KeyboardInterrupt:
        print("\n[INFO] Lazo de control detenido por el usuario (Ctrl+C).")

    finally:
        if verbose:
            print()  # salto de línea tras \r
        plant.close()
        logger.finalize()

    return logger
