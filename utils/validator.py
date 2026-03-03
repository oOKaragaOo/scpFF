import os
import csv
import json
from datetime import datetime
from tqdm import tqdm

def _parse_code_date_from_path(full_path):
    # expects filename like flightsfrom_{CODE}_{YYYY-MM-DD}.csv
    base = os.path.basename(full_path)
    parts = base.split(".")[0].split("_")
    if len(parts) >= 3:
        code = parts[1]
        date = parts[2]
        return code, date
    return None, None


def runcheck_and_report(full_path, expected_count=None, sample_k=3, stop_on_first_dup=False):
    """
    Read CSV in streaming manner, count rows and detect duplicate UIDs.
    If an issue is found (mismatch or duplicates), write a JSON report
    under Debug/<CODE>/report_<date>_<ts>.json
    """
    if not os.path.exists(full_path):
        print(f"⚠️ validator: file not found {full_path}")
        return {"error": "file_not_found", "file": full_path}

    print(f"🔍 post-export validator starting: {full_path}")

    dup_count = 0
    row_count = 0
    seen = set()
    dup_examples = []
    samples = []

    try:
        with open(full_path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            # wrap with tqdm to show progress
            for row in tqdm(reader, desc="Validating", unit="row", leave=False):
                row_count += 1
                uid = (row.get('uid') or '').strip()
                if uid:
                    if uid in seen:
                        dup_count += 1
                        if len(dup_examples) < 5:
                            dup_examples.append(uid)
                        if stop_on_first_dup:
                            break
                    else:
                        seen.add(uid)

                if len(samples) < sample_k:
                    samples.append(row)
    except Exception as e:
        return {"error": "read_failed", "exception": str(e)}

    code, date = _parse_code_date_from_path(full_path)
    report = {
        "file": full_path,
        "code": code,
        "date": date,
        "expected_rows": expected_count,
        "actual_rows": row_count,
        "duplicate_count": dup_count,
        "duplicate_examples": dup_examples,
        "samples": samples,
        "checked_at": datetime.utcnow().isoformat()
    }

    issue = False
    if expected_count is not None and int(expected_count) != int(row_count):
        issue = True
    if dup_count > 0:
        issue = True

    if issue:
        # write report
        dbg_folder = os.path.join('Debug', code or 'UNKNOWN')
        os.makedirs(dbg_folder, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        report_path = os.path.join(dbg_folder, f"report_{date or 'unknown'}_{ts}.json")
        try:
            with open(report_path, 'w', encoding='utf-8') as rf:
                json.dump(report, rf, ensure_ascii=False, indent=2)
        except Exception:
            pass
        print(f"⚠️ validator: issues detected; report written to {report_path}")
    else:
        print("✅ validator: no issues found")

    return report
