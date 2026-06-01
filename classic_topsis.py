#!/usr/bin/env python3
"""
classic_topsis.py — Реалізація класичного методу TOPSIS (Hwang & Yoon, 1981)

Метод TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
ранжує альтернативи за їх геометричною близькістю до позитивного ідеального
рішення (PIS) та віддаленістю від негативного ідеального рішення (NIS).

Джерела:
  [1] C.L. Hwang, K. Yoon. Multiple Attribute Decision Making: Methods
      and Applications. Springer-Verlag, 1981.
  [2] M. Behzadian et al. A state-of-the-art survey of TOPSIS applications.
      Expert Systems with Applications, 39(17), 2012, pp. 13051–13069.
  [3] M. Madanchian, H. Taherdoost. A comprehensive guide to the TOPSIS method
      for multi-criteria decision making. Sustainable Society Development, 2023.

═══════════════════════════════════════════════════════════════════════════

СТРУКТУРА ВХІДНИХ ДАНИХ (CSV):

  Файл: results_matrix.csv

  ┌────────────┬─────────────┬───────┬──────────────┬──────────────┬──────────────┬────────────┬───────────┬────────┬────────┐
  │ framework  │ concurrency │  rps  │ latency_p50  │ latency_p95  │ latency_p99  │ error_rate │ cpu_cores │ ram_mb │ tta_ms │
  ├────────────┼─────────────┼───────┼──────────────┼──────────────┼──────────────┼────────────┼───────────┼────────┼────────┤
  │ node       │     50      │  3.87 │     2218     │    14567     │    14812     │    0.0     │   1.13    │ 134.4  │ 5226   │
  │ node       │    100      │  3.57 │     5415     │    29013     │    29452     │    0.0     │   1.42    │ 167.9  │ 14255  │
  │ fastapi    │     50      │  2.92 │    10028     │    17820     │    18128     │    0.0     │   0.53    │  43.5  │  342   │
  │ fastapi    │    100      │  2.66 │    22024     │    37788     │    38476     │    0.0     │   0.74    │  51.0  │  378   │
  │ ...        │    ...      │  ...  │     ...      │     ...      │     ...      │    ...     │   ...     │  ...   │  ...   │
  └────────────┴─────────────┴───────┴──────────────┴──────────────┴──────────────┴────────────┴───────────┴────────┴────────┘

  Опис колонок:

  framework     (str)    — назва серверної конфігурації: 'node', 'node_workers', 'fastapi'
  concurrency   (int)    — кількість одночасних користувачів: 10, 25, 50, ..., 500
  rps           (float)  — запити на секунду [benefit ↑]
  latency_p50   (float)  — медіанна латентність, мс [cost ↓]
  latency_p95   (float)  — хвостова латентність (95-й перцентиль), мс [cost ↓]
  latency_p99   (float)  — екстремальна латентність (99-й перцентиль), мс [cost ↓]
  error_rate    (float)  — відсоток помилок, % [cost ↓]
  cpu_cores     (float)  — споживання CPU, ядра [cost ↓]
  ram_mb        (float)  — споживання RAM, МБ [cost ↓]
  tta_ms        (float)  — час архівації (Time-to-Archive), мс [cost ↓]

  Для класичного TOPSIS усі рядки з однаковим framework усереднюються
  в одну альтернативу (одне значення кожної метрики на фреймворк).
  
  Додатково можуть бути присутні розрахункові колонки:
  rei           (float)  — Resource Efficiency Index = RPS / (CPU × RAM_GB) [benefit ↑]
  rps_per_core  (float)  — RPS / CPU_cores [benefit ↑]

  Якщо вони відсутні — скрипт обчислить їх автоматично.

═══════════════════════════════════════════════════════════════════════════

Використання:
    python classic_topsis.py --data results_matrix.csv
    python classic_topsis.py --data results_matrix.csv --output results/
    python classic_topsis.py --data results_matrix.csv --metrics rps,latency_p95,cpu_cores,ram_mb,tta_ms

"""
#!/usr/bin/env python3

import argparse
import os
import sys

import numpy as np
import pandas as pd


# COLUMN MAPPING

COLUMN_MAPPING = {

    "Framework": "framework",
    "RPS": "rps",

    "P50_ms": "latency_p50",
    "P95_ms": "latency_p95",
    "P99_ms": "latency_p99",

    "ErrorRate": "error_rate",

    "CPU_Usage": "cpu_cores",
    "RAM_MB": "ram_mb",

    "TTA_ms": "tta_ms",

    "Concurrency": "concurrency"
}


# BENEFIT / COST

BENEFIT_METRICS = {
    'rps',
    'rei',
    'rps_per_core'
}

COST_METRICS = {

    'latency_p50',
    'latency_p95',
    'latency_p99',

    'error_rate',

    'cpu_cores',
    'ram_mb',

    'tta_ms'
}


# DEFAULT METRICS

DEFAULT_METRICS = [

    'rps',

    'latency_p50',
    'latency_p95',
    'latency_p99',

    'error_rate',

    'cpu_cores',
    'ram_mb',

    'tta_ms',

    'rei',
    'rps_per_core'
]


# DEFAULT WEIGHTS

DEFAULT_WEIGHTS = {

    'rps': 0.20,

    'latency_p50': 0.03,
    'latency_p95': 0.10,
    'latency_p99': 0.05,

    'error_rate': 0.07,

    'cpu_cores': 0.10,
    'ram_mb': 0.05,

    'tta_ms': 0.15,

    'rei': 0.15,
    'rps_per_core': 0.10
}


# PREPARE DATA

