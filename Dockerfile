FROM python:3.10-slim

RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ pipeline/
COPY data/features/ data/features/
COPY models/ models/

ENTRYPOINT ["python", "pipeline/4_score.py"]
CMD ["--help"]

### Ejemplo de uso:
# Si es necesario crear el directorio de alertas antes de ejecutar el script:
# docker run --rm --entrypoint /bin/sh nequi-pipeline -c "mkdir -p data/alerts && python pipeline/4_score.py --start-date 2021-01-01 --end-date 2021-01-10"

### Si no es necesario crear el directorio de alertas, se puede ejecutar directamente:
# docker run --rm nequi-pipeline --start-date 2021-01-01 --end-date 2021-11-30