# 📘 Flight Scraper — Quick Guide

## 🧩 Requirements (optional)

* Python 3.12.10
* pip (latest)

---

## ⚙️ Create & Activate venv

### Windows (CMD)

```bash
python -m venv venv
venv\Scripts\activate
```

### Windows (PowerShell)

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## ⬆️ Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## 📦 Install libraries

```bash
pip install -r requirements.txt
playwright install
```

---

## ✈️ Hook Airline List (สร้าง airport list)

ใช้ไฟล์ `getPort.py`

ไปที่:

```python
countries = [
    "Thailand"
]
```

ใส่ keyword ประเทศ/เมืองได้หลายตัว แล้วรัน:

```bash
python getPort.py
```

ผลลัพธ์:

```
world_airports_city.csv
```

---

## 🛬 Hook Flight Detail

ตั้งค่า date range ใน `main.py`

```python
START_DATE = date(2026, 2, 27)
END_DATE   = date(2026, 3, 2)
```

รัน:

```bash
python main.py
```

---

## ⚙️ Settings (วิธีใช้งาน)

ไฟล์ตั้งค่าอยู่ที่:

```
settings.py
```

ตัวอย่าง:

```python
SCRAPER_SETTINGS = {

    # -------------------------
    # PARSER
    # -------------------------
    "arrival_parser_enabled": True,
    "departure_parser_enabled": True,

    # -------------------------
    # RECOVERY                     จะทำงานเมื่อเกิด footer only หรือ กด detail แล้วเว็ปข้อมูลหาย 
    # -------------------------    RECOVERY จะเอา flight ที่ ถูกข้ามเพราะ footer only เอามาไล่ดูในส่วนที่ข้ามเพื่อพยายามเก็บรายละเอียด
    "recovery_enabled": True,      ปิดใช้งานได้โดยการเปลี่ยนเป็น False หากทำให้ใช้เวลานานกว่าปกติ 
    
    # -------------------------
    # TAB CONTROL
    # -------------------------
    "auto_restore_tab": True,

    # -------------------------
    # EXPORT
    # -------------------------
    "export_enabled": True,
    "debug_export_enabled": True,

    # day | week | month | year
    "export_mode": "month",

    # -------------------------
    # DEBUG
    # -------------------------
    "debug_week_export": True,
}
```

### 🔹 Parser Settings

| Setting                    | ความหมาย                                        |
| -------------------------- | ----------------------------------------------- |
| `arrival_parser_enabled`   | เปิด/ปิด scrape ฝั่ง Arrivals                   |
| `departure_parser_enabled` | เปิด/ปิด scrape ฝั่ง Departures                 |
| `popup_scrape_enabled`     | เมื่อ False จะไม่กดดู popup และจะเว้นค่ารายละเอียด (time_range, distance, ฯลฯ) |

---

### 🔹 Recovery

| Setting            | ความหมาย                                                 |
| ------------------ | -------------------------------------------------------- |
| `recovery_enabled` | เปิด/ปิด missing-flight recovery (ทำงานหลัง parse เสร็จ) |

> ⚠️ Footer recovery ยังคงทำงานเสมอเพื่อรักษา state ของหน้าเว็บ

---

### 🔹 Tab Control

| Setting            | ความหมาย                                      |
| ------------------ | --------------------------------------------- |
| `auto_restore_tab` | หลังจบ departure จะสลับกลับ arrival อัตโนมัติ |

---

### 🔹 Export

| Setting                | ความหมาย                                           |
| ---------------------- | -------------------------------------------------- |
| `export_enabled`       | เปิด/ปิด export CSV หลัก                           |
| `debug_export_enabled` | เปิด/ปิด debug export                              |
| `export_mode`          | เลือกระดับ export (`day`, `week`, `month`, `year`) |

---

### 🔹 Debug Export

| Setting             | ความหมาย                     |
| ------------------- | ---------------------------- |
| `debug_week_export` | export debug pick รายสัปดาห์ |

