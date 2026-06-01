import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

RESULT_DIR = "results"

# ARGUMENTS

if len(sys.argv) < 2:
    print("Usage:")
    print("python analyze_endurance.py node")
    sys.exit(1)

framework = sys.argv[1]

# FILES

metrics_csv = os.path.join(
    RESULT_DIR,
    f"endurance_metrics_{framework}.csv"
)

history_csv = os.path.join(
    RESULT_DIR,
    f"endurance_{framework}_stats_history.csv"
)

ram_graph = os.path.join(
    RESULT_DIR,
    f"ram_timeseries_{framework}.png"
)

latency_graph = os.path.join(
    RESULT_DIR,
    f"latency_timeseries_{framework}.png"
)

rps_graph = os.path.join(
    RESULT_DIR,
    f"rps_timeseries_{framework}.png"
)

# LOAD HISTORY CSV

print("")
print("====================================")
print("ENDURANCE ANALYSIS")
print("====================================")
print("")

print(f"Framework: {framework}")

if not os.path.exists(history_csv):

    print("History CSV missing!")
    print(history_csv)

    sys.exit(1)

print("")
print("Loading history CSV...")

history = pd.read_csv(history_csv)

print("")
print("Columns:")
print(history.columns.tolist())

print("")
print(f"Rows: {len(history)}")

# TIMESTAMP

timestamp_col = None

for col in history.columns:

    if "timestamp" in col.lower():

        timestamp_col = col
        break

if not timestamp_col:

    print("Timestamp column not found!")
    sys.exit(1)

print(f"Timestamp column: {timestamp_col}")

history[timestamp_col] = pd.to_datetime(
    history[timestamp_col],
    unit="s",
    errors="coerce"
)

history = history.dropna(
    subset=[timestamp_col]
)

# FILTER UPLOAD ENDPOINT

filtered = history.copy()

if "Name" in history.columns:

    upload_rows = history[
        history["Name"].astype(str)
        .str.contains("upload", case=False, na=False)
    ]

    if len(upload_rows) > 0:

        filtered = upload_rows

        print("")
        print(f"Upload rows found: {len(filtered)}")

    else:

        print("")
        print("Upload rows not found")
        print("Using all rows")

else:

    print("")
    print("Name column missing")
    print("Using all rows")

# REMOVE NaN

filtered = filtered.fillna(0)

# FIND LATENCY COLUMN

latency_col = None

possible_latency = [

    "95%",
    "95%ile",
    "Average Response Time",
    "Avg Response Time",
    "Median Response Time"
]

for col in possible_latency:

    if col in filtered.columns:

        latency_col = col
        break

print("")
print(f"Latency column: {latency_col}")

# LATENCY GRAPH

if latency_col:

    latency_data = pd.to_numeric(
        filtered[latency_col],
        errors="coerce"
    ).fillna(0)

    plt.figure(figsize=(14, 6))

    plt.plot(
        filtered[timestamp_col],
        latency_data
    )

    plt.xlabel("Time")
    plt.ylabel("Latency (ms)")

    plt.title(
        f"Latency Over Time ({framework})"
    )

    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig(latency_graph)

    print(f"Saved: {latency_graph}")

else:

    print("Latency column not found")

# FIND RPS COLUMN

rps_col = None

possible_rps = [

    "Requests/s",
    "Current RPS",
    "Total RPS"
]

for col in possible_rps:

    if col in filtered.columns:

        rps_col = col
        break

print("")
print(f"RPS column: {rps_col}")

# RPS GRAPH

if rps_col:

    rps_data = pd.to_numeric(
        filtered[rps_col],
        errors="coerce"
    ).fillna(0)

    plt.figure(figsize=(14, 6))

    plt.plot(
        filtered[timestamp_col],
        rps_data
    )

    plt.xlabel("Time")
    plt.ylabel("RPS")

    plt.title(
        f"RPS Over Time ({framework})"
    )

    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig(rps_graph)

    print(f"Saved: {rps_graph}")

else:

    print("RPS column not found")

# RAM GRAPH

if os.path.exists(metrics_csv):

    print("")
    print("Loading metrics CSV...")

    metrics = pd.read_csv(metrics_csv)

    print(f"Metrics rows: {len(metrics)}")

    metrics["timestamp"] = pd.to_datetime(
        metrics["timestamp"],
        errors="coerce"
    )

    metrics = metrics.dropna(
        subset=["timestamp"]
    )

    metrics["ram_mb"] = pd.to_numeric(
        metrics["ram_mb"],
        errors="coerce"
    ).fillna(0)

    if len(metrics) > 0:

        plt.figure(figsize=(14, 6))

        plt.plot(
            metrics["timestamp"],
            metrics["ram_mb"]
        )

        plt.xlabel("Time")
        plt.ylabel("RAM (MB)")

        plt.title(
            f"RAM Usage Over Time ({framework})"
        )

        plt.xticks(rotation=45)

        plt.tight_layout()

        plt.savefig(ram_graph)

        print(f"Saved: {ram_graph}")

        # MEMORY ANALYSIS

        ram_start = metrics["ram_mb"].iloc[0]
        ram_end = metrics["ram_mb"].iloc[-1]

        growth = ram_end - ram_start

        print("")
        print("====================================")
        print("MEMORY ANALYSIS")
        print("====================================")

        print(f"RAM Start : {ram_start:.2f} MB")
        print(f"RAM End   : {ram_end:.2f} MB")
        print(f"Growth    : {growth:.2f} MB")

        if growth > 200:

            print("")
            print("Potential memory leak detected")

        else:

            print("")
            print("No obvious memory leak")

else:

    print("")
    print("Metrics CSV missing")
    print("Skipping RAM graph")

print("")
print("Analysis completed")
print("")