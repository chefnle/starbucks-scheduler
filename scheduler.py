import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys
import json
from datetime import datetime, timedelta
import pandas as pd

import base64
from anthropic import Anthropic

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def parse_image_with_claude(api_key, image_path, prompt):
    client = Anthropic(api_key=api_key)
    encoded = encode_image(image_path)
    
    # Dynamically set media type based on the real extension
    media_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    return response.content[0].text

coverage_df = pd.read_excel('coverage.xlsx')
print("Connecting to Google Sheets...")

days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekly_schedule = {day: [] for day in days_of_week}

def parse_time_string(t_str):
    t_str = t_str.strip().lower()
    for fmt in ('%I:%M%p', '%I:%M %p', '%H:%M'):
        try:
            return datetime.strptime(t_str, fmt).strftime('%H:%M')
        except ValueError:
            continue
    return t_str

def load_partners():
    global partners, partner_hours
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    try:
        import streamlit as st
    except ImportError:
        st = None

    if os.path.exists("service_account.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    elif st is not None and "gcp_service_account" in st.secrets:
        gcp_info = st.secrets["gcp_service_account"]
        if isinstance(gcp_info, str):
            gcp_info = json.loads(gcp_info)
        else:
            gcp_info = dict(gcp_info)
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)
    else:
        raise FileNotFoundError("Could not find service_account.json or Streamlit secrets.") 

    client = gspread.authorize(creds) 
    sheet = client.open("partners").sheet1 
    rows = sheet.get_all_records()

    partners = [] 
    for row in rows: 
        partners.append({ 
            "name": row["Name"], 
            "role": row["Role"], 
            "is_keyholder": bool(row["Is Keyholder"]), 
            "min_hours": float(row["Min Hours"]), 
            "max_hours": float(row["Max Hours"]), 
            "Monday": row["Monday"], 
            "Tuesday": row["Tuesday"], 
            "Wednesday": row["Wednesday"], 
            "Thursday": row["Thursday"], 
            "Friday": row["Friday"], 
            "Saturday": row["Saturday"], 
            "Sunday": row["Sunday"],
            "requested_off": str(row.get("Requested Off", ""))
        })

    partner_hours = {p['name']: 0.0 for p in partners}
    return partners

def get_shift_hours(time_str):
    start_str, end_str = time_str.split('-')
    start_str = parse_time_string(start_str)
    end_str = parse_time_string(end_str)
    fmt = "%H:%M"
    start_time = datetime.strptime(start_str, fmt)
    end_time = datetime.strptime(end_str, fmt)
    delta = end_time - start_time
    elapsed_hours = delta.total_seconds() / 3600
    if elapsed_hours < 0:
        elapsed_hours += 24.0
    if elapsed_hours >= 6.0:
        return elapsed_hours - 0.5
    return elapsed_hours

def get_required_breaks(hours):
    if hours < 4.0:
        return []
    elif 4.0 <= hours < 6.0:
        return ["10-minute break"]
    elif 6.0 <= hours < 6.5:
        return ["10-minute break", "30-minute break"]
    elif 6.5 <= hours <= 10.0:
        return ["10-minute break", "30-minute break", "10-minute break"]
    return []

def get_valid_break_window(time_str):
    start_str, end_str = time_str.split('-')
    start_str = parse_time_string(start_str)
    end_str = parse_time_string(end_str)
    fmt = "%H:%M"
    start_time = datetime.strptime(start_str, fmt)
    end_time = datetime.strptime(end_str, fmt)
    earliest_break = start_time + timedelta(hours=1)
    latest_break = end_time - timedelta(hours=1)
    return earliest_break.strftime("%H:%M"), latest_break.strftime("%H:%M")

def get_eligible_break_slots(start_win, end_win):
    fmt = "%H:%M"
    curr = datetime.strptime(start_win, fmt)
    end = datetime.strptime(end_win, fmt)
    slots = []
    while curr <= end:
        slots.append(curr.strftime("%H:%M"))
        curr += timedelta(minutes=15)
    return slots

def get_shift_midpoint(time_str):
    start_str, end_str = time_str.split('-')
    start_str = parse_time_string(start_str)
    end_str = parse_time_string(end_str)
    fmt = "%H:%M"
    start_time = datetime.strptime(start_str, fmt)
    end_time = datetime.strptime(end_str, fmt)
    mid = start_time + (end_time - start_time) / 2
    return mid.strftime("%H:%M")

def get_best_break_slot(midpoint_str, eligible_slots):
    fmt = "%H:%M"
    mid_time = datetime.strptime(midpoint_str, fmt)
    best_slot = None
    min_diff = float('inf')
    for slot in eligible_slots:
        slot_time = datetime.strptime(slot, fmt)
        diff = abs((slot_time - mid_time).total_seconds())
        if diff < min_diff:
            min_diff = diff
            best_slot = slot
    return best_slot

