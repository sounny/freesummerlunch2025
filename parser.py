import csv
from datetime import datetime, timedelta

# Helper functions
def parse_time_24h(timestr):
    # e.g. "8:45" or "11:00"
    t = datetime.strptime(timestr, "%H:%M") if ":" in timestr else datetime.strptime(timestr, "%H")
    return t.strftime("%H:%M")

def ampm_to_24h(timestr):
    # e.g. "8:45-9:15" or "11:00-11:30"
    times = []
    for rng in timestr.split(";"):
        parts = rng.strip().split("-")
        if len(parts) == 2:
            t1 = datetime.strptime(parts[0].strip(), "%I:%M") if ":" in parts[0] else datetime.strptime(parts[0].strip(), "%I")
            t2 = datetime.strptime(parts[1].strip(), "%I:%M") if ":" in parts[1] else datetime.strptime(parts[1].strip(), "%I")
            times.append(f"{t1.strftime('%H:%M')}-{t2.strftime('%H:%M')}")
    return ";".join(times)

def parse_meal_times(meal_times):
    # e.g. "B (8:45-9:15), L (11:00-11:30)"
    result = []
    for part in meal_times.split(","):
        if "(" in part and ")" in part:
            times = part.split("(")[1].split(")")[0]
            # Handle AM/PM if present
            if "AM" in times or "PM" in times:
                times = times.replace("AM", "").replace("PM", "")
            result.append(times.strip())
    return ";".join(result)

def weekday_str_to_int(wd):
    # M=0, TU=1, W=2, TH=3, F=4, SA=5, SU=6
    wd = wd.upper()
    return {"M":0, "TU":1, "T":1, "W":2, "TH":3, "F":4, "SA":5, "SU":6}[wd]

def get_weekdays_from_range(range_str):
    # e.g. "M-TH" -> [0,1,2,3]
    days = []
    if "-" in range_str:
        start, end = range_str.split("-")
        start = start.strip()
        end = end.strip()
        all_days = ["M", "TU", "W", "TH", "F", "SA", "SU"]
        i1 = all_days.index(start)
        i2 = all_days.index(end)
        if i1 <= i2:
            days = list(range(i1, i2+1))
        else:
            days = list(range(i1, 7)) + list(range(0, i2+1))
    else:
        days = [weekday_str_to_int(range_str)]
    return days

def parse_days_of_week(datestr):
    # e.g. "06/09/25-07/02/25 (M-TH)"
    if "(" in datestr and ")" in datestr:
        days = datestr.split("(")[1].split(")")[0]
        if "-" in days:
            return get_weekdays_from_range(days)
        else:
            return [weekday_str_to_int(d) for d in days.split(",")]
    return list(range(7))

def parse_closed_open_exceptions(datestr):
    closed = set()
    open_extra = set()
    for part in datestr.split(","):
        part = part.strip()
        if part.startswith("Closed"):
            # e.g. "Closed Thursday 06/19/25"
            date_str = part.split()[-1]
            try:
                closed.add(datetime.strptime(date_str, "%m/%d/%y").date())
            except:
                pass
        elif part.startswith("Open"):
            date_str = part.split()[-1]
            try:
                open_extra.add(datetime.strptime(date_str, "%m/%d/%y").date())
            except:
                pass
    return closed, open_extra

def parse_date_range(datestr):
    # e.g. "06/09/25-07/02/25 (M-TH) Closed Thursday 06/19/25, Open Friday 06/20/25"
    main = datestr.split("(")[0].split(",")[0].strip()
    start, end = main.split("-")
    start = datetime.strptime(start.strip(), "%m/%d/%y").date()
    end = datetime.strptime(end.strip(), "%m/%d/%y").date()
    return start, end

# Date range for columns
start_date = datetime(2025, 6, 9).date()
end_date = datetime(2025, 7, 25).date()
date_list = []
d = start_date
while d <= end_date:
    date_list.append(d)
    d += timedelta(days=1)

with open("data3.csv", newline='') as infile, open("data4.csv", "a", newline='') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + [d.strftime("%Y-%m-%d") for d in date_list]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    # writer.writeheader()  # Already written

    for row in reader:
        # Parse date range, days of week, closed/open exceptions
        try:
            drange = parse_date_range(row["Dates of Service"])
            weekdays = parse_days_of_week(row["Dates of Service"])
            closed, open_extra = parse_closed_open_exceptions(row["Dates of Service"])
        except Exception as e:
            drange = (start_date, end_date)
            weekdays = list(range(7))
            closed, open_extra = set(), set()
        meal_times = parse_meal_times(row["Meal Times"])
        # Build row for each date
        for d in date_list:
            val = ""
            if d >= drange[0] and d <= drange[1]:
                if d in closed:
                    val = ""
                elif d.weekday() in weekdays or d in open_extra:
                    val = ampm_to_24h(meal_times)
            row[d.strftime("%Y-%m-%d")] = val
        writer.writerow(row)

def fix_time(t):
    # If time is 00:xx, but should be 12:xx (noon), fix it
    if t.startswith("00:"):
        return "12:" + t[3:]
    return t

def fix_range(rng):
    # Fix both start and end times in a range
    if '-' not in rng: return rng
    start, end = rng.split('-')
    return f"{fix_time(start.strip())}-{fix_time(end.strip())}"

def fix_cell(cell):
    # Fix all ranges in a cell (separated by ;)
    if not cell: return cell
    return ";".join(fix_range(rng) for rng in cell.split(';'))

with open("data4.csv", newline='') as infile:
    rows = list(csv.reader(infile))
    header = rows[0]
    data = rows[1:]

# Find all date columns (YYYY-MM-DD)
date_cols = [i for i, h in enumerate(header) if h.count('-') == 2]

for row in data:
    for i in date_cols:
        row[i] = fix_cell(row[i])

with open("data4.csv", "w", newline='') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(header)
    writer.writerows(data)

print("Time ranges fixed in data4.csv.")