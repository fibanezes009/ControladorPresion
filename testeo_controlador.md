# Instructivo de Testeo — Controlador PID de Presión en Biorreactor

> **Proyecto:** ControladorPresion  
> **Fecha de creación:** Febrero 2026  
> **Planta:** Biorreactor con PLC Allen-Bradley (CompactLogix/ControlLogix)  
> **Red:** Ethernet/IP — `192.168.185.6`

---

## Tabla de contenido

1. [Requisitos previos](#1-requisitos-previos)
2. [Configuración del entorno de software](#2-configuración-del-entorno-de-software)
3. [Fase 0 — Validación offline (sin PLC)](#3-fase-0--validación-offline-sin-plc)
4. [Fase 1 — Verificación de conectividad con el PLC](#4-fase-1--verificación-de-conectividad-con-el-plc)
5. [Fase 2 — Prueba de lectura y escritura manual](#5-fase-2--prueba-de-lectura-y-escritura-manual)
6. [Fase 3 — Prueba segura del controlador PID (SP fijo y bajo)](#6-fase-3--prueba-segura-del-controlador-pid-sp-fijo-y-bajo)
7. [Fase 4 — Prueba completa con perfil escalonado](#7-fase-4--prueba-completa-con-perfil-escalonado)
8. [Interpretación de resultados](#8-interpretación-de-resultados)
9. [Protocolo de seguridad y emergencia](#9-protocolo-de-seguridad-y-emergencia)
10. [Solución de problemas comunes](#10-solución-de-problemas-comunes)
11. [Referencia técnica del sistema](#11-referencia-técnica-del-sistema)

---

## 1. Requisitos previos

### Hardware

| Elemento | Detalle |
|---|---|
| PC con puerto Ethernet | Windows 10/11, Python 3.10+ |
| Cable Ethernet | Directo o a través de switch industrial |
| PLC Allen-Bradley | IP: `192.168.185.6`, Slot: `0` |
| Válvula neumática de vapor | Controlada por tag `Program:MainProgram.VAPOR_SANITIZACION_HMI` |
| Transmisor de presión | Lectura en tag `SAL_PRESION` (psi) |
| Válvula manual de seguridad | Accesible para cierre de emergencia de vapor |

### Software

| Componente | Versión mínima |
|---|---|
| Python | 3.10 |
| pylogix | cualquier versión reciente |
| numpy | cualquier versión reciente |
| scipy | cualquier versión reciente |
| pandas | cualquier versión reciente |
| matplotlib | cualquier versión reciente |

### Personal

- **Mínimo 2 personas:** una operando el software, otra monitoreando el biorreactor físicamente.
- El operador del biorreactor debe poder cerrar la válvula manual de vapor en cualquier momento.

---

## 2. Configuración del entorno de software

### 2.1 Preparar el entorno virtual

```powershell
# Navegar a la carpeta del proyecto
cd "C:\Users\COP21OSITB25\Mi unidad\ICESI\Controlador\ControladorPresion"

# Crear entorno virtual (si no existe)
python -m venv .venv

# Activar entorno virtual
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2.2 Verificar la instalación

```powershell
python -c "import pylogix; import numpy; import matplotlib; import scipy; import pandas; print('Todas las dependencias OK')"
```

**Resultado esperado:** `Todas las dependencias OK`

### 2.3 Configurar la IP del computador

El computador debe estar en la **misma subred** que el PLC:

| Dispositivo | IP | Máscara |
|---|---|---|
| PLC | `192.168.185.6` | `255.255.255.0` |
| PC (configurar) | `192.168.185.X` (ej: `192.168.185.100`) | `255.255.255.0` |

Configurar desde: **Panel de control → Redes → Adaptador Ethernet → Propiedades → IPv4 → Dirección IP estática.**

---

## 3. Fase 0 — Validación offline (sin PLC)

> **Objetivo:** Confirmar que el software funciona correctamente antes de conectarse al PLC.  
> **Duración:** < 1 minuto  
> **Requiere PLC:** NO

### Ejecutar

```powershell
python test_simulation.py --fast
```

### Resultado esperado

```
=======================================================
 Test de Simulación — Controlador PID de Presión
=======================================================
 Modo          : RÁPIDO (sin esperas)
 Pasos totales : 720
 Duración sim. : 2.0 h
 Set-point     : 15 → 20 → 10 → 2.5 psi
=======================================================
  [ 720/720]  t=1.9972 h  |  SP=  2.50  PV=  2.50  OP=  4.11%

[INFO] Datos guardados en : data/test_simulation_log.csv
[INFO] Total de muestras : 720
[INFO] Gráfico guardado en: data/test_simulation_result.png
```

### Verificar

- [ ] Los 720 pasos se completaron sin error.
- [ ] Se generó el archivo `data/test_simulation_log.csv`.
- [ ] Se generó el gráfico `data/test_simulation_result.png`.
- [ ] El gráfico muestra que la presión simulada (PV, línea azul) sigue al set-point (SP, línea roja punteada) en los 4 escalones: 15 → 20 → 10 → 2.5 psi.
- [ ] La apertura de la válvula (OP, línea verde) se mantiene entre 0% y 100%.

**Si esta fase falla, NO continuar a las siguientes fases.** Resolver primero el problema de software.

---

## 4. Fase 1 — Verificación de conectividad con el PLC

> **Objetivo:** Confirmar comunicación de red con el PLC.  
> **Duración:** 2 minutos  
> **Requiere PLC:** SÍ (encendido, con red conectada)

### 4.1 Ping al PLC

```powershell
ping 192.168.185.6
```

**Resultado esperado:**

```
Respuesta desde 192.168.185.6: bytes=32 tiempo<1ms TTL=64
```

- [ ] El PLC responde al ping (0% pérdida de paquetes).

**Si falla:** Verificar cable Ethernet, IP del PC (debe ser `192.168.185.X`), y que el PLC esté encendido.

### 4.2 Prueba de lectura con pylogix

Abrir un intérprete de Python:

```powershell
python
```

Ejecutar línea por línea:

```python
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = "192.168.185.6"
    ret = comm.Read("SAL_PRESION")
    print(f"Status : {ret.Status}")
    print(f"Presión: {ret.Value} psi")
```

**Resultado esperado:**

```
Status : Success
Presión: <valor numérico> psi
```

- [ ] El status es `Success`.
- [ ] El valor de presión es un número razonable (ej: entre -1 y 30 psi).

Salir del intérprete con `exit()`.

---

## 5. Fase 2 — Prueba de lectura y escritura manual

> **Objetivo:** Confirmar que se puede leer `SAL_PRESION` y escribir en `VAPOR_SANITIZACION_HMI`.  
> **Duración:** 5 minutos  
> **Requiere PLC:** SÍ  
> **PRECAUCIÓN:** Se va a escribir un valor en la válvula. Usar valor **0.0** (cerrada).

### Ejecutar en Python interactivo

```python
from pylogix import PLC
import time

PLC_IP = "192.168.185.6"

with PLC() as comm:
    comm.IPAddress = PLC_IP

    # 1. Leer presión actual
    ret = comm.Read("SAL_PRESION")
    print(f"[LECTURA]  SAL_PRESION = {ret.Value} psi  (Status: {ret.Status})")

    # 2. Leer apertura actual de la válvula
    ret_v = comm.Read("ENT_FCV101")
    print(f"[LECTURA]  ENT_FCV101 = {ret_v.Value} %    (Status: {ret_v.Status})")

    # 3. Escribir valor SEGURO (válvula cerrada)
    ret_w = comm.Write("Program:MainProgram.VAPOR_SANITIZACION_HMI", 0.0)
    print(f"[ESCRITURA] VAPOR_SANITIZACION_HMI = 0.0 %  (Status: {ret_w.Status})")

    time.sleep(3)

    # 4. Verificar que la escritura se reflejó
    ret_c = comm.Read("ENT_FCV101")
    print(f"[VERIF]    ENT_FCV101 = {ret_c.Value} %    (Status: {ret_c.Status})")
```

### Checklist

- [ ] `SAL_PRESION` se leyó con status `Success`.
- [ ] `ENT_FCV101` se leyó con status `Success`.
- [ ] La escritura de `VAPOR_SANITIZACION_HMI` retornó `Success`.
- [ ] Después de 3 segundos, `ENT_FCV101` refleja un valor coherente con la escritura (puede haber un ligero desfase por el procesamiento del PLC).

**Si la escritura falla:** Verificar que el tag `Program:MainProgram.VAPOR_SANITIZACION_HMI` existe y que el PLC está en modo **Remote Run** (no en modo Program).

---

## 6. Fase 3 — Prueba segura del controlador PID (SP fijo y bajo)

> **Objetivo:** Verificar el funcionamiento del PID en lazo cerrado con un set-point conservador.  
> **Duración:** 5 minutos (30 pasos × 10 s)  
> **Requiere PLC:** SÍ  
> **PRECAUCIÓN:** El controlador va a mover la válvula automáticamente.

### Parámetros de esta prueba

| Parámetro | Valor | Motivo |
|---|---|---|
| Set-point | 5.0 psi | Presión baja y segura |
| Pasos | 30 | Solo 5 minutos de operación |
| Límite de válvula | 30% | Protección extra: aunque el PID pida más, no se abrirá más del 30% |

### Antes de ejecutar

⚠️ **CHECKLIST OBLIGATORIO:**

- [ ] Cable Ethernet conectado al PLC.
- [ ] Fase 1 y Fase 2 completadas exitosamente.
- [ ] Operador presente físicamente junto al biorreactor.
- [ ] Válvula manual de vapor accesible para cierre de emergencia.
- [ ] Presión actual del reactor conocida y estable.
- [ ] Se ha comunicado al equipo de laboratorio que se va a ejecutar un controlador automático.

### Script de prueba

Crear el archivo `test_real_safe.py` en la raíz del proyecto con el siguiente contenido:

```python
"""
Prueba segura del PID contra el PLC real.
- Set-point fijo y bajo (5 psi)
- Solo 30 pasos (5 minutos)
- Al terminar, cierra la válvula a 0%
"""
from pylogix import PLC
import time
import matplotlib.pyplot as plt
from config.plc_config import PLC_IP, PRESSURE_TAG, VALVE_WRITE_TAG
from config.pid_config import SAMPLE_TIME_SEC
from src.pid_controller import PIDController
from utils.data_logger import DataLogger

# ── Parámetros de la prueba segura ──
SETPOINT_PSI = 5.0
N_STEPS = 30
VALVE_LIMIT = 30.0

def main():
    print("=" * 55)
    print(" PRUEBA SEGURA — PID vs PLC Real")
    print("=" * 55)
    print(f" Set-point      : {SETPOINT_PSI} psi")
    print(f" Pasos          : {N_STEPS} ({N_STEPS * SAMPLE_TIME_SEC / 60:.0f} min)")
    print(f" Límite válvula : {VALVE_LIMIT} %")
    print(f" PLC IP         : {PLC_IP}")
    print("=" * 55)
    input(" Presiona ENTER para iniciar (Ctrl+C para abortar)... ")

    pid = PIDController()
    logger = DataLogger("data/test_real_safe_log.csv")
    data = []

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
                comm.Write(VALVE_WRITE_TAG, op)

            # 5. Registrar
            data.append((t_h, SETPOINT_PSI, pv, op))
            logger.log(t_h, SETPOINT_PSI, pv, op)
            print(f"  Paso {step+1:3d}/{N_STEPS} | t={t_h:.4f}h | "
                  f"SP={SETPOINT_PSI:.1f} | PV={pv:.2f} | OP={op:.2f}%")

            # 6. Esperar
            time.sleep(SAMPLE_TIME_SEC)

    except KeyboardInterrupt:
        print("\n[WARN] Interrumpido por el usuario.")

    finally:
        # ── SEGURIDAD: Cerrar válvula al terminar ──
        print("\n[SEGURIDAD] Cerrando válvula a 0% ...")
        try:
            with PLC() as comm:
                comm.IPAddress = PLC_IP
                comm.Write(VALVE_WRITE_TAG, 0.0)
            print("[SEGURIDAD] Válvula cerrada.")
        except Exception as e:
            print(f"[SEGURIDAD] No se pudo cerrar la válvula: {e}")

        logger.finalize()

    # ── Graficar resultado ──
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
```

### Ejecutar

```powershell
python test_real_safe.py
```

### Durante la ejecución

- Monitorear en consola que la PV se mueve hacia el SP (5 psi).
- Verificar visualmente que la válvula neumática se mueve.
- Si algo es inesperado: **Ctrl+C** para detener (la válvula se cierra a 0% automáticamente).

### Checklist post-ejecución

- [ ] Los 30 pasos se completaron o se detuvo con Ctrl+C sin errores.
- [ ] La válvula se cerró a 0% al finalizar (mensaje de SEGURIDAD en consola).
- [ ] Se generó `data/test_real_safe_log.csv`.
- [ ] Se generó `data/test_real_safe_result.png`.
- [ ] La presión (PV) mostró tendencia a acercarse al set-point (5 psi).
- [ ] La apertura de válvula (OP) no superó el 30%.

### Qué observar en el gráfico

| Comportamiento | Significado | Acción |
|---|---|---|
| PV sube gradualmente hacia SP | El controlador funciona correctamente | Continuar a Fase 4 |
| PV oscila mucho alrededor de SP | Ganancia Kc demasiado alta | Reducir `KC` en `config/pid_config.py` |
| PV sube muy lento, no llega a SP | Ganancia Kc demasiado baja o límite de válvula muy bajo | Subir `KC` o aumentar `VALVE_LIMIT` |
| OP saturada en 30% y PV no llega | El límite protector es bajo para este SP | Aumentar `VALVE_LIMIT` en la próxima prueba |
| Error de comunicación | Problema de red o PLC | Volver a Fase 1 |

---

## 7. Fase 4 — Prueba completa con perfil escalonado

> **Objetivo:** Ejecutar el controlador con el perfil de set-point completo.  
> **Duración:** ~2 horas  
> **Requiere PLC:** SÍ  
> **PRECAUCIÓN:** El controlador operará la válvula continuamente durante 2 horas.

### Perfil de set-point

| Intervalo | Set-point (psi) | Duración |
|---|---|---|
| [0.0, 0.5) h | 15.0 | 30 min |
| [0.5, 1.0) h | 20.0 | 30 min |
| [1.0, 1.5) h | 10.0 | 30 min |
| [1.5, 2.0] h | 2.5 | 30 min |

Total: **720 pasos**, **2 horas**, muestreo cada **10 segundos**.

### Antes de ejecutar

- [ ] Fase 3 completada exitosamente (PID probado con SP bajo).
- [ ] Operador junto al biorreactor durante toda la ejecución.
- [ ] Biorreactor en condiciones estables.
- [ ] Se ha validado que el rango 2.5–20 psi es seguro para el proceso.

### Ejecutar

```powershell
python main.py
```

### Salida esperada

```
=======================================================
 Controlador PID de Presión — PLC Real
=======================================================
 PLC           : 192.168.185.6
 Tag lectura   : SAL_PRESION
 Tag escritura : Program:MainProgram.VAPOR_SANITIZACION_HMI
 Muestreo      : 10 s
 Pasos totales : 720
 Duración      : 2.0 h
=======================================================
 Presiona Ctrl+C para detener.

  [   1/ 720]  t=0.0000 h  |  SP= 15.00  PV=  X.XX  OP=  X.XX%
```

### Durante la ejecución (2 horas)

- La consola muestra el progreso en cada paso (SP, PV, OP).
- **Ctrl+C** detiene el controlador en cualquier momento.
- Al detenerse, la conexión con el PLC se cierra y los datos se guardan.

### Checklist post-ejecución

- [ ] Se completaron los 720 pasos (o se detuvo intencionalmente con Ctrl+C).
- [ ] Se generó el archivo `data/plc_control_log.csv`.
- [ ] La presión siguió los cambios de set-point en los 4 escalones.
- [ ] No hubo errores de comunicación persistentes.

### Generar gráfico de la ejecución real

Después de ejecutar `main.py`, los datos quedan en `data/plc_control_log.csv`. Para graficar:

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("data/plc_control_log.csv")
plt.style.use("ggplot")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

ax1.step(df["Time_h"], df["Setpoint_psi"], "r--", where="post", label="Set-point")
ax1.step(df["Time_h"], df["Pressure_psi"], "b-",  where="post", label="Presión (PV)")
ax1.set_ylabel("Presión (psi)")
ax1.set_title("Controlador PID Real — Biorreactor")
ax1.legend()

ax2.step(df["Time_h"], df["Valve_pct"], "g-", where="post", label="Válvula (OP)")
ax2.set_ylabel("Apertura (%)")
ax2.set_xlabel("Tiempo (h)")
ax2.legend()

plt.tight_layout()
plt.savefig("data/plc_control_result.png", dpi=150)
plt.show()
```

---

## 8. Interpretación de resultados

### Métricas clave

| Métrica | Cómo calcularla | Valor aceptable |
|---|---|---|
| **Overshoot** | `(PV_max - SP) / SP × 100` | < 20% |
| **Tiempo de establecimiento** | Tiempo hasta que PV se mantiene dentro de ±2% del SP | < 0.15 h (9 min) |
| **Error en estado estable** | `SP - PV_final` | < 0.5 psi |
| **Oscilación** | PV cruza el SP más de 3 veces | Indicador de que Kc es alto |

### Comparación con la simulación

Compare el gráfico real (`data/plc_control_result.png` o `data/test_real_safe_result.png`) contra el simulado (`data/test_simulation_result.png`):

- Si la **forma general** es similar → el modelo FOPDT identificado es bueno.
- Si la respuesta real es **más lenta** → τ real es mayor que el identificado.
- Si hay **más overshoot** → K real es mayor o θ es diferente.
- Si hay **oscilaciones** → considerar reducir Kc un 20-30% en `config/pid_config.py`.

---

## 9. Protocolo de seguridad y emergencia

### Detención normal

```
Ctrl+C en la terminal → El software cierra la válvula y guarda datos.
```

### Detención de emergencia

Si `Ctrl+C` no funciona o el software se cuelga:

1. **Cerrar la terminal** (cerrar la ventana de PowerShell).
2. **Ejecutar inmediatamente:**
   ```python
   from pylogix import PLC
   with PLC() as c:
       c.IPAddress = "192.168.185.6"
       c.Write("Program:MainProgram.VAPOR_SANITIZACION_HMI", 0.0)
   print("Válvula cerrada manualmente")
   ```
3. **Si nada funciona:** Cerrar la válvula manual de vapor físicamente.

### Límites de operación seguros

| Variable | Límite inferior | Límite superior | Acción si se excede |
|---|---|---|---|
| Presión (psi) | 0 | 25 | Detener controlador, cerrar válvula |
| Apertura válvula (%) | 0 | 100 | Saturación automática por software |
| Cambio de válvula por paso (%) | -5 | +5 | Rate limiter automático por software |
| Temperatura reactor (°C) | — | 80 | Detener controlador |

---

## 10. Solución de problemas comunes

### Error: `ping 192.168.185.6` no responde

- Verificar que el cable Ethernet está bien conectado.
- Verificar que la IP del PC es `192.168.185.X` con máscara `255.255.255.0`.
- Verificar que el PLC está encendido.
- Probar en otro puerto del switch.
- Desactivar el firewall de Windows temporalmente.

### Error: `Status: Connection failure` al leer tags

- El PLC está encendido pero no acepta conexiones CIP.
- Verificar que el PLC está en modo **Remote Run**.
- Verificar que no hay otro software (RSLogix/Studio 5000) bloqueando la conexión.

### Error: `Status: Path destination unknown`

- El tag no existe en el PLC. Verificar el nombre exacto:
  - Lectura: `SAL_PRESION`
  - Escritura: `Program:MainProgram.VAPOR_SANITIZACION_HMI`
- Los nombres son **case-sensitive** en algunos contextos.

### Error: El PID no mueve la válvula

- Verificar que se está escribiendo en el tag correcto (`VAPOR_SANITIZACION_HMI`, no `ENT_FCV101`).
- `ENT_FCV101` es de **lectura** (retroalimentación del actuador), no de escritura.
- Verificar que el PLC no tiene un controlador interno que sobrescriba el valor.

### Error: `ModuleNotFoundError: No module named 'pylogix'`

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### La presión no responde como en la simulación

- El modelo fue identificado en condiciones específicas (datos de SIP2.csv). Si las condiciones de operación cambiaron (temperatura, presión de vapor de alimentación, etc.), la dinámica puede ser diferente.
- Considerar re-identificar el modelo ejecutando un nuevo escalón y ajustando con `Dev_notebooks/AjusteFT_PID.ipynb`.

---

## 11. Referencia técnica del sistema

### Estructura del proyecto

```
ControladorPresion/
├── config/
│   ├── plc_config.py         ← IP y tags del PLC
│   └── pid_config.py         ← Parámetros K, Kc, Ti, Td, restricciones
├── src/
│   ├── plant_interface.py    ← RealPLCInterface / SimulatedPlantInterface
│   ├── pid_controller.py     ← PIDController (incremental)
│   └── control_loop.py       ← Lazo cerrado genérico
├── utils/
│   └── data_logger.py        ← Logger CSV
├── data/                     ← Salida (logs CSV, gráficos PNG)
├── Dev_notebooks/            ← Desarrollo (notebook, CSVs originales)
├── main.py                   ← Entrada para PLC real
├── test_simulation.py        ← Entrada para simulación offline
├── test_real_safe.py         ← Entrada para prueba segura (generarlo según Fase 3)
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Tags del PLC utilizados

| Tag | Tipo | Uso | Descripción |
|---|---|---|---|
| `SAL_PRESION` | Lectura | Variable de proceso (PV) | Presión del reactor en psi |
| `Program:MainProgram.VAPOR_SANITIZACION_HMI` | Escritura | Variable manipulada (OP) | Apertura de la válvula neumática de vapor (0–100%) |
| `ENT_FCV101` | Lectura | Verificación | Retroalimentación de la posición real de la válvula (%) |

### Parámetros del modelo FOPDT identificado

| Parámetro | Símbolo | Valor | Unidad |
|---|---|---|---|
| Ganancia estática | K | 0.6086 | psi/% |
| Constante de tiempo | τ | 0.0995 | h (358 s) |
| Tiempo muerto | θ | 0.0200 | h (72 s) |
| Retraso discreto | d | 7 | muestras |
| Periodo de muestreo | Ts | 10 | s |

### Parámetros del controlador PID

| Parámetro | Símbolo | Valor | Unidad |
|---|---|---|---|
| Ganancia proporcional | Kc | 4.9574 | %/psi |
| Tiempo integral | Ti | 0.0581 | h (209 s) |
| Tiempo derivativo | Td | 0.0073 | h (26 s) |
| Saturación mínima | OP_MIN | 0.0 | % |
| Saturación máxima | OP_MAX | 100.0 | % |
| Rate limiter | MAX_DELTA_OP | 5.0 | %/muestra |
| Criterio de sintonización | — | IAE Set-point | — |

### Algoritmo PID (forma incremental)

```
Δop[k] = ΔP + ΔI + ΔD

ΔP = Kc · (e[k] - e[k-1])                          ← Proporcional sobre error
ΔI = (Kc · Ts / Ti) · e[k]                          ← Integral sobre error
ΔD = (Kc · Td / Ts) · (-pv[k] + 2·pv[k-1] - pv[k-2])  ← Derivativa sobre PV

Δop[k] = clip(Δop[k], -MAX_DELTA_OP, +MAX_DELTA_OP)  ← Rate limiter
op[k]  = clip(op[k-1] + Δop[k], OP_MIN, OP_MAX)      ← Saturación
```

---

## Resumen del flujo de prueba

```
  Fase 0                Fase 1              Fase 2              Fase 3              Fase 4
┌──────────┐      ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│Simulación│ ──→  │  Ping + Read │ ─→ │ Read + Write │ ─→ │ PID seguro   │ ─→ │ PID completo │
│  offline │      │  (sin write) │    │   (manual)   │    │ SP=5, 5 min  │    │ 2 h, 4 SP    │
│ --fast   │      │              │    │  val=0.0%    │    │ lim=30%      │    │              │
└──────────┘      └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
 Sin PLC            Con PLC              Con PLC             Con PLC             Con PLC
 < 1 min            2 min                5 min               5 min               2 horas
```

> **Regla de oro:** Nunca saltar fases. Si una fase falla, resolver antes de continuar.
