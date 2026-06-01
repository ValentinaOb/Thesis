import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from classic_topsis import COST_METRICS

from classic_topsis import (

    prepare_dataframe,
    prepare_decision_matrix,

    vector_normalize,
    apply_weights,

    find_ideal_solutions,

    compute_distances,
    compute_closeness,

    DEFAULT_METRICS,
    DEFAULT_WEIGHTS,

    BENEFIT_METRICS
)


# STYLE

sns.set_theme(style="whitegrid")

PLOT_DPI = 300


# HELPERS

def save_plot(output_dir, filename):

    path = os.path.join(
        output_dir,
        filename
    )

    plt.tight_layout()

    plt.savefig(
        path,
        dpi=PLOT_DPI,
        bbox_inches="tight"
    )

    print(f"Saved: {path}")

    plt.close()


def pretty_metric_name(metric):

    mapping = {

        "rps": "RPS",

        "latency_p50": "P50",
        "latency_p95": "P95",
        "latency_p99": "P99",

        "error_rate": "Error Rate",

        "cpu_cores": "CPU",
        "ram_mb": "RAM",

        "tta_ms": "TTA",

        "rei": "REI",

        "rps_per_core": "RPS/Core"
    }

    return mapping.get(
        metric,
        metric
    )


# 1. DECISION MATRIX HEATMAP

def plot_decision_matrix_heatmap(
    X,
    output_dir
):

    plt.figure(figsize=(14, 6))

    sns.heatmap(
        X,
        annot=True,
        fmt=".3f",
        cmap="icefire",
        linewidths=0.5,
        linecolor="white"
    )

    plt.title(
        "Decision Matrix Heatmap (Raw Means)"
    )

    plt.xlabel("Metrics")
    plt.ylabel("Framework")

    save_plot(
        output_dir,
        "01_decision_matrix_heatmap.png"
    )


# 2. NORMALIZED MATRIX HEATMAP

def plot_normalized_matrix_heatmap(
    R,
    output_dir
):

    plt.figure(figsize=(14, 6))

    sns.heatmap(
        R,
        annot=True,
        fmt=".3f",

        cmap="YlGnBu",

        linewidths=0.5,
        linecolor="white",

        vmin=0
    )

    plt.title(
        "Normalized Matrix Heatmap"
    )

    plt.xlabel("Metrics")
    plt.ylabel("Framework")

    save_plot(
        output_dir,
        "02_normalized_matrix_heatmap.png"
    )


# 3. WEIGHTED MATRIX HEATMAP

def plot_weighted_matrix_heatmap(
    V,
    output_dir
):

    plt.figure(figsize=(14, 6))

    sns.heatmap(
        V,
        annot=True,
        fmt=".3f",

        cmap="coolwarm",

        linewidths=0.5,
        linecolor="white"
    )

    plt.title(
        "Weighted Normalized Matrix Heatmap"
    )

    plt.xlabel("Metrics")
    plt.ylabel("Framework")

    save_plot(
        output_dir,
        "03_weighted_matrix_heatmap.png"
    )


# 4. IDEAL / ANTI-IDEAL

def plot_ideal_solutions(
    V,
    A_plus,
    A_minus,
    output_dir
):

    metrics = list(V.columns)

    y = np.arange(len(metrics))

    plus_values = []
    minus_values = []

    plus_labels = []
    minus_labels = []

    for m in metrics:

        plus_values.append(
            A_plus[m]
        )

        minus_values.append(
            A_minus[m]
        )

        # benefit metric
        if m in BENEFIT_METRICS:

            plus_fw = V[m].idxmax()
            minus_fw = V[m].idxmin()

        # cost metric
        else:

            plus_fw = V[m].idxmin()
            minus_fw = V[m].idxmax()

        plus_labels.append(
            plus_fw
        )

        minus_labels.append(
            minus_fw
        )

    plt.figure(figsize=(13, 8))

    bar_width = 0.4

    bars1 = plt.barh(
        y - bar_width / 2,
        plus_values,
        height=bar_width,
        label="Ideal (A+)"
    )

    bars2 = plt.barh(
        y + bar_width / 2,
        minus_values,
        height=bar_width,
        label="Anti-Ideal (A-)"
    )

    # annotations

    for i, b in enumerate(bars1):

        plt.text(
            b.get_width(),
            b.get_y() + b.get_height() / 2,
            f" {plus_labels[i]}",
            va="center"
        )

    for i, b in enumerate(bars2):

        plt.text(
            b.get_width(),
            b.get_y() + b.get_height() / 2,
            f" {minus_labels[i]}",
            va="center"
        )

    plt.yticks(
        y,
        [
            pretty_metric_name(m)
            for m in metrics
        ]
    )

    plt.xlabel("Weighted Value")

    plt.title(
        "Ideal vs Anti-Ideal Solutions"
    )

    plt.legend()

    save_plot(
        output_dir,
        "04_ideal_antiideal_bar_chart.png"
    )


