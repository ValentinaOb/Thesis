# analyze.py

import os
import re
import glob
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

RESULTS_DIR = "results"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# LOAD final_results.csv

df = pd.read_csv(
    os.path.join(RESULTS_DIR, "final_results.csv"),
    decimal=","
)

# normalize column names
df.columns = [c.strip().replace('"', '') for c in df.columns]

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
        df[col] = pd.to_numeric(df[col], errors="coerce")


# remove RAM outliers using IQR
q1 = df["RAM_MB"].quantile(0.25)
q3 = df["RAM_MB"].quantile(0.75)

iqr = q3 - q1

upper = q3 + 1.5 * iqr

df.loc[df["RAM_MB"] > upper, "RAM_MB"] = np.nan

# HELPERS

def ci95(series):
    """
    95% confidence interval
    """
    s = series.dropna()

    if len(s) <= 1:
        return 0

    return 1.96 * s.std(ddof=1) / np.sqrt(len(s))


def save_fig(name):
    plt.tight_layout()
    plt.savefig(
        os.path.join(OUTPUT_DIR, name),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()


frameworks = df["Framework"].unique()


# AGGREGATED STATS

agg = (
    df.groupby(["Framework", "VCPU", "Concurrency"])
    .agg({
        "RPS": ["mean", ci95],
        "P95_ms": ["mean", ci95],
        "CPU_Usage": ["mean", ci95],
        "RAM_MB": ["mean", "min", "max"],
        "TTA_ms": ["mean", ci95]
    })
)

agg.columns = [
    "_".join([str(x) for x in col]).strip("_")
    for col in agg.columns
]

agg = agg.reset_index()


# FIGURE 1
# RPS vs Concurrency

plt.figure(figsize=(10, 6))

for fw in frameworks:

    sub = agg[
        (agg["Framework"] == fw) &
        (agg["VCPU"] == 4)
    ].sort_values("Concurrency")

    plt.errorbar(
        sub["Concurrency"],
        sub["RPS_mean"],
        yerr=sub["RPS_ci95"],
        marker="o",
        capsize=4,
        label=fw
    )

# деградація FastAPI
fastapi = agg[
    (agg["Framework"] == "fastapi") &
    (agg["VCPU"] == 4)
].sort_values("Concurrency")

if len(fastapi) > 1:

    peak_idx = fastapi["RPS_mean"].idxmax()
    degradation_point = fastapi.loc[peak_idx, "Concurrency"]

    plt.axvline(
        degradation_point,
        linestyle="--",
        label=f"FastAPI degradation ({degradation_point})"
    )

plt.xlabel("Concurrency")
plt.ylabel("RPS")
plt.title("RPS vs Concurrency")
plt.legend()
plt.grid(True)

save_fig("fig1_rps_vs_concurrency.png")


# FIGURE 2
# P95 Latency vs Concurrency

plt.figure(figsize=(10, 6))

node_curve = None
fastapi_curve = None

for fw in frameworks:

    sub = agg[
        (agg["Framework"] == fw) &
        (agg["VCPU"] == 4)
    ].sort_values("Concurrency")

    x = sub["Concurrency"]
    y = sub["P95_ms_mean"]
    ci = sub["P95_ms_ci95"]

    plt.plot(x, y, marker="o", label=fw)

    plt.fill_between(
        x,
        y - ci,
        y + ci,
        alpha=0.2
    )

    if fw == "node":
        node_curve = sub

    if fw == "fastapi":
        fastapi_curve = sub

# crossover point
if node_curve is not None and fastapi_curve is not None:

    merged = pd.merge(
        node_curve,
        fastapi_curve,
        on="Concurrency",
        suffixes=("_node", "_fastapi")
    )

    merged["diff"] = (
        merged["P95_ms_mean_fastapi"]
        - merged["P95_ms_mean_node"]
    )

    crossover = merged.iloc[
        (merged["diff"]).abs().argsort()[:1]
    ]

    cross_x = crossover["Concurrency"].values[0]

    plt.axvline(
        cross_x,
        linestyle="--",
        label=f"Crossover ≈ {cross_x}"
    )

plt.xlabel("Concurrency")
plt.ylabel("P95 latency (ms)")
plt.title("Latency p95 vs Concurrency")
plt.legend()
plt.grid(True)

save_fig("fig2_p95_vs_concurrency.png")


# FIGURE 3
# Latency distribution boxplot

for fw in frameworks:

    sub = df[
        (df["Framework"] == fw) &
        (df["VCPU"] == 4)
    ]

    concurrencies = sorted(sub["Concurrency"].unique())

    data = [
        sub[sub["Concurrency"] == c]["P95_ms"].dropna()
        for c in concurrencies
    ]

    plt.figure(figsize=(12, 6))

    plt.boxplot(
        data,
        tick_labels=concurrencies
    )

    plt.xlabel("Concurrency")
    plt.ylabel("P95 latency (ms)")
    plt.title(f"{fw} latency distribution")

    plt.grid(True)

    save_fig(f"fig3_boxplot_{fw}.png")


# FIGURE 4
# CPU usage

vcpu = 4

sub = agg[agg["VCPU"] == vcpu]

concurrency_levels = sorted(sub["Concurrency"].unique())

x = np.arange(len(concurrency_levels))
width = 0.35

plt.figure(figsize=(12, 6))

for i, fw in enumerate(frameworks):

    fw_data = sub[sub["Framework"] == fw].sort_values("Concurrency")

    offset = (i - 0.5) * width

    plt.bar(
        x + offset,
        fw_data["CPU_Usage_mean"],
        width=width,
        yerr=fw_data["CPU_Usage_ci95"],
        capsize=4,
        label=fw
    )

plt.xticks(x, concurrency_levels)

plt.xlabel("Concurrency")
plt.ylabel("CPU Usage (%)")
plt.title("CPU Usage vs Concurrency")
plt.legend()
plt.grid(True)

save_fig("fig4_cpu_usage.png")


# FIGURE 5
# RAM usage

plt.figure(figsize=(10, 6))

for fw in frameworks:

    sub = agg[
        (agg["Framework"] == fw) &
        (agg["VCPU"] == 4)
    ].sort_values("Concurrency")

    x = sub["Concurrency"]
    y = sub["RAM_MB_mean"]

    plt.plot(
        x,
        y,
        marker="o",
        label=fw
    )

    plt.fill_between(
        x,
        sub["RAM_MB_min"],
        sub["RAM_MB_max"],
        alpha=0.2
    )

plt.xlabel("Concurrency")
plt.ylabel("RAM (MB)")
plt.title("RAM Usage vs Concurrency")
plt.legend()
plt.grid(True)

save_fig("fig5_ram_usage.png")


# FIGURE 6
# TTA distribution

for fw in frameworks:

    sub = df[
        (df["Framework"] == fw) &
        (df["VCPU"] == 4)
    ]

    concurrencies = sorted(sub["Concurrency"].unique())

    data = [
        sub[sub["Concurrency"] == c]["TTA_ms"].dropna()
        for c in concurrencies
    ]

    plt.figure(figsize=(12, 6))

    plt.violinplot(
        data,
        showmeans=True,
        showmedians=True
    )

    plt.xticks(
        np.arange(1, len(concurrencies) + 1),
        concurrencies
    )

    plt.xlabel("Concurrency")
    plt.ylabel("TTA (ms)")
    plt.title(f"{fw} TTA distribution")

    plt.grid(True)

    save_fig(f"fig6_tta_{fw}.png")


# FIGURE 7
# Throughput efficiency

plt.figure(figsize=(10, 6))

for fw in frameworks:

    sub = agg[
        (agg["Framework"] == fw) &
        (agg["VCPU"] == 4)
    ].sort_values("Concurrency")

    efficiency = (
        sub["RPS_mean"] / sub["Concurrency"]
    ) * 100

    plt.plot(
        sub["Concurrency"],
        efficiency,
        marker="o",
        label=fw
    )

plt.xlabel("Concurrency")
plt.ylabel("RPS / Concurrency × 100")
plt.title("Throughput efficiency")
plt.legend()
plt.grid(True)

save_fig("fig7_throughput_efficiency.png")


# FIGURE 8
# Heatmap

for fw in frameworks:

    sub = agg[agg["Framework"] == fw]

    pivot = sub.pivot_table(
        index="VCPU",
        columns="Concurrency",
        values="RPS_mean"
    )

    plt.figure(figsize=(12, 6))

    plt.imshow(
        pivot,
        aspect="auto"
    )

    plt.colorbar(label="RPS")

    plt.xticks(
        range(len(pivot.columns)),
        pivot.columns
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index
    )

    plt.xlabel("Concurrency")
    plt.ylabel("vCPU")
    plt.title(f"{fw} vCPU scaling heatmap")

    save_fig(f"fig8_heatmap_{fw}.png")

print("\nAll figures generated successfully.")
print(f"Saved to: {OUTPUT_DIR}")