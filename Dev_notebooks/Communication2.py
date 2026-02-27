import csv
import os
import time
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pylogix import PLC
import threading #para controles

# ================== CONFIG ==================
OUTPUT_FILE = "plc_selected_tags.xls"   # CSV con extensión .xls (como tu script)
INTERVAL_SEC = 5.0                      # Leer cada 5 s
READ_CHUNK_SIZE = 20                    # Lote de lectura (10–40 recomendado)

PLC_IP = "192.168.185.6"
PLC_SLOT = 0

# Tags específicos a leer (en el orden en que se grabarán en el archivo)
TAGS: List[str] = [
    "ENT_AGITADOR",             # Agitador RPM
    "SAL_PRESION",              # Presión psi ################################
    "SAL_RTD_TE102",            # Temperatura chaqueta °C    
    "SAL_RTD_TE103",            # Temperatura chiller °C
    "SAL_RTD_TE106",            # Temperatura calderas °C
    "SAL_RTD_TE101",            # Temperatura reactor °C
    "ENT_FCV101",               # Válvula neumática de vapor (%)
    "SAL_FLUJO_GAS",            # Flujo de aire medido L/min
    "ENT_P101",                 # Porcentaje bomba peristáltica de miel % 
    "SV101",                    # Contador de activaciones de antiespumante
    "ENT_P102",                 # Porcentaje bomba peristáltica de urea % 
    "SAL_O2",                   # O2 %v/v
    "SAL_CO2",                  # CO2 %v/v
    "ENT_P104_CHILLER",         # Bomba de chiller Hz
    "RQ",                       # RQ  
    "SAL_PH",                   # pH
    "Q_CO2",                    # Consumo de O2
    "SAL_OXIGENO",              # Oxígeno disuelto mg/L
    "Q_O2",                     # Consumo de CO2
    "SAL_FLUJO_YOKOGAWA",       # Flujo de miel medido mL/min
    "SAL_DENSIDAD_YOKOGAWA",    # Densidad de miel alimentada g/L
    "FLUJO_GAS",              # Set-point de gas g/L  LECTURA Y ESCRITURA
    "FLUJO_GAS_2",              # Set-point de gas g/L  LECTURA Y ESCRITURA
    "PID_OXI_DISUEL_SALIDA",     # Salida del PID (% de enriquecimiento de O2)"
    "ENT_FCV101"
    #"Program:MainProgram.VAPOR_SANITIZACION_HMI"    # Para modificar la válvula FCV101. Solo escritura, no lectura
    #"Program:MainProgram.P103_HMI"     # Para modificar bomba sustrato
    #"Program:MainProgram.AGITADOR_HMI"     # Para modificar bomba sustrato
]
# ============================================

# Excepciones: alias -> (ip, slot, nombre_real_en_el_PLC)
EXCEPTIONS: Dict[str, Tuple[str, int, str]] = {
    # "RQ-40LA": ("192.168.185.4", 0, "RQ"),
    # "SAL_O2-40LA": ("192.168.185.4", 0, "SAL_O2"),
    # "SAL_CO2-40LA": ("192.168.185.4", 0, "SAL_CO2"),
    # Si mañana agregas más, sigue el mismo patrón:
    # "OtroAlias": ("192.168.185.4", 0, "TAG_REAL"),
}

def batch_read_values(ip: str, slot: int, tag_names: List[str]) -> Dict[str, Any]:
    """
    Lee valores en lotes respetando READ_CHUNK_SIZE, desde un mismo PLC.
    Retorna: { tag_name: value }
    """
    out: Dict[str, Any] = {}
    if not tag_names:
        return out
    with PLC() as comm:
        comm.IPAddress = ip
        # comm.ProcessorSlot = slot

        for i in range(0, len(tag_names), READ_CHUNK_SIZE):
            chunk = tag_names[i: i + READ_CHUNK_SIZE]
            try:
                r = comm.Read(chunk)
                if not isinstance(r, list):
                    r = [r]
                for item in r:
                    out[item.TagName] = item.Value if getattr(item, "Status", None) == "Success" else None
            except Exception:
                # Si falla un lote, marcamos esos tags como None
                for tn in chunk:
                    out[tn] = None
    return out

def read_exception_values(exceptions: Dict[str, Tuple[str, int, str]]) -> Dict[str, Any]:
    """
    Lee todos los tags definidos en EXCEPTIONS, agrupando por (ip, slot).
    Retorna: { alias: value }
    """
    out: Dict[str, Any] = {}
    if not exceptions:
        return out

    # Agrupar por conexión (ip, slot) para leer en lote
    groups: Dict[Tuple[str, int], List[Tuple[str, str]]] = defaultdict(list)
    for alias, (ip, slot, plc_tag) in exceptions.items():
        groups[(ip, slot)].append((alias, plc_tag))

    for (ip, slot), alias_and_tags in groups.items():
        with PLC() as comm:
            comm.IPAddress = ip
            comm.ProcessorSlot = slot
            tag_list = [plc_tag for _, plc_tag in alias_and_tags]
            try:
                r = comm.Read(tag_list)
                if not isinstance(r, list):
                    r = [r]
                # Mapear por nombre real de tag
                rmap = {getattr(item, "TagName", None): item for item in r}
                for alias, plc_tag in alias_and_tags:
                    item = rmap.get(plc_tag)
                    out[alias] = (item.Value if item and getattr(item, "Status", None) == "Success" else None)
            except Exception:
                for alias, _ in alias_and_tags:
                    out[alias] = None

    return out

def normalize_value(val: Any) -> str:
    """
    Normaliza el valor a string para CSV (maneja bytes, listas simples, None, etc.).
    """
    if val is None:
        return ""
    if isinstance(val, (bytes, bytearray)):
        return val.hex()
    if isinstance(val, (list, tuple)):
        try:
            return "[" + ", ".join(normalize_value(v) for v in val) + "]"
        except Exception:
            return str(val)
    return str(val)

def ensure_header(path: str, tag_names: List[str]) -> List[str]:
    """
    Si existe archivo con encabezado compatible (Timestamp + tags en el mismo orden), lo reutiliza.
    Si no, crea/reescribe con el nuevo encabezado.
    Retorna el encabezado final.
    """
    desired_header = ["Timestamp"] + tag_names
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
            if header == desired_header:
                return header
        except Exception:
            pass
    # (Re)escribir encabezado
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(desired_header)
    return desired_header

def main():
    header = ensure_header(OUTPUT_FILE, TAGS)
    
    # Separar qué tags van al PLC principal y cuáles son excepciones
    normal_tags = [tn for tn in TAGS if tn not in EXCEPTIONS]
    while True:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1) Lectura normal (PLC principal .6) en lotes
        values_map = batch_read_values(PLC_IP, PLC_SLOT, normal_tags)
        
        ######## modificación de un actuador ############################
        with PLC() as comm:
            comm.IPAddress = PLC_IP
            comm.Write("Program:MainProgram.VAPOR_SANITIZACION_HMI", 10) ################################
        #################################################################

        # 2) Lectura de excepciones (otros PLC/IP) y fusionar
        if EXCEPTIONS:
            values_map.update(read_exception_values(EXCEPTIONS))

        # 3) Armar la fila según el orden exacto del header
        row = [ts] + [normalize_value(values_map.get(tn, None)) for tn in TAGS]

        # 4) Escribir la fila
        with open(OUTPUT_FILE, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(row)

        # Consola opcional
        # print(f"[{ts}] fila agregada.")
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()

