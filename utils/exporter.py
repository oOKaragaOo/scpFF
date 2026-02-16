import os
import pandas as pd

ENABLE_DAILY_DEBUG = True
# =========================
# CONFIG
# =========================

COLUMN_ORDER = [
    # CORE
    "date",
    "day_name",
    "airport",
    "direction",
    "time",
    "destination",
    "flight",
    "airline",
    "duration",

    # DETAIL
    "time_range",
    "distance",
    "aircraft",
    "seats",
    "codeshare",
    "entertainment",
    "meals",

    # META
    "uid",
    "airline_source",
    "page_date_verified",
    "scraped_at"
]


# =========================
# INTERNAL HELPERS
# =========================

def set_daily_debug(enabled: bool):
    """
    Toggle daily debug export globally.
    """
    global ENABLE_DAILY_DEBUG
    ENABLE_DAILY_DEBUG = enabled


def _build_dataframe(rows):
    """
    Build dataframe with stable column order.
    Extra columns will be ignored.
    """
    df = pd.DataFrame(rows)

    existing_cols = [c for c in COLUMN_ORDER if c in df.columns]
    df = df.reindex(columns=existing_cols)

    return df


def _ensure_folder(path):
    os.makedirs(path, exist_ok=True)


# =========================
# DEBUG EXPORT (DAY / WEEK)
# =========================

def export_day_debug(day_rows, code, date_str, mode="arrivals"):

    # -------------------------
    # DEBUG SWITCH
    # -------------------------
    if not ENABLE_DAILY_DEBUG:
        return

    if not day_rows:
        return


# =========================
# MAIN MONTH EXPORT (APPEND)
# =========================

def append_month_rows(rows, code, month_key):
    """
    Append rows into monthly CSV.

    Parameters
    ----------
    month_key : str
        Example: "2026-10"
    """

    if not rows:
        return

    folder = os.path.join("export", code)
    _ensure_folder(folder)

    file_name = f"{month_key}.csv"
    full_path = os.path.join(folder, file_name)

    df = _build_dataframe(rows)

    file_exists = os.path.exists(full_path)

    df.to_csv(
        full_path,
        mode="a",
        header=not file_exists,
        index=False
    )

    print(f"   📦 Appended {len(df)} rows -> {full_path}")


# =========================
# WEEKLY DEBUG PICK EXPORT
# =========================

def export_week_debug_pick(debug_pick, code):
    """
    Export 1 debug file per week.

    debug_pick format:
    {
        "day": date,
        "rows": [...],
        "kill": int
    }
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

    print(
        f"   🏆 WEEK DEBUG PICK: "
        f"{day} (kill={kill})"
    )