def prepare_dataframe(df):

    df = df.rename(columns=COLUMN_MAPPING)

    # lowercase framework
    if "framework" in df.columns:

        df["framework"] = (
            df["framework"]
            .astype(str)
            .str.lower()
        )

    # numeric conversion
    for col in df.columns:

        if col != "framework":

            df[col] = (

                df[col]
                .astype(str)

                # replace decimal comma
                .str.replace(",", ".", regex=False)

                # remove spaces
                .str.strip()
            )

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    return df


# DECISION MATRIX

def prepare_decision_matrix(df, metrics):

    df = df.copy()


    # REI

    if "rei" not in df.columns:

        ram_gb = df["ram_mb"] / 1024.0

        cpu_safe = (
            df["cpu_cores"]
            .replace(0, np.nan)
        )

        ram_safe = ram_gb.replace(0, np.nan)

        df["rei"] = (
            df["rps"] /
            (cpu_safe * ram_safe)
        )

        df["rei"] = df["rei"].fillna(0)


    # RPS PER CORE

    if "rps_per_core" not in df.columns:

        cpu_safe = (
            df["cpu_cores"]
            .replace(0, np.nan)
        )

        df["rps_per_core"] = (
            df["rps"] / cpu_safe
        )

        df["rps_per_core"] = (
            df["rps_per_core"]
            .fillna(0)
        )


    # AVAILABLE METRICS

    available = [

        m for m in metrics
        if m in df.columns
    ]

    missing = set(metrics) - set(available)

    if missing:

        print("")
        print(f"Missing metrics: {missing}")


    # GROUP BY FRAMEWORK

    matrix = (

        df
        .groupby("framework")[available]
        .mean()

    )

    return matrix


# NORMALIZATION

def vector_normalize(X):

    R = X.copy()

    for col in X.columns:

        denominator = np.sqrt(
            (X[col] ** 2).sum()
        )

        if denominator > 0:

            R[col] = X[col] / denominator

        else:

            R[col] = 0.0

    return R


# WEIGHTS

def apply_weights(R, weights):

    V = R.copy()

    for col in R.columns:

        V[col] = (
            weights.get(col, 0) *
            R[col]
        )

    return V


# IDEAL SOLUTIONS

def find_ideal_solutions(V):

    A_plus = {}
    A_minus = {}

    for col in V.columns:

        if col in BENEFIT_METRICS:

            A_plus[col] = V[col].max()
            A_minus[col] = V[col].min()

        else:

            A_plus[col] = V[col].min()
            A_minus[col] = V[col].max()

    return A_plus, A_minus


# DISTANCES

def compute_distances(V, A_plus, A_minus):

    D_plus = {}
    D_minus = {}

    for alt in V.index:

        dp = np.sqrt(sum(

            (
                V.loc[alt, col] -
                A_plus[col]
            ) ** 2

            for col in V.columns
        ))

        dm = np.sqrt(sum(

            (
                V.loc[alt, col] -
                A_minus[col]
            ) ** 2

            for col in V.columns
        ))

        D_plus[alt] = dp
        D_minus[alt] = dm

    return D_plus, D_minus


# CLOSENESS

def compute_closeness(D_plus, D_minus):

    CC = {}

    for alt in D_plus:

        denominator = (
            D_plus[alt] +
            D_minus[alt]
        )

        if denominator > 0:

            CC[alt] = (
                D_minus[alt] /
                denominator
            )

        else:

            CC[alt] = 0.5

    return CC


# RANKING

def rank_alternatives(CC):

    ranking = pd.DataFrame([

        {
            "framework": alt,
            "CC": cc
        }

        for alt, cc in sorted(
            CC.items(),
            key=lambda x: x[1],
            reverse=True
        )
    ])

    ranking["rank"] = range(
        1,
        len(ranking) + 1
    )

    return ranking


# MAIN TOPSIS

def run_topsis(df):

    print("")
    print("=" * 60)
    print("TOPSIS")
    print("=" * 60)

    X = prepare_decision_matrix(
        df,
        DEFAULT_METRICS
    )

    print("")
    print("Decision matrix:")
    print(X.round(4))

    R = vector_normalize(X)

    V = apply_weights(
        R,
        DEFAULT_WEIGHTS
    )

    A_plus, A_minus = (
        find_ideal_solutions(V)
    )

    D_plus, D_minus = (
        compute_distances(
            V,
            A_plus,
            A_minus
        )
    )

    CC = compute_closeness(
        D_plus,
        D_minus
    )

    ranking = rank_alternatives(CC)

    print("")
    print("=" * 60)
    print("RANKING")
    print("=" * 60)

    for _, row in ranking.iterrows():

        fw = row["framework"]

        print(
            f"{int(row['rank'])}. "
            f"{fw:<15} "
            f"CC={row['CC']:.4f}"
        )

    return ranking


# MAIN

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        required=True
    )

    parser.add_argument(
        "--output",
        default="results"
    )

    args = parser.parse_args()

    if not os.path.exists(args.data):

        print("CSV file not found")
        sys.exit(1)


    # LOAD

    df = pd.read_csv(args.data)

    print("")
    print(f"Loaded: {args.data}")
    print(f"Rows: {len(df)}")

    print("")
    print("Original columns:")
    print(df.columns.tolist())


    # PREPARE

    df = prepare_dataframe(df)

    print("")
    print("Mapped columns:")
    print(df.columns.tolist())
    print(df.dtypes)
    print(df.head())


    # RUN

    ranking = run_topsis(df)


    # SAVE

    os.makedirs(
        args.output,
        exist_ok=True
    )

    output_file = os.path.join(
        args.output,
        "topsis_ranking.csv"
    )

    ranking.to_csv(
        output_file,
        index=False
    )

    print("")
    print(f"Saved: {output_file}")
    print("")

if __name__ == "__main__":
    main()