#!/usr/bin/env python
# pipeline/3_train.py

import argparse
import os
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import pyarrow.dataset as ds

def load_features(feat_dir, start_date, end_date):
    print(f"▶️ Cargando features de {start_date} a {end_date} con PyArrow Dataset…")
    dataset = ds.dataset(feat_dir, format="parquet", partitioning="hive")
    table = dataset.to_table()
    df = table.to_pandas()
    # Reconstruir fecha desde particiones
    df["date"] = pd.to_datetime({
        "year":  df["year"],
        "month": df["month"],
        "day":   df["day"]
    })
    # Filtrar por rango
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    return df.loc[mask]

def main():
    parser = argparse.ArgumentParser(
        description="3. Entrenamiento de IsolationForest con todo el histórico de features."
    )
    parser.add_argument("--start-date",    type=str,   required=True, help="YYYY-MM-DD inicio histórico")
    parser.add_argument("--end-date",      type=str,   required=True, help="YYYY-MM-DD fin histórico")
    parser.add_argument("--features-dir",  type=str,   default="data/features", help="Dir base de features particionadas")
    parser.add_argument("--model-dir",     type=str,   default="models",        help="Dónde guardar el pipeline entrenado")
    parser.add_argument("--contamination", type=float, default=0.01,           help="Fracción de contaminación para IsolationForest")
    parser.add_argument("--n-estimators",  type=int,   default=100,            help="Número de árboles en IsolationForest")
    parser.add_argument("--scale",         action="store_true",              help="Estandarizar features antes de entrenar")
    args = parser.parse_args()

    # 1) Carga de todas las features en rango
    df = load_features(args.features_dir, args.start_date, args.end_date)

    # 2) Filtrar usuarios con >10 transacciones diarias
    if "cnt_24h" in df.columns:
        df = df[df["cnt_24h"] > 10]
        print(f"🧑‍💼 Usuarios con >10 transacciones en algún día: {df['user_id'].nunique()} usuarios")
    else:
        print("⚠️ No se encontró 'cnt_24h'. Se omitió filtro por cantidad.")

    # 3) Preparar X (eliminar columnas no numéricas/identificadoras)
    drop_cols = [c for c in ["user_id", "year", "month", "day", "date"] if c in df.columns]
    X = df.drop(columns=drop_cols, errors="ignore")
    print(f"🔧 Matriz X: {X.shape[0]} muestras × {X.shape[1]} features")

    # 4) Construir pipeline
    steps = []
    if args.scale:
        steps.append(("scaler", StandardScaler()))
    steps.append((
        "iforest",
        IsolationForest(
            n_estimators=args.n_estimators,
            contamination=args.contamination,
            random_state=42,
            n_jobs=-1
        )
    ))
    pipeline = Pipeline(steps)

    # 5) Entrenar
    print("🎯 Entrenando IsolationForest…")
    pipeline.fit(X)
    print("✅ Entrenamiento completado.")

    # 6) Estadísticas de scores en entrenamiento
    scores = pipeline.decision_function(X)
    print("📊 Estadísticas de scores (decision_function):")
    print(pd.Series(scores).describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]))
    preds = pipeline.predict(X)
    n_anom = (preds == -1).sum()
    prop_anom = n_anom / len(preds)
    print(f"⚠️ Anomalías en entrenamiento: {n_anom}/{len(preds)} ({prop_anom:.2%})")
    print(f"🏅 Score medio de decision_function: {scores.mean():.4f}")

    # 7) Persistir pipeline completo
    os.makedirs(args.model_dir, exist_ok=True)
    model_path = os.path.join(args.model_dir, "iforest_pipeline.pkl")
    joblib.dump(pipeline, model_path)
    print(f"✅ Pipeline guardado en {model_path}")

if __name__ == "__main__":
    main()

# python pipeline/3_train.py --start-date 2021-01-01 --end-date 2021-11-30 --scale
