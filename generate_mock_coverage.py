import pandas as pd 
import datetime

times = [] 
headcount = [] 

curr_dt = datetime.datetime.combine(datetime.date.today(), datetime.time(4, 30)) 
end_dt = datetime.datetime.combine(datetime.date.today(), datetime.time(21, 30))

while curr_dt <= end_dt: 
    t_str = curr_dt.strftime("%H:%M") 
    times.append(t_str) 
    
    hour = curr_dt.hour 
    if hour < 5: 
        count = 3 
    elif 5 <= hour < 7: 
        count = 5 
    elif 7 <= hour < 9: 
        count = 8 
    elif 9 <= hour < 11: 
        count = 6 
    elif 11 <= hour < 14: 
        count = 7 
    elif 14 <= hour < 17: 
        count = 4 
    elif 17 <= hour < 19: 
        count = 5 
    else: 
        count = 3 
        
    headcount.append(count) 
    curr_dt += datetime.timedelta(minutes=15)

df = pd.DataFrame({"Time": times, "Target": headcount}) 
df.to_excel("coverage.xlsx", index=False) 

print("Mock coverage.xlsx generated successfully!")