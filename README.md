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

```

---

## ✈️ Hook Airline List (สร้าง airport list)

ใช้ไฟล์ `getPort.py`

ไปที่:

```python
countries = [
    "Dallas"
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

## 📤 Export (สรุปสั้น)

Flow:

1. ดึง flight list
2. เปิด popup เก็บ detail
3. parse → rows
4. export เป็น CSV แยกตามเดือน

ข้อมูลหลักที่ export:

* airport
* flight
* airline
* date / time
* duration
* aircraft
* distance
* seats
* uid

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
