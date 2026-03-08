import argparse
import glob

import pandas as pd
import plotly.io as pio
from plotly.subplots import make_subplots
import plotly.graph_objects as go


pio.renderers.default = "browser"
DEPARTURE_COLOR = "#1f77b4"
ARRIVAL_COLOR = "#ff7f0e"


def _find_csv_files(pattern):
    files = glob.glob(pattern, recursive=True)
    return [f for f in files if f.lower().endswith(".csv")]


def _read_all_csv(files):
    df_list = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df["__source_file"] = f
            df_list.append(df)
        except Exception as e:
            print(f"[skip] read failed: {f} | {e}")
    if not df_list:
        return pd.DataFrame()
    return pd.concat(df_list, ignore_index=True)


def _normalize(df):
    df.columns = df.columns.str.strip().str.lower()
    if "airport" in df.columns:
        df["airport"] = df["airport"].astype(str).str.strip().str.upper()
    if "direction" in df.columns:
        df["direction"] = df["direction"].astype(str).str.strip().str.lower()
    if "date" in df.columns:
        dt = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df["date_dt"] = dt
        df["date_key"] = dt.dt.strftime("%Y-%m-%d")
    return df


def calc_damage_ratio(pivot_df, threshold=100):
    total_days = len(pivot_df)
    if total_days == 0:
        return 0, 0, 0.0
    damaged_days = (pivot_df["diff"].abs() > threshold).sum()
    ratio = (damaged_days / total_days) * 100
    return total_days, int(damaged_days), float(ratio)


def build_daily_pivot(df_one_airport):
    summary = (
        df_one_airport.groupby(["date_key", "direction"])
        .size()
        .reset_index(name="count")
    )

    pivot = (
        summary.pivot(index="date_key", columns="direction", values="count")
        .fillna(0)
        .sort_index()
    )

    if "arrival" not in pivot.columns:
        pivot["arrival"] = 0
    if "departure" not in pivot.columns:
        pivot["departure"] = 0

    pivot["arrival"] = pivot["arrival"].astype(int)
    pivot["departure"] = pivot["departure"].astype(int)
    pivot["diff"] = pivot["departure"] - pivot["arrival"]
    return pivot


def plot_all_airports_one_page(pivots):
    codes = list(pivots.keys())
    fig = make_subplots(
        rows=len(codes),
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.04,
        subplot_titles=[f"สถิติเที่ยวบินรายวัน ({c})" for c in codes],
    )

    for row_idx, code in enumerate(codes, start=1):
        pivot = pivots[code]
        x = pivot.index.tolist()
        dep = pivot["departure"].tolist()
        arr = pivot["arrival"].tolist()

        fig.add_trace(
            go.Scatter(
                x=x,
                y=dep,
                mode="lines+markers",
                name="departure",
                line={"color": DEPARTURE_COLOR},
                marker={"color": DEPARTURE_COLOR},
                legendgroup="departure",
                showlegend=(row_idx == 1),
            ),
            row=row_idx,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=arr,
                mode="lines+markers",
                name="arrival",
                line={"color": ARRIVAL_COLOR},
                marker={"color": ARRIVAL_COLOR},
                legendgroup="arrival",
                showlegend=(row_idx == 1),
            ),
            row=row_idx,
            col=1,
        )
        fig.update_yaxes(title_text="จำนวนเที่ยวบิน", row=row_idx, col=1)

    fig.update_layout(
        title="สถิติเที่ยวบินรายวัน (ทุกสนามบิน)",
        height=max(500, 300 * len(codes)),
        hovermode="x unified",
    )
    fig.show()


def generate_charts(
    pattern="export/day/**/flightsfrom_output/flightsfrom_*.csv",
    airport=None,
    threshold=100,
):
    files = _find_csv_files(pattern)
    if not files:
        print(f"No CSV files found with pattern: {pattern}")
        return False

    print(f"Found {len(files)} CSV files")
    df = _read_all_csv(files)
    if df.empty:
        print("No readable CSV data")
        return False

    df = _normalize(df)
    required = {"airport", "direction", "date_key"}
    if not required.issubset(set(df.columns)):
        print(f"Missing required columns. Need: {sorted(required)}")
        print(f"Current columns: {list(df.columns)}")
        return False

    if airport:
        df = df[df["airport"] == airport.strip().upper()]
        if df.empty:
            print(f"No rows found for airport: {airport}")
            return False

    airports = sorted(df["airport"].dropna().unique().tolist())
    print(f"Airports to plot: {len(airports)}")

    pivots = {}
    for code in airports:
        dfx = df[df["airport"] == code].copy()
        pivot = build_daily_pivot(dfx)

        if pivot.empty:
            print(f"[skip] {code}: no daily data")
            continue
        pivots[code] = pivot

        print(f"\n=== {code} ===")
        total_days, damaged_days, ratio = calc_damage_ratio(pivot, threshold=threshold)
        print(f"จำนวนวันทั้งหมด: {total_days}")
        print(f"จำนวนวันที่ Dept. - Arriv. ห่างกันเกิน {threshold}: {damaged_days}")
        print(f"คิดเป็น {ratio:.2f}% ของข้อมูลทั้งหมด")

    if not pivots:
        print("No pivots to plot")
        return False

    plot_all_airports_one_page(pivots)
    return True


def main():
    parser = argparse.ArgumentParser(description="Plot daily flight charts by airport")
    parser.add_argument(
        "--pattern",
        default="export/day/**/flightsfrom_output/flightsfrom_*.csv",
        help="Glob pattern for CSV files (supports recursive glob)",
    )
    parser.add_argument(
        "--airport",
        default=None,
        help="Optional airport code filter, ex: BKK",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=100,
        help="Threshold for damage ratio based on abs(departure-arrival)",
    )
    args = parser.parse_args()
    generate_charts(
        pattern=args.pattern,
        airport=args.airport,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