Debug export จะถูกแยกเป็น:

```
arrival
departure
```

---

### 🧪 Recommended Modes

**Fast test mode**

```python
"recovery_enabled": False
"debug_export_enabled": False
```

**Long run (stable mode)**

```python
"recovery_enabled": True
"auto_restore_tab": True
```

---

## 📤 Export (วิธีใช้งาน)

ระบบจะ export อัตโนมัติระหว่าง scrape โดยใช้ `exporter.py`

### 📂 โครงสร้างไฟล์ output

```
export/
 └── <AIRPORT_CODE>/
      └── YYYY-MM.csv
```

ตัวอย่าง:

```
export/BKK/2026-03.csv
```

### ⚙️ วิธีการ export (สรุป)

1. scraper ดึงข้อมูลรายวัน
2. parse flight + popup detail
3. รวม rows รายเดือน
4. append ลง CSV อัตโนมัติ

ฟังก์ชันหลักที่ใช้:

```python
append_month_rows(rows, code, month_key)
```

* append ข้อมูลเพิ่ม (ไม่ overwrite)
* สร้าง folder/file ให้อัตโนมัติ

### 🧾 Column หลักในไฟล์

* date / day_name
* airport / direction
* flight / airline
* time / duration
* aircraft / distance / seats
* uid (unique id)
* scraped_at

### 🧪 Debug export (optional)

ใน `exporter.py`

```python
ENABLE_DAILY_DEBUG = True
```

* True  → export debug รายวัน/รายสัปดาห์
* False → export เฉพาะไฟล์หลัก

---

## 🧭 วิธีอ่าน Log (สั้น ๆ)

### 🔹 Progress bar (tqdm)

ตัวอย่าง:

```
Row runing :  35%|███▌ ... | Footer Kill : 2
```

ความหมาย:

* Row running → จำนวน flight ที่ parse ไปแล้ว
* Footer Kill → จำนวนครั้งที่ข้อมูล Airline บนหน้าเว็ปหายแล้ว Airline กลับมา
* Recovery → จำนวน flight ที่กู้คืนได้

### 🔹 Log สำคัญที่ควรดู

* `Snapshot unique flights` → จำนวน flight ที่ detect จากหน้าเว็บ
* `Start parse (arrival/departure)` → เริ่ม parse จริง
* `Appended ... rows` → export สำเร็จ
* `WEEK DEBUG PICK` → debug file ที่ถูกเลือก export

ถ้าเลข flight น้อยผิดปกติ → เช็ค calendar หรือ popup render ก่อน

---

## 🐞 ข้อแนะนำเมื่อเจอบัคของ tqdm

อาการที่เจอบ่อย:

* progress bar ค้าง
* log ขึ้นทับกัน
* bar ไม่ปิดเมื่อ error

วิธีแก้เร็ว:

1️⃣ ปิด tqdm ชั่วคราวเพื่อ debug

```python
pbar = tqdm(..., disable=True)
```

2️⃣ อย่าใช้ `print()` รัว ๆ ขณะ tqdm ทำงาน
ใช้:

```python
pbar.set_postfix_str("message")
```

แทน

3️⃣ ถ้า bar เพี้ยนหลัง exception
ให้แน่ใจว่ามี:

```python
pbar.close()
```

(หรือให้ loop จบปกติ)

4️⃣ ถ้า run บนบาง terminal แล้วกระตุก
ลองลด:

```python
ncols=40
```

หรือลองเอา `colour` ออก

💡 Tip: tqdm เป็นแค่ UI ไม่เกี่ยวกับ logic scrape — ถ้ามีบัค parsing ให้ปิด tqdm ก่อนเพื่อ isolate ปัญหา

---

## 🚀 Quick Start (สั้นสุด)

```bash

python -m venv venv
# activate venv
pip install -r requirements.txt
playwright install
python getPort.py
python main.py

```
