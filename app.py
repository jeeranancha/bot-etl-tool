import os
import requests
import pandas as pd
from io import StringIO
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# 1. Initialize the app
app = FastAPI()

# 2. Setup templates folder
templates = Jinja2Templates(directory="templates")

def format_decimal(val):
    if val is None or val == "": return ""
    try: return f"{float(val):.10f}"
    except ValueError: return ""

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # This renders your index.html
        # CHANGE THIS ONE LINE ONLY
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/extract")
async def extract_fx(target_date: str = Form(...), api_token: str = Form(...)):
    url = f"https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period={target_date}&end_period={target_date}"
    headers = {"X-IBM-Client-Id": api_token, "Accept": "application/json"}
    headers = {
        "X-IBM-Client-Id": api_token,
        "Authorization": api_token,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return JSONResponse(content={"error": f"Failed: {response.text}"}, status_code=400)
        
        data = response.json()
        details = data.get("result", {}).get("data", {}).get("data_detail", [])
        if not details:
            return JSONResponse(content={"error": "No data for this date."}, status_code=400)
            
        records = []
        for row in details:
            currency = row.get("currency_id", "").upper().strip()
            div = 100.0 if currency == "JPY" else 1.0
            mid = float(row.get("mid_rate", 0))/div if row.get("mid_rate") else None
            buy = float(row.get("buying_transfer", 0))/div if row.get("buying_transfer") else None
            sel = float(row.get("selling", 0))/div if row.get("selling") else None
            
            records.append({
                "data_date": row.get("period", target_date), "from_currency": currency, "to_currency": "THB",
                "fx_rate": format_decimal(mid), "buying_transfer": format_decimal(buy), "selling": format_decimal(sel)
            })
        
        records.append({"data_date": target_date, "from_currency": "THB", "to_currency": "THB", "fx_rate": "1.0000000000", "buying_transfer": "1.0000000000", "selling": "1.0000000000"})
        
        df = pd.DataFrame(records)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        return {"records": records, "csv_data": csv_buffer.getvalue()}
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
