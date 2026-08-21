import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"] 
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope) 
client = gspread.authorize(creds) 

sheet = client.open("partners").sheet1 
df = pd.read_excel("partners.xlsx") 
df = df.fillna("") 

data = [df.columns.values.tolist()] + df.values.tolist() 
sheet.update("A1", data) 
print("Google Sheet successfully seeded!")