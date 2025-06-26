#!/usr/bin/env python
import argparse
import subprocess
import sys
import pandas as pd
import datetime
from concurrent.futures import ProcessPoolExecutor

def call(script, *args):
    cmd = [sys.executable, script] + list(args)
    print(":", " ".join(cmd))
    subprocess.run(cmd, check=True)

def process_date(date_str):
    call("pipeline/1_ingest_clean.py", "--run-date", date_str)
    call("pipeline/2_featurize.py",   "--date",     date_str)

def main():
    parser = argparse.ArgumentParser(
        description="Run all steps: ingest → featurize → train sobre un rango dado"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="YYYY-MM-DD inicio del rango histórico"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="YYYY-MM-DD fin del rango histórico"
    )
    args = parser.parse_args()

    # Construir lista de fechas
    start = pd.to_datetime(args.start_date).date()
    end   = pd.to_datetime(args.end_date).date()
    delta = datetime.timedelta(days=1)
    fechas = [
        (start + i * delta).isoformat()
        for i in range((end - start).days + 1)
    ]

    print(f"▶️ Procesando {len(fechas)} días en paralelo…")
    with ProcessPoolExecutor(max_workers=4) as executor:
        executor.map(process_date, fechas)

    # 3) Entrenar con TODO el histórico
    call(
        "pipeline/3_train.py",
        "--start-date", args.start_date,
        "--end-date",   args.end_date
    )

    print("🏁 Pipeline completo.")

if __name__ == "__main__":
    main()
