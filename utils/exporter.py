import pandas as pd
import os

def export_day_debug(day_rows, code, date_str, mode="arrivals"):

    if not day_rows:
        return

    # 🔥 เปลี่ยน path มา debug
    folder_path = os.path.join("debug", code)
    os.makedirs(folder_path, exist_ok=True)

    file_name = f"{date_str}_{mode}.csv"
    full_path = os.path.join(folder_path, file_name)

    df = pd.DataFrame(day_rows)
    df.to_csv(full_path, index=False)

    print(f"   💾 Exported {len(df)} rows to {full_path}")
