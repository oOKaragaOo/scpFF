import argparse
import json
import os
import re
import shutil
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime, timezone

import pandas as pd
from playwright.sync_api import sync_playwright

from core.airport_scraper import AirportScraper
from core.SoundNotifier import SoundNotifier
from settings import SCRAPER_SETTINGS


DEFAULT_START_DATE = date(2026, 3, 24)
DEFAULT_END_DATE = date(2026, 3, 25)
DEFAULT_WORKERS = 3
DEFAULT_RETRIES = 2
STATE_DIR = os.path.join("export", "_run_state")
PROFILE_ROOT = "profile_workers"


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def _state_file_path(run_id):
    return os.path.join(STATE_DIR, f"{run_id}.json")


def _save_state(path, state):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _load_state(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_latest_state_file():
    if not os.path.isdir(STATE_DIR):
        return None

    files = [
        os.path.join(STATE_DIR, name)
        for name in os.listdir(STATE_DIR)
        if name.endswith(".json")
    ]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _resolve_airport_csv_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "data", "reference", "world_airports_city.csv"),
        os.path.join(base_dir, "..", "data", "reference", "world_airports_city.csv"),
        os.path.join("data", "reference", "world_airports_city.csv"),
        os.path.join("..", "data", "reference", "world_airports_city.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "world_airports_city.csv not found. tried: "
        + ", ".join(candidates)
    )


def _build_codes(codes_arg):
    def normalize_codes(values):
        seen = set()
        result = []
        for raw in values:
            code = str(raw).strip().upper()
            if not code or code in {"NAN", "NONE", "NULL"}:
                continue
            if not re.fullmatch(r"[A-Z]{3}", code):
                continue
            if code not in seen:
                seen.add(code)
                result.append(code)
        return result

    if codes_arg:
        return normalize_codes(codes_arg.split(","))

    airports_df = pd.read_csv(_resolve_airport_csv_path())
    return normalize_codes(airports_df["airport_code"].tolist())


def _build_run_id():
    return datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")


def _cleanup_profiles(profile_root):
    if not os.path.exists(profile_root):
        print(f"[cleanup] profile root not found: {profile_root}")
        return 0

    if not os.path.isdir(profile_root):
        raise ValueError(f"profile root is not a directory: {profile_root}")

    removed = 0
    for name in os.listdir(profile_root):
        target = os.path.join(profile_root, name)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=False)
            removed += 1
        elif os.path.isfile(target):
            os.remove(target)
            removed += 1

    print(f"[cleanup] removed {removed} item(s) from {profile_root}")
    return removed


def _init_state(run_id, args, codes):
    jobs = {}
    for code in codes:
        jobs[code] = {
            "status": "pending",
            "attempts": 0,
            "rows": 0,
            "last_error": None,
            "updated_at": _utc_now_iso()
        }
    return {
        "run_id": run_id,
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "args": {
            "start": args.start.isoformat(),
            "end": args.end.isoformat(),
            "workers": args.workers,
            "retries": args.retries,
            "headless": args.headless
        },
        "jobs": jobs
    }


def _worker_scrape_job(run_id, code, start_iso, end_iso, headless, attempt, disable_tqdm):
    start_d = _parse_date(start_iso)
    end_d = _parse_date(end_iso)
    pid = os.getpid()
    worker_id = f"W{pid}"
    prefix = f"[{run_id}][{worker_id}][{code}]"
    profile_dir = os.path.join("profile_workers", f"{code}_{pid}_a{attempt}")
    os.makedirs(profile_dir, exist_ok=True)
    os.environ["SCRAPER_DISABLE_TQDM"] = "1" if disable_tqdm else "0"

    print(f"{prefix} start attempt={attempt} range={start_iso}->{end_iso}")
    t0 = time.time()

    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                profile_dir,
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )

            page = ctx.new_page()
            scraper = AirportScraper(page)

            try:
                rows = scraper.scrape_airport(code, start_d, end_d)
            finally:
                ctx.close()

        elapsed = round(time.time() - t0, 2)
        row_count = len(rows)
        print(f"{prefix} success rows={row_count} elapsed={elapsed}s")
        return {
            "success": True,
            "code": code,
            "rows": row_count,
            "attempt": attempt,
            "elapsed_sec": elapsed,
            "error": None,
            "traceback": None
        }

    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        tb = traceback.format_exc(limit=20)
        print(f"{prefix} failed attempt={attempt} elapsed={elapsed}s err={e}")
        return {
            "success": False,
            "code": code,
            "rows": 0,
            "attempt": attempt,
            "elapsed_sec": elapsed,
            "error": str(e),
            "traceback": tb
        }


