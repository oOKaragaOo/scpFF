import argparse
import glob
import os

import pandas as pd
import plotly.io as pio
from plotly.subplots import make_subplots
import plotly.graph_objects as go


pio.renderers.default = "browser"
DEPARTURE_COLOR = "#1f77b4"
ARRIVAL_COLOR = "#ff7f0e"


def _find_csv_files(pattern, airport_codes=None):
    all_files = glob.glob(pattern, recursive=True)
    csv_files = [f for f in all_files if f.lower().endswith(".csv")]
    
    # If specific airport codes are requested, filter files by airport code in path
    if airport_codes:
        codes_upper = {c.strip().upper() for c in airport_codes if str(c).strip()}
        if codes_upper:
            filtered = []
            for f in csv_files:
                # Check if any airport code appears in the file path
                if any(code in f.upper() for code in codes_upper):
                    filtered.append(f)
            if filtered:
                print(f"[filter] {len(filtered)} files match airports {sorted(codes_upper)}")
                return filtered
    
    return csv_files


def _read_csv_chunks(files, chunk_size=500):
    """อ่าน CSV แบบ chunked และ yield chunks เพื่อประมวลผลทีละ chunk"""
    total_chunks = (len(files) + chunk_size - 1) // chunk_size
    
    for chunk_idx in range(total_chunks):
        start = chunk_idx * chunk_size
        end = start + chunk_size
        chunk_files = files[start:end]
        
        chunk_df_list = []
        for f in chunk_files:
            try:
                df = pd.read_csv(f)
                df["__source_file"] = f
                chunk_df_list.append(df)
            except Exception as e:
                print(f"[skip] read failed: {f} | {e}")
        
        if chunk_df_list:
            chunk_df = pd.concat(chunk_df_list, ignore_index=True)
            print(f"[chunk] {chunk_idx + 1}/{total_chunks} processed ({len(chunk_files)} files, {len(chunk_df)} rows)")
            yield chunk_df


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


def plot_all_airports_one_page(pivots, pdf_path=None, show_in_browser=True):
    codes = list(pivots.keys())
    num_charts = len(codes)
    
    # ปรับ vertical spacing ตามจำนวน charts
    vertical_spacing = 0.05 if num_charts <= 6 else 0.03
    
    fig = make_subplots(
        rows=num_charts,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=vertical_spacing,
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
                mode="lines",
                name="departure",
                line={"color": DEPARTURE_COLOR},
                connectgaps=True,
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
                mode="lines",
                name="arrival",
                line={"color": ARRIVAL_COLOR},
                connectgaps=True,
                legendgroup="arrival",
                showlegend=(row_idx == 1),
            ),
            row=row_idx,
            col=1,
        )
        fig.update_yaxes(title_text="จำนวนเที่ยวบิน", row=row_idx, col=1)

    # เพิ่ม height และ margin ให้เหมาะสมกับจำนวน charts
    height = max(600, 420 * num_charts)
    fig.update_layout(
        title="สถิติเที่ยวบินรายวัน (ทุกสนามบิน)",
        height=height,
        hovermode="x unified",
        margin=dict(l=50, r=50, t=80, b=50),
    )
    
    if pdf_path:
        try:
            fig.write_image(pdf_path, format='pdf')
            print(f"✓ Saved: {pdf_path}")
        except Exception as e:
            print(f"❌ PDF export failed: {e}")
            print(f"   Install kaleido: pip install kaleido")
    
    if show_in_browser:
        fig.show()


def plot_all_airports_paginated(pivots, charts_per_page=12, pdf_dir=None, show_in_browser=True):
    codes = list(pivots.keys())
    if charts_per_page <= 0:
        charts_per_page = 12

    total_pages = (len(codes) + charts_per_page - 1) // charts_per_page
    for page_idx in range(total_pages):
        start = page_idx * charts_per_page
        end = start + charts_per_page
        page_codes = codes[start:end]
        page_pivots = {c: pivots[c] for c in page_codes}
        print(f"[chart] page {page_idx + 1}/{total_pages} airports={len(page_codes)}")
        
        pdf_path = None
        if pdf_dir:
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = os.path.join(pdf_dir, f"page_{page_idx + 1:03d}.pdf")
        
        plot_all_airports_one_page(page_pivots, pdf_path=pdf_path, show_in_browser=show_in_browser)


