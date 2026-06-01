import os
import numpy as np
import pandas as pd
from scipy import stats

RESULTS_DIR = "results"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_RESULTS = os.path.join(RESULTS_DIR, "final_results.csv")

if not os.path.exists(FINAL_RESULTS):
    raise FileNotFoundError(
        f"File not found: {FINAL_RESULTS}"
    )

# LOAD DATA

df = pd.read_csv(FINAL_RESULTS)

# normalize columns
df.columns = [
    c.strip().replace('"', '')
    for c in df.columns
]

# normalize framework names
df["Framework"] = (
    df["Framework"]
    .astype(str)
    .str.strip()
    .str.replace('"', '', regex=False)
    .str.lower()
)
print("\nFramework values:")
print(df["Framework"].unique())

# numeric conversion
numeric_cols = [
    "VCPU",
    "Concurrency",
    "Run",
    "RPS",
    "P50_ms",
    "P95_ms",
    "P99_ms",
    "ErrorRate",
    "TTA_ms",
    "CPU_Usage",
    "RAM_MB"
]

for col in numeric_cols:

    if col in df.columns:

        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

# drop broken rows
df = df.dropna(
    subset=[
        "Framework",
        "VCPU",
        "Concurrency",
        "Run"
    ]
)

print("\nLoaded rows:", len(df))
print(df.head())

# SAVE CLEAN RAW DATA

df.to_csv(
    os.path.join(OUTPUT_DIR, "raw_data.csv"),
    index=False
)

# OUTLIER DETECTION

def grubbs_remove(data, alpha=0.05):

    data = list(data)
    removed = []

    while len(data) >= 3:

        arr = np.array(data)

        mean = np.mean(arr)
        std = np.std(arr, ddof=1)

        if std == 0 or np.isnan(std):
            break

        diffs = np.abs(arr - mean)

        max_idx = np.argmax(diffs)

        G = diffs[max_idx] / std

        n = len(arr)

        t = stats.t.ppf(
            1 - alpha / (2 * n),
            n - 2
        )

        G_crit = (
            ((n - 1) / np.sqrt(n))
            * np.sqrt(
                t**2 / (n - 2 + t**2)
            )
        )

        if G > G_crit:

            removed.append(arr[max_idx])

            data.pop(max_idx)

        else:
            break

    return np.array(data), removed


def detect_outlier_reason(metric, value, mean):

    if metric == "RPS":

        if value < mean * 0.7:
            return "Possible saturation"

        if value > mean * 1.3:
            return "Unusually high throughput"

    if metric in ["P95_ms", "P99_ms"]:

        if value > mean * 1.5:
            return "Latency spike"

    if metric == "ErrorRate":

        if value > 0:
            return "Request failures"

    return "Unknown"


# AGGREGATED STATISTICS

metrics = [
    "RPS",
    "P50_ms",
    "P95_ms",
    "P99_ms",
    "ErrorRate",
    "TTA_ms",
    "CPU_Usage",
    "RAM_MB"
]

results = []
outliers = []

grouped = df.groupby(
    ["Framework", "VCPU", "Concurrency"]
)

for name, group in grouped:

    framework, vcpu, concurrency = name

    for metric in metrics:

        values = (
            group[metric]
            .dropna()
            .values
        )

        if len(values) < 2:
            continue

        clean_values, removed = grubbs_remove(values)

        if len(clean_values) < 1:
            continue

        if len(removed) > 0:

            reasons = [
                detect_outlier_reason(
                    metric,
                    val,
                    np.mean(values)
                )
                for val in removed
            ]

            outliers.append({
                "Framework": framework,
                "VCPU": vcpu,
                "Concurrency": concurrency,
                "Metric": metric,
                "Removed": removed,
                "Reasons": reasons
            })

        n = len(clean_values)

        mean = np.mean(clean_values)
        median = np.median(clean_values)

        if n > 1:
            std = np.std(
                clean_values,
                ddof=1
            )
        else:
            std = 0

        min_v = np.min(clean_values)
        max_v = np.max(clean_values)

        # 95% CI

        if n > 1 and std > 0:

            t_val = stats.t.ppf(
                0.975,
                n - 1
            )

            ci = (
                t_val
                * std
                / np.sqrt(n)
            )

        else:
            ci = 0

        # normality

        try:

            if n >= 3 and std > 0:

                shapiro_p = stats.shapiro(
                    clean_values
                )[1]

            else:
                shapiro_p = 1.0

        except:
            shapiro_p = 1.0

        results.append({

            "Framework": framework,
            "VCPU": vcpu,
            "Concurrency": concurrency,
            "Metric": metric,

            "N": n,

            "Mean": round(mean, 4),
            "Median": round(median, 4),
            "Std": round(std, 4),

            "Min": round(min_v, 4),
            "Max": round(max_v, 4),

            "CI95_Low": round(mean - ci, 4),
            "CI95_High": round(mean + ci, 4),

            "Shapiro_p": round(shapiro_p, 6),

            "UseMedian": (
                shapiro_p < 0.05
            ),

            "OutliersRemoved": len(removed)
        })

