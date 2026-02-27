# ── Etapa 1: imagen base con dependencias ─────────────────
FROM python:3.13-slim AS base

# Evitar prompts interactivos y configurar matplotlib sin GUI
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

# Instalar solo lo mínimo del sistema que necesita pylogix (sockets raw)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iputils-ping \
        net-tools && \
    rm -rf /var/lib/apt/lists/*

# ── Etapa 2: dependencias Python ──────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Etapa 3: código del proyecto ──────────────────────────
COPY config/ config/
COPY src/ src/
COPY utils/ utils/
COPY main.py .
COPY test_simulation.py .

# Crear carpeta de salida de datos
RUN mkdir -p data

# ── Volumen para persistir logs y gráficos ────────────────
VOLUME ["/app/data"]

# ── Puerto Ethernet/IP (CIP) ─────────────────────────────
# pylogix se conecta al PLC en el puerto 44818 TCP (EtherNet/IP).
# Se expone como documentación; la comunicación real es SALIENTE
# desde el contenedor hacia el PLC, no entrante.
EXPOSE 44818

# ── Punto de entrada por defecto: controlador real ────────
# Sobrescribir con:  docker run ... controlador-presion python test_simulation.py --fast
ENTRYPOINT ["python"]
CMD ["main.py"]
