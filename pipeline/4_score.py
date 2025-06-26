#!/usr/bin/env python
# pipeline/4_score.py

import argparse
import os
import pandas as pd
import joblib
import pyarrow.dataset as ds
import numpy as np
from datetime import datetime, timedelta
from tabulate import tabulate

def parse_dates(args):
    if args.date:
        return [args.date]
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end   = datetime.strptime(args.end_date,   "%Y-%m-%d").date()
    if end < start:
        raise ValueError("end-date debe ser ≥ start-date")
    dates = []
    while start <= end:
        dates.append(start.isoformat())
        start += timedelta(days=1)
    return dates

def load_features_range(feat_dir, start_date, end_date):
    print(f"▶️ Cargando rango de features de {start_date} a {end_date}…")
    dataset = ds.dataset(feat_dir, format="parquet", partitioning="hive")
    table   = dataset.to_table()
    df      = table.to_pandas()
    df["date"] = pd.to_datetime({
        "year":  df["year"],
        "month": df["month"],
        "day":   df["day"]
    })
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    return df.loc[mask]

def main():
    parser = argparse.ArgumentParser(
        description="4. Scoring: aplica el pipeline a una fecha o a un rango"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date",       type=str, help="Fecha única 'YYYY-MM-DD'")
    group.add_argument("--start-date", type=str, help="Fecha inicio rango 'YYYY-MM-DD'")
    parser.add_argument("--end-date",     type=str, default=None, help="Fecha fin rango (obligatorio si --start-date)")
    parser.add_argument("--features-dir", type=str, default="data/features")
    parser.add_argument("--model-path",   type=str, default="models/iforest_pipeline.pkl")
    parser.add_argument("--alerts-dir",   type=str, default="data/alerts")
    parser.add_argument("--no-save",      action="store_true", help="Sólo imprime alertas y no guarda archivos")
    args = parser.parse_args()

    if args.start_date and not args.end_date:
        parser.error("--end-date es obligatorio con --start-date")

    dates = parse_dates(args)
    pipeline = joblib.load(args.model_path)
    print(f"▶️ Pipeline cargado desde {args.model_path}\n")

    all_alerts = []  # Lista para almacenar todas las alertas de todas las fechas

    for fecha in dates:
        yyyy, mm, dd = fecha.split("-")
        feat_path = os.path.join(
            args.features_dir,
            f"year={yyyy}", f"month={mm}", f"day={dd}", "features.parquet"
        )
        if not os.path.exists(feat_path):
            continue

        df = pd.read_parquet(feat_path)

        # Filtro mínimo de actividad
        if "cnt_24h" in df.columns:
            df = df[df["cnt_24h"] > 10]
        else:
            print("⚠️ No se encontró 'cnt_24h'. Se omite filtro.")

        if df.empty:
            continue

        # Preparar X (drop identificadores y particiones)
        drop_cols = [c for c in ["user_id", "year", "month", "day", "date"] if c in df.columns]
        X = df.drop(columns=drop_cols, errors="ignore")

        # Scoring
        scores = pipeline.decision_function(X)
        flag_static = pipeline.predict(X) < 0

        # Umbral dinámico basado en contamination del modelo
        if hasattr(pipeline, "named_steps") and "iforest" in pipeline.named_steps:
            cont = pipeline.named_steps["iforest"].contamination
        elif hasattr(pipeline, "contamination"):
            cont = pipeline.contamination
        else:
            cont = 0.01
        threshold = np.percentile(scores, cont * 100)
        flag_dynamic = scores < threshold

        alerts = pd.DataFrame({
            "user_id":                df["user_id"],
            "date":                   fecha,
            "cnt_24h":                df.get("cnt_24h"),
            "sum_24h":                df.get("sum_24h"),
            "avg_amount":             df.get("avg_amount"),
            "unique_merchants":       df.get("unique_merchants"),
            "anomaly_score":          scores,
            "flag_suspicious":        flag_static,
            "flag_suspicious_dynamic":flag_dynamic
        })

        # Ya no se guarda en la carpeta consolidated
        all_alerts.append(alerts)

    # Resumen global
    if all_alerts:
        df_all = pd.concat(all_alerts, ignore_index=True)
        total_s = df_all["flag_suspicious"].sum()
        print(f"\n🔎 Total de alertas estáticas en el rango: {total_s}")
        top10 = df_all.sort_values("anomaly_score").head(10)
        print("\n🏆 Top 10 estático de usuarios más anómalos:")
        print(tabulate(top10, headers="keys", tablefmt="psql", showindex=False))

        # Guardar todo el dataframe consolidado como CSV
        if not args.no_save:
            consolidated_path = os.path.join(args.alerts_dir, "alerts_consolidated.csv")
            df_all.to_csv(consolidated_path, index=False)
            print(f"\n✅ CSV consolidado guardado en: {consolidated_path}")

if __name__ == "__main__":
    main()

# Ejecutar ejemplo:
# python pipeline/4_score.py --start-date 2021-01-01 --end-date 2021-11-30
# python pipeline/4_score.py --date 2021-11-30