df_stats = pd.DataFrame(results)

df_stats.to_csv(
    os.path.join(OUTPUT_DIR, "stats.csv"),
    index=False
)

print("\nSaved stats.csv")

# OUTLIER LOG

df_outliers = pd.DataFrame(outliers)

df_outliers.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "outliers_log.csv"
    ),
    index=False
)

print("Saved outliers_log.csv")

# COMPARISON TESTS

comparisons = []

for (vcpu, concurrency), group in df.groupby(
    ["VCPU", "Concurrency"]
):

    node = (
        group[
            group["Framework"] == "node"
        ]["RPS"]
        .dropna()
    )

    fastapi = (
        group[
            group["Framework"] == "fastapi"
        ]["RPS"]
        .dropna()
    )

    if len(node) < 2 or len(fastapi) < 2:
        continue

    try:

        u, p = stats.mannwhitneyu(
            node,
            fastapi,
            alternative="two-sided"
        )

    except:
        p = np.nan

    pooled_std = np.sqrt(
        (
            np.var(node, ddof=1)
            + np.var(fastapi, ddof=1)
        ) / 2
    )

    if pooled_std == 0 or np.isnan(pooled_std):

        d = 0

    else:

        d = (
            np.mean(node)
            - np.mean(fastapi)
        ) / pooled_std

    comparisons.append({

        "VCPU": vcpu,
        "Concurrency": concurrency,

        "Node_RPS_Mean": round(
            np.mean(node),
            4
        ),

        "FastAPI_RPS_Mean": round(
            np.mean(fastapi),
            4
        ),

        "P_Value": round(p, 6),

        "Cohen_d": round(d, 4)
    })

df_cmp = pd.DataFrame(comparisons)

df_cmp.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "comparisons.csv"
    ),
    index=False
)

print("Saved comparisons.csv")

# DEGRADATION DETECTION

degradation = []

fastapi = df[
    df["Framework"] == "fastapi"
]

for vcpu, group in fastapi.groupby("VCPU"):

    agg = (
        group.groupby("Concurrency")["RPS"]
        .mean()
        .reset_index()
        .sort_values("Concurrency")
    )

    peak_rps = agg["RPS"].max()

    threshold = peak_rps * 0.8

    degraded = agg[
        agg["RPS"] < threshold
    ]

    if len(degraded) > 0:

        degradation_point = degraded.iloc[0]

        degradation.append({

            "VCPU": vcpu,

            "Peak_RPS": round(
                peak_rps,
                4
            ),

            "Threshold_80pct": round(
                threshold,
                4
            ),

            "C_star": int(
                degradation_point["Concurrency"]
            )
        })

    else:

        degradation.append({

            "VCPU": vcpu,

            "Peak_RPS": round(
                peak_rps,
                4
            ),

            "Threshold_80pct": round(
                threshold,
                4
            ),

            "C_star": "NOT_REACHED"
        })
        
df_deg = pd.DataFrame(degradation)

df_deg.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "degradation.csv"
    ),
    index=False
)

print("Saved degradation.csv")

# LaTeX TABLES

with open(
    os.path.join(
        OUTPUT_DIR,
        "table_stats.tex"
    ),
    "w",
    encoding="utf-8"
) as f:

    f.write(
        df_stats.to_latex(
            index=False,
            escape=False
        )
    )

with open(
    os.path.join(
        OUTPUT_DIR,
        "table_comparisons.tex"
    ),
    "w",
    encoding="utf-8"
) as f:

    f.write(
        df_cmp.to_latex(
            index=False,
            escape=False
        )
    )

print("Saved LaTeX tables")

# SUMMARY

summary = {

    "total_rows": len(df),

    "frameworks": sorted(
        df["Framework"].unique().tolist()
    ),

    "vcpu_values": sorted(
        df["VCPU"].unique().tolist()
    ),

    "concurrency_values": sorted(
        df["Concurrency"].unique().tolist()
    ),

    "runs": sorted(
        df["Run"].unique().tolist()
    )
}

summary_df = pd.DataFrame([summary])

summary_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "summary.csv"
    ),
    index=False
)

print("\n===================================")
print("Analysis complete")
print("===================================")

print(f"Rows loaded      : {len(df)}")
print(f"Stats rows       : {len(df_stats)}")
print(f"Comparisons      : {len(df_cmp)}")
print(f"Outlier groups   : {len(df_outliers)}")
print(f"Degradation rows : {len(df_deg)}")

print("\nSaved to:")
print(OUTPUT_DIR)