def generate_charts(
    pattern="export/day/**/flightsfrom_output/flightsfrom_*.csv",
    airport=None,
    threshold=100,
    airport_codes=None,
    run_id=None,
    charts_per_page=12,
    export_pdf=False,
):
    # Determine airport codes to filter by
    codes_to_filter = airport_codes
    if not codes_to_filter and airport:
        codes_to_filter = [airport]
    
    # Find CSV files, filtering by airport codes if specified
    files = _find_csv_files(pattern, airport_codes=codes_to_filter)
    if not files:
        print(f"No CSV files found with pattern: {pattern}")
        return False

    print(f"Found {len(files)} CSV files")
    
    # Prepare airport filter for content filtering
    airport_filter = None
    if airport:
        airport_filter = airport.strip().upper()
    elif airport_codes:
        airport_filter = {c.strip().upper() for c in airport_codes if str(c).strip()}
    
    # Process chunks and accumulate data by airport
    airport_chunks = {}  # airport_code -> list of dataframes
    pivots = {}  # airport_code -> pivot dataframe (ready to plot)
    
    for chunk_df in _read_csv_chunks(files):
        chunk_df = _normalize(chunk_df)
        
        # Filter by airport if needed
        if airport:
            chunk_df = chunk_df[chunk_df["airport"] == airport_filter]
        elif airport_codes:
            chunk_df = chunk_df[chunk_df["airport"].isin(airport_filter)]
        
        if chunk_df.empty:
            continue
        
        # Accumulate data by airport and build pivots incrementally
        for code in chunk_df["airport"].unique():
            if pd.isna(code):
                continue
            
            if code not in airport_chunks:
                airport_chunks[code] = []
            
            airport_chunks[code].append(chunk_df[chunk_df["airport"] == code])
            
            # Build/update pivot for this airport (incremental aggregation)
            df_one_airport = pd.concat(airport_chunks[code], ignore_index=True)
            pivot = build_daily_pivot(df_one_airport)
            
            if not pivot.empty:
                pivots[code] = pivot
    
    if not pivots:
        print("No data found after filtering")
        return False
    
    # Sort and display stats
    airports = sorted(pivots.keys())
    print(f"Airports to plot: {len(airports)}")
    if run_id:
        print(f"Run scope: {run_id}")
    
    for code in airports:
        pivot = pivots[code]
        print(f"\n=== {code} ===")
        total_days, damaged_days, ratio = calc_damage_ratio(pivot, threshold=threshold)
        print(f"จำนวนวันทั้งหมด: {total_days}")
        print(f"จำนวนวันที่ Dept. - Arriv. ห่างกันเกิน {threshold}: {damaged_days}")
        print(f"คิดเป็น {ratio:.2f}% ของข้อมูลทั้งหมด")
    
    # Clear chunks to free memory
    airport_chunks.clear()
    
    # Plot pages with ready pivots
    plot_all_airports_paginated(pivots, charts_per_page=charts_per_page, pdf_dir="export/charts" if export_pdf else None, show_in_browser=not export_pdf)
    
    pivots.clear()
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
    parser.add_argument(
        "--charts-per-page",
        type=int,
        default=12,
        help="Number of airport charts per page",
    )
    parser.add_argument(
        "--export-pdf",
        action="store_true",
        help="Export charts to PDF instead of rendering in browser",
    )
    args = parser.parse_args()
    generate_charts(
        pattern=args.pattern,
        airport=args.airport,
        threshold=args.threshold,
        charts_per_page=args.charts_per_page,
        export_pdf=args.export_pdf,
    )


if __name__ == "__main__":
    main()
