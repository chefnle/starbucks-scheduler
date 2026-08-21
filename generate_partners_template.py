import pandas as pd

columns = [ 
    "Name", 
    "Role", 
    "Is Keyholder", 
    "Min Hours", 
    "Max Hours", 
    "Monday", 
    "Tuesday", 
    "Wednesday", 
    "Thursday", 
    "Friday", 
    "Saturday", 
    "Sunday" 
]

partners_data = [ 
    { 
        "Name": "Nate Le", 
        "Role": "Store Manager", 
        "Is Keyholder": True, 
        "Min Hours": 35.0, 
        "Max Hours": 40.0, 
        "Monday": "07:00-15:30", 
        "Tuesday": "04:30-22:00", 
        "Wednesday": "04:30-22:00", 
        "Thursday": "04:30-22:00", 
        "Friday": "04:30-22:00", 
        "Saturday": "04:30-22:00", 
        "Sunday": "04:30-22:00" 
    }, 
    { 
        "Name": "Kenna Perryman", 
        "Role": "Shift Supervisor", 
        "Is Keyholder": True, 
        "Min Hours": 25.0, 
        "Max Hours": 30.0, 
        "Monday": "", 
        "Tuesday": "04:30-15:00", 
        "Wednesday": "04:30-15:00", 
        "Thursday": "04:30-15:00", 
        "Friday": "04:30-15:00", 
        "Saturday": "", 
        "Sunday": "04:30-15:00" 
    }, 
    { 
        "Name": "Izzy Schedel", 
        "Role": "Shift Supervisor", 
        "Is Keyholder": True, 
        "Min Hours": 30.0, 
        "Max Hours": 35.0, 
        "Monday": "04:30-22:00", 
        "Tuesday": "04:30-22:00", 
        "Wednesday": "04:30-22:00", 
        "Thursday": "04:30-22:00", 
        "Friday": "04:30-22:00", 
        "Saturday": "04:30-22:00", 
        "Sunday": "04:30-22:00" 
    }, 
    { 
        "Name": "Alice", 
        "Role": "Barista", 
        "Is Keyholder": False, 
        "Min Hours": 15.0, 
        "Max Hours": 20.0, 
        "Monday": "04:30-22:00", 
        "Tuesday": "04:30-22:00", 
        "Wednesday": "04:30-22:00", 
        "Thursday": "04:30-22:00", 
        "Friday": "04:30-22:00", 
        "Saturday": "04:30-22:00", 
        "Sunday": "04:30-22:00" 
    }, 
    { 
        "Name": "Bob", 
        "Role": "Barista", 
        "Is Keyholder": False, 
        "Min Hours": 10.0, 
        "Max Hours": 15.0, 
        "Monday": "", 
        "Tuesday": "", 
        "Wednesday": "", 
        "Thursday": "", 
        "Friday": "", 
        "Saturday": "", 
        "Sunday": "12:00-22:00" 
    }, 
    { 
        "Name": "Charlie", 
        "Role": "Barista", 
        "Is Keyholder": False, 
        "Min Hours": 20.0, 
        "Max Hours": 25.0, 
        "Monday": "04:30-22:00", 
        "Tuesday": "04:30-22:00", 
        "Wednesday": "04:30-22:00", 
        "Thursday": "04:30-22:00", 
        "Friday": "04:30-22:00", 
        "Saturday": "04:30-22:00", 
        "Sunday": "04:30-22:00" 
    } 
]

df = pd.DataFrame(partners_data, columns=columns) 
df.to_excel("partners.xlsx", index=False) 
print("Updated partners.xlsx with Min and Max hours successfully generated!")