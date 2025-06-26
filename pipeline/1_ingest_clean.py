import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser(
        description="1. Ingesta y limpieza para una fecha dada."
    )
    parser.add_argument(
        "--raw-file",
        type=str,
        default="data/raw/df_clean.parquet",
        help="Parquet con TODO el histórico (1 año)."
    )
    parser.add_argument(
        "--run-date",
        type=str,
        required=True,
        help="Fecha a procesar en formato YYYY-MM-DD"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/clean",
        help="Directorio base para la data limpia particionada"
    )
    args = parser.parse_args()

    # Parsear fecha
    run_date = pd.to_datetime(args.run_date).date()
    year = f"{run_date.year:04d}"
    month = f"{run_date.month:02d}"
    day = f"{run_date.day:02d}"

    # Leer raw y filtrar por día
    print(f"▶️ Ingesta+limpieza para {run_date}")
    df = pd.read_parquet(args.raw_file)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df_day = df[df["transaction_date"].dt.date == run_date].copy()

    # Limpieza básica
    df_day = df_day.drop_duplicates(subset=["_id"])
    df_day["transaction_amount"] = pd.to_numeric(
        df_day["transaction_amount"], errors="coerce"
    )
    df_day["transaction_type"] = df_day["transaction_type"].astype("category")

    # Particionar y escribir
    out_dir = os.path.join(
        args.output_dir,
        f"year={year}",
        f"month={month}",
        f"day={day}"
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "df_clean.parquet")
    df_day.to_parquet(out_path, index=False)
    print(f"✅ Data limpia escrita en {out_path}")


if __name__ == "__main__":
    main()