def _submit_job(pool, future_map, run_id, args, code, attempt):
    fut = pool.submit(
        _worker_scrape_job,
        run_id,
        code,
        args.start.isoformat(),
        args.end.isoformat(),
        args.headless,
        attempt,
        args.workers > 1
    )
    future_map[fut] = {"code": code, "attempt": attempt}


def _should_run_job(job_state):
    return job_state.get("status") != "success"


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Parallel flightsfrom scraper (airport-level workers)"
    )
    parser.add_argument("--codes", type=str, default=None, help="CSV airport codes, ex: MYY,KUL,BKK")
    parser.add_argument("--start", type=_parse_date, default=DEFAULT_START_DATE, help="YYYY-MM-DD")
    parser.add_argument("--end", type=_parse_date, default=DEFAULT_END_DATE, help="YYYY-MM-DD")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--headless", action="store_true", help="Run Playwright in headless mode")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run state")
    parser.add_argument("--run-id", type=str, default=None, help="Run id to resume")
    parser.add_argument("--cleanup-profiles", action="store_true", help="Delete all items in profile_workers then exit")
    return parser


def _maybe_generate_chart(run_id, airport_codes):
    if not SCRAPER_SETTINGS.get("chart_export_enabled", False):
        return

    pattern = SCRAPER_SETTINGS.get(
        "chart_export_pattern",
        "export/day/**/flightsfrom_output/flightsfrom_*.csv",
    )
    threshold = int(SCRAPER_SETTINGS.get("chart_export_threshold", 100))
    charts_per_page = int(SCRAPER_SETTINGS.get("chart_export_charts_per_page", 12))

    try:
        from run_pandas_chart_plot import generate_charts
        scoped_codes = sorted({c.strip().upper() for c in airport_codes if str(c).strip()})
        if not scoped_codes:
            print(f"[chart] skip: no success airports in run {run_id}")
            return
        print(
            f"[chart] generating charts run_id={run_id} "
            f"airports={len(scoped_codes)} threshold={threshold} "
            f"per_page={charts_per_page}"
        )
        ok = generate_charts(
            pattern=pattern,
            threshold=threshold,
            airport_codes=scoped_codes,
            run_id=run_id,
            charts_per_page=charts_per_page,
        )
        if not ok:
            print("[chart] no chart generated")
    except Exception as e:
        print(f"[chart] generate failed: {e}")


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.end < args.start:
        raise ValueError("end date must be >= start date")
    if args.workers < 1:
        raise ValueError("workers must be >= 1")
    if args.retries < 0:
        raise ValueError("retries must be >= 0")

    if args.cleanup_profiles:
        allow_cleanup = bool(SCRAPER_SETTINGS.get("allow_profile_cleanup", False))
        if not allow_cleanup:
            print(
                "[cleanup] blocked by settings: "
                "set SCRAPER_SETTINGS['allow_profile_cleanup'] = True first"
            )
            return 2
        _cleanup_profiles(PROFILE_ROOT)
        return 0

    all_codes = _build_codes(args.codes)
    if not all_codes:
        raise ValueError("no airport codes found")

    _ensure_state_dir()

    if args.resume:
        if args.run_id:
            state_path = _state_file_path(args.run_id)
            if not os.path.exists(state_path):
                raise FileNotFoundError(f"state file not found for run-id: {args.run_id}")
        else:
            state_path = _find_latest_state_file()
            if state_path is None:
                raise FileNotFoundError("no state file found to resume")

        state = _load_state(state_path)
        run_id = state["run_id"]
        print(f"[{run_id}] resume from state: {state_path}")

        # keep only requested codes if --codes specified
        selected_codes = all_codes
        for code in selected_codes:
            if code not in state["jobs"]:
                state["jobs"][code] = {
                    "status": "pending",
                    "attempts": 0,
                    "rows": 0,
                    "last_error": None,
                    "updated_at": _utc_now_iso()
                }
    else:
        run_id = args.run_id or _build_run_id()
        state_path = _state_file_path(run_id)
        state = _init_state(run_id, args, all_codes)
        _save_state(state_path, state)
        print(f"[{run_id}] new run state: {state_path}")

    codes_to_run = [code for code in all_codes if _should_run_job(state["jobs"].get(code, {}))]
    if not codes_to_run:
        print(f"[{run_id}] no pending jobs (all success)")
        return 0

    total_jobs = len(codes_to_run)
    max_attempts = args.retries + 1
    backoff = [5, 15]
    start_ts = time.time()

    print(
        f"[{run_id}] jobs={total_jobs} workers={args.workers} "
        f"range={args.start.isoformat()}->{args.end.isoformat()} retries={args.retries}"
    )

    notifier = SoundNotifier()
    success_count = 0
    failed_count = 0
    future_map = {}

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for code in codes_to_run:
            job = state["jobs"][code]
            attempt = int(job.get("attempts", 0)) + 1
            job["status"] = "running"
            job["attempts"] = attempt
            job["updated_at"] = _utc_now_iso()
            _submit_job(pool, future_map, run_id, args, code, attempt)

        state["updated_at"] = _utc_now_iso()
        _save_state(state_path, state)

        while future_map:
            done_future = next(as_completed(future_map))
            meta = future_map.pop(done_future)
            code = meta["code"]

            result = done_future.result()
            job = state["jobs"][code]
            job["updated_at"] = _utc_now_iso()

            if result["success"]:
                job["status"] = "success"
                job["rows"] = int(result.get("rows", 0))
                job["last_error"] = None
                success_count += 1
                print(
                    f"[{run_id}][{code}] success "
                    f"attempt={result['attempt']} rows={result['rows']}"
                )
            else:
                attempt = int(result.get("attempt", job.get("attempts", 1)))
                err = result.get("error") or "unknown error"
                tb = result.get("traceback") or ""
                job["last_error"] = {
                    "message": err,
                    "traceback": tb[:4000],
                    "at": _utc_now_iso()
                }

                if attempt < max_attempts:
                    wait_sec = backoff[min(attempt - 1, len(backoff) - 1)]
                    job["status"] = "pending"
                    job["attempts"] = attempt + 1
                    print(
                        f"[{run_id}][{code}] retry scheduled "
                        f"attempt={attempt + 1}/{max_attempts} after={wait_sec}s"
                    )
                    state["updated_at"] = _utc_now_iso()
                    _save_state(state_path, state)
                    time.sleep(wait_sec)

                    job["status"] = "running"
                    job["updated_at"] = _utc_now_iso()
                    _submit_job(pool, future_map, run_id, args, code, attempt + 1)
                else:
                    job["status"] = "failed"
                    failed_count += 1
                    print(
                        f"[{run_id}][{code}] failed "
                        f"attempts={attempt}/{max_attempts} err={err}"
                    )

            state["updated_at"] = _utc_now_iso()
            _save_state(state_path, state)

    elapsed = int(time.time() - start_ts)
    mins = elapsed // 60
    secs = elapsed % 60
    success_airports = [
        code for code, job in state["jobs"].items()
        if code in codes_to_run and job.get("status") == "success"
    ]

    print(
        f"\n[{run_id}] summary success={success_count} failed={failed_count} "
        f"total={total_jobs} runtime={mins}m{secs}s state={state_path}"
    )
    _maybe_generate_chart(run_id, success_airports)

    if failed_count == 0:
        notifier.success()
        return 0

    notifier.error()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
