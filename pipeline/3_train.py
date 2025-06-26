import argparse
import os
import glob
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

def load_features(feat_dir, start_date, end_date):
    dates = pd.date_range(start=start_date, end=end_date).date
    files = []
    for d in dates:
        y,m,d_ = d.year, f"{d.month:02d}", f"{d.day:02d}"
        path = os.path.join(
            feat_dir,
            f"year={y}",
            f"month={m}",
            f"day={d_}",
            "features.parquet"
        )
        if os.path.exists(path):
            files.append(path)
    if not files:
        raise FileNotFoundError("No se encontraron features en el rango dado.")
    dfs = [pd.read_parquet(f) for f in files]
    return pd.concat(dfs, ignore_index=True)

def main():
    parser = argparse.ArgumentParser(
        description="3. Entrenamiento de IsolationForest con todo el histórico de features."
    )
    parser.add_argument(
        "--start-date", type=str, required=True, help="YYYY-MM-DD inicio del rango histórico"
    )
    parser.add_argument(
        "--end-date", type=str, required=True, help="YYYY-MM-DD fin del rango histórico"
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

    print(f"▶️ Cargando features de {args.start_date} a {args.end_date}")
    df = load_features(args.features_dir, args.start_date, args.end_date)

    X = df.drop(columns=["user_id"], errors="ignore")
    print(f"🔧 Matriz X: {X.shape[0]} muestras × {X.shape[1]} features")

    print("🎯 Entrenando IsolationForest…")
    model = IsolationForest(n_estimators=100, max_samples="auto", contamination=0.01, random_state=42)
    model.fit(X)

    os.makedirs(args.model_dir, exist_ok=True)
    model_path = os.path.join(args.model_dir, "iforest.pkl")
    joblib.dump(model, model_path)
    print(f"✅ Modelo guardado en {model_path}")

if __name__ == "__main__":
    main()
