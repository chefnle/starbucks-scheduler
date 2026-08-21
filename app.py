import streamlit as st
import pandas as pd
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from scheduler import auto_generate_schedule, export_schedule_to_excel

st.set_page_config(page_title="Starbucks Scheduler", page_icon="☕")
st.markdown('<style>h1 { color: #00704a !important; }</style>', unsafe_allow_html=True)
st.title("Starbucks Scheduler ☕")

days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
if os.path.exists("service_account.json"):
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
else:
    gcp_info = st.secrets["gcp_service_account"]
    if isinstance(gcp_info, str):
        gcp_info = json.loads(gcp_info)
    else:
        gcp_info = dict(gcp_info)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)

client = gspread.authorize(creds)
sheet = client.open("partners").sheet1

tab1, tab2 = st.tabs(["Manage Partners", "Schedule Generate"])

with tab1:
    st.header("Manage Team Directory")
    rows = sheet.get_all_records()
    if rows:
        df_p = pd.DataFrame(rows)
        df_p = df_p.fillna("")
    else:
        df_p = pd.DataFrame(columns=["Name", "Role", "Is Keyholder", "Min Hours", "Max Hours"] + days_list)

    names_list = df_p["Name"].tolist()
    selection = st.selectbox("Select Partner to Edit or Choose Add New:", ["-- Add New Partner --"] + names_list)

    default_name = ""
    default_role = "Barista"
    default_keyholder = False
    default_min = 15.0
    default_max = 20.0
    default_days = {day: "" for day in days_list}

    is_edit = selection != "-- Add New Partner --"
    if is_edit:
        p_row = df_p[df_p["Name"] == selection].iloc[0]
        default_name = p_row["Name"]
        default_role = p_row["Role"]
        default_keyholder = bool(p_row["Is Keyholder"])
        default_min = float(p_row["Min Hours"])
        default_max = float(p_row["Max Hours"])
        for day in days_list:
            default_days[day] = str(p_row[day])
        
    p_name = st.text_input("Name:", value=default_name, disabled=is_edit)
    p_role = st.selectbox("Role:", ["Barista", "Shift Supervisor", "Store Manager"], index=["Barista", "Shift Supervisor", "Store Manager"].index(default_role))
    p_keyholder = st.checkbox("Is Keyholder", value=default_keyholder)

    col_min, col_max = st.columns(2)
    with col_min:
        p_min = st.number_input("Min Hours:", min_value=0.0, max_value=40.0, value=default_min, step=0.5)
    with col_max:
        p_max = st.number_input("Max Hours:", min_value=0.0, max_value=40.0, value=default_max, step=0.5)
    
    st.subheader("Daily Availabilities (e.g. 04:30-15:00 or leave blank)")
    avail_inputs = {}
    for day in days_list:
        avail_inputs[day] = st.text_input(f"{day}:", value=default_days[day], key=f"input_{day}")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Save / Update Partner"):
            if p_name.strip():
                new_partner_row = {
                    "Name": p_name.strip(),
                    "Role": p_role,
                    "Is Keyholder": p_keyholder,
                    "Min Hours": p_min,
                    "Max Hours": p_max
                }
                for day in days_list:
                    new_partner_row[day] = avail_inputs[day].strip()
                if is_edit:
                    df_p.loc[df_p["Name"] == selection] = pd.Series(new_partner_row)
                else:
                    df_p = pd.concat([df_p, pd.DataFrame([new_partner_row])], ignore_index=True)
                data = [df_p.columns.values.tolist()] + df_p.values.tolist()
                sheet.clear()
                sheet.update("A1", data)
                st.success(f"Successfully saved {p_name}!")
                st.rerun()
            else:
                st.error("Name is required.")

    with col_btn2:
        if is_edit:
            if st.button("🗑️ Delete Partner", type="secondary"):
                df_p = df_p[df_p["Name"] != selection]
                data = [df_p.columns.values.tolist()] + df_p.values.tolist()
                sheet.clear()
                sheet.update("A1", data)
                st.success(f"Removed {selection} from team roster.")
                st.rerun()

with tab2:
    st.header("Schedule Generate 📊")

    day_themes = {
        "Monday": ("🔴 Monday", "#ef4444"),
        "Tuesday": ("🟠 Tuesday", "#f97316"),
        "Wednesday": ("🟡 Wednesday", "#eab308"),
        "Thursday": ("🟢 Thursday", "#22c55e"),
        "Friday": ("🔵 Friday", "#3b82f6"),
        "Saturday": ("🟣 Saturday", "#a855f7"),
        "Sunday": ("🟤 Sunday", "#8b5cf6")
    }

    budgets = {}

    for day in days_list:
        label, color = day_themes.get(day, (f"⚪ {day}", "#3b82f6"))
        
        with st.expander(label):
            col_left, col_right = st.columns([1, 2])
            
            with col_left:
                budgets[day] = st.number_input(
                    f"{day} Budget (Hours):",
                    min_value=0.0,
                    max_value=200.0,
                    value=40.0,
                    step=0.5,
                    key=f"budget_{day}"
                )
                
                uploaded_img = st.file_uploader(
                    f"Scan {day} Graph:",
                    type=["png", "jpg", "jpeg"],
                    key=f"uploader_{day}"
                )
                
                if uploaded_img:
                    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY")
                    if api_key:
                        with st.spinner(f"Scanning {day} graph..."):
                            temp_path = f"temp_{day}.png"
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_img.getbuffer())
                            
                            from scheduler import parse_image_with_claude
                            prompt = "Look at this coverage graph and transcribe the 15-minute partner targets into a clean JSON dictionary, like {'04:30': 3, '04:45': 3}."
                            try:
                                result_data = parse_image_with_claude(api_key, temp_path, prompt)
                                st.success(f"{day} graph scanned successfully!")
                                st.json(result_data)
                                os.remove(temp_path)
                            except Exception as e:
                                st.error(f"Scan failed: {e}")
                    else:
                        st.error("Missing ANTHROPIC_API_KEY in secrets.")
            
            with col_right:
                if os.path.exists("coverage.xlsx"):
                    from scheduler import get_scheduled_count
                    coverage_df = pd.read_excel("coverage.xlsx")
                    chart_data = []
                    for index, row in coverage_df.iterrows():
                        time_slot = row['Time']
                        target = row['Target']
                        scheduled = get_scheduled_count(time_slot, day)
                        chart_data.append({
                            "Time": time_slot,
                            "Target": target,
                            "Scheduled": scheduled
                        })
                    df_chart = pd.DataFrame(chart_data)
                    st.line_chart(df_chart.set_index("Time"))
                else:
                    st.info("Please ensure coverage.xlsx is in your project folder.")

    st.write("---")
    weekly_total = sum(budgets.values())
    st.metric("Total Weekly Hour Budget:", f"{weekly_total:.1f} hours")

    if st.button("Generate Schedule"):
        with st.spinner("Calculating optimal shifts and breaks..."):
            auto_generate_schedule()
            export_schedule_to_excel()
        st.success("Schedule generated successfully!")
        
        with open("weekly_schedule_output.xlsx", "rb") as f:
            st.download_button(
                label="📥 Download Weekly Schedule",
                data=f,
                file_name="weekly_schedule_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )