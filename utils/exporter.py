import os
import pandas as pd
from datetime import timedelta , datetime

# ==================================================
# CONFIG
# ==================================================

ENABLE_DAILY_DEBUG = True

EXPORT_ROOT = "export"
DEBUG_ROOT = "Debug"

# Track which day files have been first-exported in this session
# Format: (country, code, date_key) → marks the first export for that day
_DAILY_EXPORTS_SEEN = set()

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

def reset_daily_export_tracker():
    """
    Clear the tracking set for a new scraping session.
    Call this at the start of each airport scrape.
    """
    global _DAILY_EXPORTS_SEEN
    _DAILY_EXPORTS_SEEN.clear()

def _is_first_export_for_day(country, code, date_key):
    """
    Check if this is the first export for a specific day.
    If yes, mark it as seen and return True (use write mode).
    If no, return False (use append mode).
    """
    global _DAILY_EXPORTS_SEEN
    key = (country, code, date_key)
    if key not in _DAILY_EXPORTS_SEEN:
        _DAILY_EXPORTS_SEEN.add(key)
        return True  # first export → override file
    return False  # subsequent export → append

def _ensure_folder(path):
    os.makedirs(path, exist_ok=True)

def _build_dataframe(rows):
    df = pd.DataFrame(rows)

    existing = [c for c in COLUMN_ORDER if c in df.columns]
    return df.reindex(columns=existing)

def _append_csv(rows, full_path, mode="a"):
    """
    core append/write logic
    mode="a" for append, mode="w" for write (override)
    """

    if not rows:
        return

    df = _build_dataframe(rows)

    file_exists = os.path.exists(full_path)
    header_needed = (mode == "w") or (not file_exists)

    df.to_csv(
        full_path,
        mode=mode,
        header=header_needed,
        index=False
    )

    action = "Wrote" if mode == "w" else "Appended"
    print(f"📦 {action} {len(df)} rows -> {full_path}")

# ==================================================
# MAIN EXPORT
# ==================================================

def append_day_rows(rows, country, code, date_key, expected_count=None, expected_arrival=None, expected_departure=None):

    if not rows:
        return None, False

    # 🔥 sanitize date
    safe_date = datetime.strptime(date_key, "%Y-%m-%d").strftime("%Y-%m-%d")

    # base path เดิม
    base_folder = _build_base_path("day", country, code)

    # 🔥 เพิ่ม subfolder
    folder = os.path.join(base_folder, "flightsfrom_output")
    _ensure_folder(folder)

    # 🔥 เปลี่ยนชื่อไฟล์
    file_name = f"flightsfrom_{code}_{safe_date}.csv"

    full_path = os.path.join(folder, file_name)

    # write metadata (atomic) into a dedicated meta subfolder
    try:
        meta = {}
        # If both arrival+departure provided, derive total from them (prefer explicit parts)
        if expected_arrival is not None and expected_departure is not None:
            meta["expected_arrival"] = int(expected_arrival)
            meta["expected_departure"] = int(expected_departure)
            meta["expected_rows"] = int(expected_arrival) + int(expected_departure)
        else:
            if expected_count is not None:
                meta["expected_rows"] = int(expected_count)
            if expected_arrival is not None:
                meta["expected_arrival"] = int(expected_arrival)
            if expected_departure is not None:
                meta["expected_departure"] = int(expected_departure)
        meta["generated_at"] = datetime.utcnow().isoformat()
        meta_folder = os.path.join(folder, "meta")
        _ensure_folder(meta_folder)
        meta_path = os.path.join(meta_folder, f"flightsfrom_{code}_{safe_date}.json")
        tmp_meta = meta_path + ".tmp"
        with open(tmp_meta, "w", encoding="utf-8") as f:
            import json
            json.dump(meta, f)
        os.replace(tmp_meta, meta_path)
    except Exception:
        # fail silently on metadata write
        pass

    # ⭐ check if first export for this day
    first = _is_first_export_for_day(country, code, date_key)
    if first:
        # first export → override mode
        _append_csv(rows, full_path, mode="w")
    else:
        # subsequent export → append mode
        _append_csv(rows, full_path, mode="a")

    return full_path, first

def append_week_rows(rows, country, code, week_key):

    if not rows:
        return

    folder = _build_base_path("week", country, code)

    file_name = f"flightsfrom_output_{week_key}.csv"
    full_path = os.path.join(folder, file_name)

    _append_csv(rows, full_path)

def append_month_rows(rows, country, code, month_key):

    if not rows:
        return

    folder = _build_base_path("month", country, code)

    file_name = f"flightsfrom_output_{month_key}.csv"
    full_path = os.path.join(folder, file_name)

    _append_csv(rows, full_path)

def append_year_rows(rows, country, code, year_key):

    if not rows:
        return

    folder = _build_base_path("year", country, code)

    file_name = f"flightsfrom_output_{year_key}.csv"
    full_path = os.path.join(folder, file_name)

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

def _build_base_path(mode, country, code):
    """
    Build path:
    export/{mode}/{country}/{code}
    """

    folder = os.path.join(EXPORT_ROOT, mode, country, code)
    _ensure_folder(folder)

    return folder
