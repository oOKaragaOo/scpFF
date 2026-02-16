import os
import pandas as pd

# ==================================================
# CONFIG
# ==================================================

ENABLE_DAILY_DEBUG = True

EXPORT_ROOT = "export"
DEBUG_ROOT = "Debug"

COLUMN_ORDER = [
    "date",
    "day_name",
    "airport",
    "direction",
    "time",
    "destination",
    "flight",
    "airline",
    "duration",

    "time_range",
    "distance",
    "aircraft",
    "seats",
    "codeshare",
    "entertainment",
    "meals",

    "uid",
    "airline_source",
    "page_date_verified",
    "scraped_at"
]


# ==================================================
# INTERNAL HELPERS
# ==================================================

def set_daily_debug(enabled: bool):
    global ENABLE_DAILY_DEBUG
    ENABLE_DAILY_DEBUG = enabled


def _ensure_folder(path):
    os.makedirs(path, exist_ok=True)


def _build_dataframe(rows):
    df = pd.DataFrame(rows)

    existing = [c for c in COLUMN_ORDER if c in df.columns]
    return df.reindex(columns=existing)


# ==================================================
# MAIN EXPORT (MONTHLY APPEND)
# ==================================================

def append_month_rows(rows, code, month_key):
    """
    Export monthly CSV (append mode)
    path: export/<CODE>/YYYY-MM.csv
    """

    if not rows:
        return

    folder = os.path.join(EXPORT_ROOT, code)
    _ensure_folder(folder)

    full_path = os.path.join(folder, f"{month_key}.csv")

    df = _build_dataframe(rows)

    file_exists = os.path.exists(full_path)

    df.to_csv(
        full_path,
        mode="a",
        header=not file_exists,
        index=False
    )

    print(f"📦 Appended {len(df)} rows -> {full_path}")


# ==================================================
# DEBUG EXPORT (DAY)
# ==================================================

def export_day_debug(day_rows, code, date_str, mode="arrivals"):
    """
    Export debug file
    path: Debug/<CODE>/<date>_<mode>.csv
    """

    if not ENABLE_DAILY_DEBUG:
        return

    if not day_rows:
        return

    folder = os.path.join(DEBUG_ROOT, code)
    _ensure_folder(folder)

    file_name = f"{date_str}_{mode}.csv"
    full_path = os.path.join(folder, file_name)

    df = _build_dataframe(day_rows)
    df.to_csv(full_path, index=False)

    print(f"🐞 Debug export -> {full_path}")


# ==================================================
# WEEK DEBUG PICK
# ==================================================

def export_week_debug_pick(debug_pick, code):
    """
    Export 1 debug file per week
    """

    if not debug_pick or not debug_pick.get("rows"):
        return

    day = debug_pick["day"]
    kill = debug_pick.get("kill", 0)

    export_day_debug(
        debug_pick["rows"],
        code,
        day.isoformat(),
        mode=f"week_debug_k{kill}"
    )

    print(f"🏆 WEEK DEBUG PICK: {day} (kill={kill})")