def allocate_all_breaks(time_str):
    hours = get_shift_hours(time_str)
    breaks = get_required_breaks(hours)
    if not breaks:
        return []
    start_str, end_str = time_str.split('-')
    fmt = "%H:%M"
    start_time = datetime.strptime(start_str, fmt)
    end_time = datetime.strptime(end_str, fmt)
    mid_time = start_time + (end_time - start_time) / 2
    start_win, end_win = get_valid_break_window(time_str)
    eligible = get_eligible_break_slots(start_win, end_win)
    if len(breaks) == 1:
        b10 = get_best_break_slot(mid_time.strftime("%H:%M"), eligible)
        return [{"type": "10-minute break", "time": b10}]
    elif len(breaks) == 2:
        first_half_mid = start_time + (mid_time - start_time) / 2
        b30 = get_best_break_slot(mid_time.strftime("%H:%M"), eligible)
        b10 = get_best_break_slot(first_half_mid.strftime("%H:%M"), [s for s in eligible if s < b30])
        return [{"type": "10-minute break", "time": b10}, {"type": "30-minute break", "time": b30}]
    elif len(breaks) == 3:
        first_half_mid = start_time + (mid_time - start_time) / 2
        second_half_mid = mid_time + (end_time - mid_time) / 2
        b30 = get_best_break_slot(mid_time.strftime("%H:%M"), eligible)
        b10_1 = get_best_break_slot(first_half_mid.strftime("%H:%M"), [s for s in eligible if s < b30])
        b10_2 = get_best_break_slot(second_half_mid.strftime("%H:%M"), [s for s in eligible if s > b30])
        return [
            {"type": "10-minute break (1)", "time": b10_1},
            {"type": "30-minute break", "time": b30},
            {"type": "10-minute break (2)", "time": b10_2}
        ]
    return []

def get_break_slots_for_shift(time_str):
    breaks = allocate_all_breaks(time_str)
    break_slots = []
    for b in breaks:
        b_time = b['time']
        break_slots.append(b_time)
        if "30-minute" in b['type']:
            fmt = "%H:%M"
            dt = datetime.strptime(b_time, fmt)
            next_dt = dt + timedelta(minutes=15)
            break_slots.append(next_dt.strftime("%H:%M"))
    return break_slots

def get_scheduled_count(time_str, day):
    count = 0
    day_shifts = weekly_schedule.get(day, [])
    for shift in day_shifts:
        if shift['assigned_to']:
            start, end = shift['time'].split('-')
            if start <= time_str < end:
                break_slots = get_break_slots_for_shift(shift['time'])
                if time_str not in break_slots:
                    count += 1
    return count

def get_coverage_gaps(day):
    gaps = []
    for index, row in coverage_df.iterrows():
        time_slot = row['Time']
        target = row['Target']
        scheduled = get_scheduled_count(time_slot, day)
        gap = target - scheduled
        if gap > 0:
            gaps.append({"time": time_slot, "gap": gap})
    return gaps

def get_hours_deficit(name, scheduled_hours):
    preferred = next(p['max_hours'] for p in partners if p['name'] == name)
    return preferred - scheduled_hours

def find_partner_for_time(time_str, day, pool, dynamic_off=None):
    if dynamic_off is None:
        dynamic_off = {}
    sorted_pool = sorted(pool, key=lambda p: get_hours_deficit(p['name'], partner_hours[p['name']]), reverse=True)
    for p in sorted_pool:
        if p['name'] in dynamic_off and day in dynamic_off[p['name']]:
            continue
        if day in p.get('requested_off', ''):
            continue
        day_availability = p.get(day, "")
        if day_availability == "full":
            return p
        elif day_availability != "":
            start_avail, end_avail = day_availability.split('-')
            start_avail = parse_time_string(start_avail)
            end_avail = parse_time_string(end_avail)
            if start_avail <= time_str < end_avail:
                return p
    return None

def get_shift_end_time(start_str, hours):
    fmt = "%H:%M"
    start_time = datetime.strptime(start_str, fmt)
    end_time = start_time + timedelta(hours=hours)
    return end_time.strftime("%H:%M")

def create_staggered_shift(partner_name, start_str):
    deficit = get_hours_deficit(partner_name, partner_hours[partner_name])
    shift_length = min(8.0, max(4.0, deficit))
    end_str = get_shift_end_time(start_str, shift_length)
    if end_str > "21:30":
        end_str = "21:30"
    return {
        "name": f"Staggered Shift - {partner_name}",
        "time": f"{start_str}-{end_str}",
        "requires_keyholder": next(p['is_keyholder'] for p in partners if p['name'] == partner_name),
        "assigned_to": partner_name
    }

