import os
import pandas as pd
from datetime import timedelta

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


def _append_csv(rows, full_path):
    """
    core append logic
    """

    if not rows:
        return

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
# MAIN EXPORT
# ==================================================

def append_day_rows(rows, code, date_key):
    """
    path: export/<CODE>/daily/YYYY-MM-DD.csv
    """

    if not rows:
        return

    folder = os.path.join(EXPORT_ROOT, code, "daily")
    _ensure_folder(folder)

    full_path = os.path.join(folder, f"{date_key}.csv")

    _append_csv(rows, full_path)


def append_week_rows(rows, code, week_key):
    """
    path: export/<CODE>/weekly/YYYY-Wxx.csv
    """

    if not rows:
        return

    folder = os.path.join(EXPORT_ROOT, code, "weekly")
    _ensure_folder(folder)

    full_path = os.path.join(folder, f"{week_key}.csv")

    _append_csv(rows, full_path)


def append_month_rows(rows, code, month_key):
    """
    path: export/<CODE>/YYYY-MM.csv
    (ของเดิม — ยังใช้งานได้เหมือนเดิม)
    """

    if not rows:
        return

    folder = os.path.join(EXPORT_ROOT, code)
    _ensure_folder(folder)

    full_path = os.path.join(folder, f"{month_key}.csv")

    _append_csv(rows, full_path)


def append_year_rows(rows, code, year_key):
    """
    path: export/<CODE>/yearly/YYYY.csv
    """

    if not rows:
        return

    folder = os.path.join(EXPORT_ROOT, code, "yearly")
    _ensure_folder(folder)

    full_path = os.path.join(folder, f"{year_key}.csv")

    _append_csv(rows, full_path)


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

    # กัน None / empty
    if not debug_pick:
        return

    rows = debug_pick.get("rows")
    day = debug_pick.get("day")

    if not rows or day is None:
        return

    # ⭐ SAFE READ
    kill = debug_pick.get("kill", 0)

    week_start = day - timedelta(days=day.weekday())

    file_key = f"{week_start.isoformat()}_to_{day.isoformat()}"

    export_day_debug(
        rows,
        code,
        file_key,
        mode=f"week_debug_k{kill}"
    )


    print(f"🏆 WEEK DEBUG PICK: {day} (kill={kill})")
