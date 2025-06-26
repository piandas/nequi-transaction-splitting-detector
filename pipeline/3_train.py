#!/usr/bin/env python
import argparse
import os
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
import pyarrow.dataset as ds

def load_features(feat_dir, start_date, end_date):
    """
    Carga masivamente todos los parquet de features usando PyArrow Dataset,
    reconstruye la fecha a partir de las particiones year/month/day,
    filtra por rango y retorna un DataFrame pandas.
    """
    print(f"▶️ Cargando features de {start_date} a {end_date} con PyArrow Dataset…")
    dataset = ds.dataset(feat_dir, format="parquet", partitioning="hive")
    table   = dataset.to_table()
    df      = table.to_pandas()
    # Reconstruir fecha desde las particiones
    df["date"] = pd.to_datetime({
        "year":  df["year"],
        "month": df["month"],
        "day":   df["day"]
    })
    start = pd.to_datetime(start_date)
    end   = pd.to_datetime(end_date)
    mask  = (df["date"] >= start) & (df["date"] <= end)
    return df.loc[mask]

def main():
    parser = argparse.ArgumentParser(
        description="3. Entrenamiento de IsolationForest con todo el histórico de features."
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
    parser.add_argument(
        "--features-dir",
        type=str,
        default="data/features",
        help="Base dir de features particionadas"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="models",
        help="Dónde guardar el modelo entrenado"
    )
    args = parser.parse_args()

    # 1) Carga de features
    df = load_features(args.features_dir, args.start_date, args.end_date)

    # Filtrar usuarios con más de 10 transacciones
    if 'cnt_24h' in df.columns:
        df = df[df['cnt_24h'] > 10]
        print(f"🧑‍💼 Usuarios con >10 transacciones: {df['user_id'].nunique()} usuarios")
    else:
        print("⚠️ No se encontró la columna 'cnt_24h'. No se filtraron usuarios por cantidad de transacciones.")

    # Verificar feature de tiempo entre transacciones
    if 'avg_interval_minutes' in df.columns:
        print("⏱️ Feature 'avg_interval_minutes' presente. Ejemplo:")
        print(df[['user_id', 'avg_interval_minutes']].head())
    else:
        print("⚠️ No se encontró la columna 'avg_interval_minutes'. Considera revisar la featurización.")

    # Preparamos X eliminando usuario y columnas de partición
    X = df.drop(columns=[c for c in ["user_id", "year", "month", "day", "date"] if c in df.columns], errors="ignore")
    print(f"🔧 Matriz X: {X.shape[0]} muestras × {X.shape[1]} features")

    # 2) Entrenar IsolationForest en paralelo
    print("🎯 Entrenando IsolationForest…")
    model = IsolationForest(
        n_estimators=100,
        max_samples="auto",
        contamination=0.01,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X)

    # 3) Validación simple: puntuaciones y percentiles
    scores = model.decision_function(X)
    print("📊 Estadísticas de scores (decision_function):")
    print(pd.Series(scores).describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]))

    # 4) Persistir el modelo
    os.makedirs(args.model_dir, exist_ok=True)
    model_path = os.path.join(args.model_dir, "iforest.pkl")
    joblib.dump(model, model_path)
    print(f"✅ Modelo guardado en {model_path}")

if __name__ == "__main__":
    main()