# 5. DISTANCE & CC

def plot_distance_cc_chart(
    D_plus,
    D_minus,
    CC,
    output_dir
):

    frameworks = list(CC.keys())

    x = np.arange(
        len(frameworks)
    )

    width = 0.25

    dp_vals = [
        D_plus[f]
        for f in frameworks
    ]

    dm_vals = [
        D_minus[f]
        for f in frameworks
    ]

    cc_vals = [
        CC[f]
        for f in frameworks
    ]

    plt.figure(figsize=(12, 6))

    plt.bar(
        x - width,
        dp_vals,
        width,
        label="D+"
    )

    plt.bar(
        x,
        dm_vals,
        width,
        label="D-"
    )

    plt.bar(
        x + width,
        cc_vals,
        width,
        label="CC"
    )

    plt.xticks(
        x,
        frameworks
    )

    plt.ylabel("Value")

    plt.title(
        "TOPSIS Distances and Closeness Coefficient"
    )

    plt.legend()

    save_plot(
        output_dir,
        "05_distance_cc_bar_chart.png"
    )


# 6. RADAR CHART

def plot_radar_chart(
    V,
    output_dir
):

    labels = [

        pretty_metric_name(c)

        for c in V.columns
    ]

    num_vars = len(labels)

    angles = np.linspace(
        0,
        2 * np.pi,
        num_vars,
        endpoint=False
    ).tolist()

    angles += angles[:1]

    fig, ax = plt.subplots(

        figsize=(9, 9),

        subplot_kw=dict(
            polar=True
        )
    )

    for framework in V.index:

        values = (
            V.loc[framework]
            .tolist()
        )

        values += values[:1]

        ax.plot(
            angles,
            values,
            linewidth=2,
            label=framework
        )

        ax.fill(
            angles,
            values,
            alpha=0.15
        )

    ax.set_xticks(
        angles[:-1]
    )

    ax.set_xticklabels(
        labels
    )

    plt.title(
        "Radar Chart of Weighted Normalized Metrics",
        y=1.08
    )

    plt.legend(
        loc="upper right",
        bbox_to_anchor=(1.25, 1.1)
    )

    save_plot(
        output_dir,
        "06_radar_chart.png"
    )


def prepare_visual_normalized_matrix(R):

    R_vis = R.copy()

    # invert cost metrics for visualization only
    for col in R_vis.columns:

        if col in COST_METRICS:

            max_val = R_vis[col].max()

            if max_val > 0:

                R_vis[col] = (
                    max_val - R_vis[col]
                )

    return R_vis

# MAIN

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        required=True
    )

    parser.add_argument(
        "--output",
        default="topsis_plots"
    )

    args = parser.parse_args()

    os.makedirs(
        args.output,
        exist_ok=True
    )

    # LOAD

    df = pd.read_csv(args.data)

    df = prepare_dataframe(df)

    # TOPSIS

    X = prepare_decision_matrix(
        df,
        DEFAULT_METRICS
    )

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

    # SAVE ORIGINAL METRIC NAMES
    # IMPORTANT:
    # do NOT overwrite V.columns

    X_plot = X.copy()
    V_plot = V.copy()

    X_plot.columns = [

        pretty_metric_name(c)

        for c in X_plot.columns
    ]

    # visualization-friendly normalized matrix
    # where bigger = better

    R_plot = prepare_visual_normalized_matrix(R)

    R_plot.columns = [

        pretty_metric_name(c)

        for c in R_plot.columns
    ]

    V_plot.columns = [

        pretty_metric_name(c)

        for c in V_plot.columns
    ]

    # PLOTS

    plot_decision_matrix_heatmap(
        X_plot,
        args.output
    )

    plot_normalized_matrix_heatmap(
        R_plot,
        args.output
    )

    plot_weighted_matrix_heatmap(
        V_plot,
        args.output
    )

    plot_ideal_solutions(
        V,
        A_plus,
        A_minus,
        args.output
    )

    plot_distance_cc_chart(
        D_plus,
        D_minus,
        CC,
        args.output
    )

    plot_radar_chart(
        V_plot,
        args.output
    )

    print("")
    print("=" * 30)
    print("ALL PLOTS GENERATED")
    print("=" * 30)
    print("")


if __name__ == "__main__":
    main()