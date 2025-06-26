import argparse
import subprocess
import sys
import pandas as pd
import datetime

def call(script, *args):
    cmd = [sys.executable, script] + list(args)
    print(":", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(
        description="Run all steps: ingest → featurize → train sobre un rango dado"
    )
    parser.add_argument(
        "--start-date", type=str, required=True, help="YYYY-MM-DD fecha inicial"
    )
    parser.add_argument(
        "--end-date", type=str, required=True, help="YYYY-MM-DD fecha final"
    )
    args = parser.parse_args()

    start = pd.to_datetime(args.start_date).date()
    end = pd.to_datetime(args.end_date).date()
    delta = datetime.timedelta(days=1)

    current = start
    while current <= end:
        date_str = current.isoformat()
        # 1) Ingest + clean
        call("pipeline/1_ingest_clean.py", "--run-date", date_str)
        # 2) Featurize
        call("pipeline/2_featurize.py", "--date", date_str)
        current += delta

    # 3) Entrenar con TODO el histórico
    call(
        "pipeline/3_train.py",
        "--start-date", args.start_date,
        "--end-date", args.end_date
    )

    print("🏁 Pipeline completo.")

if __name__ == "__main__":
    main()

# python pipeline/run_pipeline.py --start-date 2021-01-01 --end-date 2021-12-31