def auto_generate_schedule(dynamic_off=None):
    load_partners()
    global weekly_schedule, partner_hours
    weekly_schedule = {day: [] for day in days_of_week}
    partner_hours = {p['name']: 0.0 for p in partners}
    for day in days_of_week:
        active_pool = list(partners)
        if day == "Monday":
            admin_shift = {
                "name": "Admin Shift - Nate Le",
                "time": "07:00-15:30",
                "requires_keyholder": True,
                "assigned_to": "Nate Le"
            }
            weekly_schedule["Monday"].append(admin_shift)
            partner_hours["Nate Le"] += get_shift_hours("07:00-15:30")
            nate_partner = next((p for p in active_pool if p['name'] == "Nate Le"), None)
            if nate_partner:
                active_pool.remove(nate_partner)
        elif day == "Wednesday":
            clean_play_partners = []
            keyholder_found = False
            sorted_pool = sorted(active_pool, key=lambda p: get_hours_deficit(p['name'], partner_hours[p['name']]), reverse=True)
            for p in sorted_pool:
                if len(clean_play_partners) < 3:
                    if not keyholder_found and p['is_keyholder']:
                        clean_play_partners.append(p)
                        keyholder_found = True
                    elif len(clean_play_partners) < 3:
                        clean_play_partners.append(p)
            for cp_p in clean_play_partners:
                cp_shift = {
                    "name": f"Clean Play - {cp_p['name']}",
                    "time": "21:30-23:59",
                    "requires_keyholder": cp_p['is_keyholder'],
                    "assigned_to": cp_p['name']
                }
                weekly_schedule["Wednesday"].append(cp_shift)
                partner_hours[cp_p['name']] += get_shift_hours("21:30-23:59")
                active_pool.remove(cp_p)
        skipped_gaps = set()
        while True:
            gaps = get_coverage_gaps(day)
            gaps = [g for g in gaps if g['time'] not in skipped_gaps]
            if not gaps:
                break
            first_gap_time = gaps[0]['time']
            candidate = find_partner_for_time(first_gap_time, day, active_pool, dynamic_off)
            if candidate:
                new_shift = create_staggered_shift(candidate['name'], first_gap_time)
                weekly_schedule[day].append(new_shift)
                partner_hours[candidate['name']] += get_shift_hours(new_shift['time'])
                active_pool.remove(candidate)
            else:
                skipped_gaps.add(first_gap_time)

if __name__ == "__main__":
    auto_generate_schedule()
    print("\nAuto-Generated Weekly Schedule:")
    for day in days_of_week:
        print(f"\n--- {day} ---")
        for s in weekly_schedule[day]:
            print(f"{s['assigned_to']}: {s['time']}")

    print('\nWeekly Partner Hours Summary:') 
    for name, hours in partner_hours.items(): 
        p_dict = next(p for p in partners if p['name'] == name) 
        print(f'{name}: Scheduled {hours:.1f} hours (Range: {p_dict["min_hours"]}-{p_dict["max_hours"]} hours)')

    print("\nChecking coverage score against Excel targets (Sunday):")
    matches = 0
    for index, row in coverage_df.iterrows():
        time_slot = row['Time']
        target = row['Target']
        scheduled = get_scheduled_count(time_slot, "Sunday")
        if scheduled >= target:
            matches += 1
    score = (matches / len(coverage_df)) * 100
    print(f"Sunday Coverage Score: {score:.1f}%")

def get_breaks_text(time_str):
    breaks = allocate_all_breaks(time_str)
    if not breaks:
        return ""
    times = [str(b["time"]) for b in breaks if b.get("time") is not None]
    if not times:
        return ""
    return " [Breaks: " + ", ".join(times) + "]"

def export_schedule_to_excel(): 
    schedule_rows = [] 
    
    for p in partners: 
        row = {"Name": p["name"]} 
        for day in days_of_week: 
            shift_time = "Off" 
            for shift in weekly_schedule[day]: 
                if shift["assigned_to"] == p["name"]: 
                    if "Admin" in shift["name"] or "Clean Play" in shift["name"]: 
                        shift_time = shift["time"] 
                    else: 
                        shift_time = shift["time"] + get_breaks_text(shift["time"]) 
                    break 
            row[day] = shift_time 
        schedule_rows.append(row) 
        
    df = pd.DataFrame(schedule_rows) 
    df.to_excel("weekly_schedule_output.xlsx", index=False) 
    print("\nSaved weekly_schedule_output.xlsx successfully with optimized break plans!")