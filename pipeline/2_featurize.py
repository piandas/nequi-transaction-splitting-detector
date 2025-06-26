import argparse
import os
import pandas as pd
import numpy as np

def compute_intervals(group):
    times = group.sort_values("transaction_date")["transaction_date"]
    diffs = times.diff().dt.total_seconds().dropna() / 60.0
    return pd.Series({
        "avg_interval_minutes": diffs.mean() if not diffs.empty else 0,
        "std_interval_minutes": diffs.std() if len(diffs) > 1 else 0
    })

def main():
    parser = argparse.ArgumentParser(
        description="2. Featurización diaria a partir de df_clean.parquet particionado"
    )
    parser.add_argument("--date", type=str, required=True, help="YYYY-MM-DD a procesar")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/clean",
        help="Base dir de data limpia particionada"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/features",
        help="Base dir para features particionadas"
    )
    args = parser.parse_args()

    fecha = pd.to_datetime(args.date).date()
    year = f"{fecha.year:04d}"
    month = f"{fecha.month:02d}"
    day = f"{fecha.day:02d}"

    clean_path = os.path.join(
        args.input_dir,
        f"year={year}",
        f"month={month}",
        f"day={day}",
        "df_clean.parquet"
    )
    if not os.path.exists(clean_path):
        print(f"⚠️ No existe {clean_path}, se omite.")
        return

    print(f"▶️ Featurizando {fecha}")
    df = pd.read_parquet(clean_path)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    # Nos quedamos solo con débitos:
    debitos = df[df["transaction_type"] == "DEBITO"].copy()
    if debitos.empty:
        print("ℹ️ No hay débitos para este día.")
        return

    # Agrupaciones principales:
    agg = debitos.groupby("user_id").agg(
        cnt_24h=("transaction_amount", "count"),
        sum_24h=("transaction_amount", "sum"),
        avg_amount=("transaction_amount", "mean"),
        amount_std=("transaction_amount", "std"),
        unique_merchants=("merchant_id", "nunique"),
        unique_subsidiaries=("subsidiary", "nunique"),
    ).reset_index().fillna(0)

    # Coeficiente de variación y rango:
    agg["amount_cv"] = agg["amount_std"] / agg["avg_amount"].replace(0, np.nan)
    agg["amount_cv"] = agg["amount_cv"].fillna(0)
    agg["amount_range"] = debitos.groupby("user_id")["transaction_amount"].agg(
        lambda x: x.max() - x.min()
    ).values

    # Concentraciones:
    merchant_conc = debitos.groupby("user_id")["merchant_id"].apply(
        lambda x: x.value_counts().iloc[0] / len(x)
    )
    subsidiary_conc = debitos.groupby("user_id")["subsidiary"].apply(
        lambda x: x.value_counts().iloc[0] / len(x)
    )
    amount_conc = debitos.groupby("user_id")["transaction_amount"].apply(
        lambda x: x.value_counts().iloc[0] / len(x)
    )
    agg["merchant_concentration"] = agg["user_id"].map(merchant_conc)
    agg["subsidiary_concentration"] = agg["user_id"].map(subsidiary_conc)
    agg["same_amount_ratio"] = agg["user_id"].map(amount_conc)

    # Intervalos temporales:
    iv = debitos.groupby("user_id").apply(compute_intervals).reset_index()
    feat = agg.merge(iv, on="user_id", how="left")

    # Escribir particionado
    out_dir = os.path.join(
        args.output_dir,
        f"year={year}",
        f"month={month}",
        f"day={day}"
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "features.parquet")
    feat.to_parquet(out_path, index=False)
    print(f"✅ Features guardadas en {out_path}")

if __name__ == "__main__":
    main()
