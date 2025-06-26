#!/usr/bin/env python
import argparse
import os
import pandas as pd
import joblib
from datetime import datetime, timedelta
from tabulate import tabulate  # pip install tabulate

def parse_dates(args):
    if args.date:
        return [args.date]
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end   = datetime.strptime(args.end_date,   "%Y-%m-%d").date()
    if end < start:
        raise ValueError("end-date debe ser ≥ start-date")
    delta = timedelta(days=1)
    dates = []
    while start <= end:
        dates.append(start.isoformat())
        start += delta
    return dates

def main():
    parser = argparse.ArgumentParser(
        description="4. Scoring: aplica el modelo a un día o a un rango"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date",       type=str, help="Fecha única 'YYYY-MM-DD'")
    group.add_argument("--start-date", type=str, help="Fecha inicio rango")
    parser.add_argument("--end-date",   type=str, help="Fecha fin rango")
    parser.add_argument("--features-dir", type=str, default="data/features")
    parser.add_argument("--model-path",   type=str, default="models/iforest.pkl")
    parser.add_argument("--alerts-dir",   type=str, default="data/alerts")
    parser.add_argument("--no-save",      action="store_true",
                        help="Sólo imprime alertas (top20) y no guarda archivos")
    args = parser.parse_args()

    if args.start_date and not args.end_date:
        parser.error("--end-date es obligatorio con --start-date")

    dates = parse_dates(args)
    model = joblib.load(args.model_path)
    print(f"▶️ Modelo cargado desde {args.model_path}\n")

    all_alerts = []
    for fecha in dates:
        yyyy, mm, dd = fecha.split("-")
        feat_path = os.path.join(
            args.features_dir,
            f"year={yyyy}", f"month={mm}", f"day={dd}", "features.parquet"
        )
        if not os.path.exists(feat_path):
            continue

        df = pd.read_parquet(feat_path)

        # Filtrar usuarios con más de 10 transacciones
        if 'cnt_24h' in df.columns:
            df = df[df['cnt_24h'] > 10]
        # Verificar feature de tiempo entre transacciones
        if 'avg_interval_minutes' in df.columns:
            pass
        else:
            print("⚠️ No se encontró la columna 'avg_interval_minutes'. Considera revisar la featurización.")

        # Si no hay usuarios tras el filtro, saltar el día
        if df.empty:
            continue

        X  = df.drop(columns=[c for c in ["user_id"] if c in df.columns], errors="ignore")
        scores = model.decision_function(X)
        flags  = model.predict(X) < 0

        alerts = pd.DataFrame({
            "user_id":         df["user_id"],
            "date":            fecha,
            "cnt_24h":         df.get("cnt_24h"),
            "sum_24h":         df.get("sum_24h"),
            "avg_amount":      df.get("avg_amount"),
            "unique_merchants":df.get("unique_merchants"),
            "anomaly_score":   scores,
            "flag_suspicious": flags
        })

        if args.no_save:
            all_alerts.append(alerts)
        else:
            outdir = os.path.join(
                args.alerts_dir,
                f"year={yyyy}", f"month={mm}", f"day={dd}"
            )
            os.makedirs(outdir, exist_ok=True)
            outfile = os.path.join(outdir, "alerts.parquet")
            alerts.to_parquet(outfile, index=False)
            print(f"✅ Guardado: {outfile}\n")
        # Acumular todos los resultados, no solo si no_save
        all_alerts.append(alerts)

    # Resumen global después de procesar todos los días
    if all_alerts:
        df_all = pd.concat(all_alerts, ignore_index=True)
        total_sospechosos = df_all['flag_suspicious'].sum()
        print(f"\n🔎 Total de usuarios marcados como sospechosos en el rango: {total_sospechosos}")
        top10 = df_all.sort_values("anomaly_score").head(10)
        print("\n🏆 Top 10 global de usuarios más anómalos en el rango:")
        print(tabulate(top10, headers="keys", tablefmt="psql", showindex=False))

if __name__ == "__main__":
    main()
