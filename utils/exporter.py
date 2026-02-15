import pandas as pd
import os

# def export_day_debug(day_rows, code, date_str, mode="arrivals"):

#     if not day_rows:
#         return

#     # 🔥 เปลี่ยน path มา debug
#     folder_path = os.path.join("debug", code)
#     os.makedirs(folder_path, exist_ok=True)

#     file_name = f"{date_str}_{mode}.csv"
#     full_path = os.path.join(folder_path, file_name)

#     df = pd.DataFrame(day_rows)
#     df.to_csv(full_path, index=False)

#     print(f"   💾 Exported {len(df)} rows to {full_path}")

def export_day_debug(day_rows, code, date_str, mode="arrivals"):

        if not day_rows:
            return

        # 🔥 debug path
        folder_path = os.path.join("debug", code)
        os.makedirs(folder_path, exist_ok=True)

        file_name = f"{date_str}_{mode}.csv"
        full_path = os.path.join(folder_path, file_name)

        # -------------------------
        # COLUMN ORDER
        # -------------------------
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

        df = pd.DataFrame(day_rows)

        # เอาเฉพาะ column ที่มีจริง
        existing_cols = [c for c in COLUMN_ORDER if c in df.columns]
        df = df.reindex(columns=existing_cols)

        df.to_csv(full_path, index=False)

        print(f"   💾 Exported {len(df)} rows to {full_path}")

