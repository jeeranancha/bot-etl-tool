import os
import requests
import pandas as pd
from io import StringIO
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="BOT Fx Rate ETL")
templates = Jinja2Templates(directory="templates")

def format_decimal(val):
    if val is None or val == "":
        return ""
    try:
        return f"{float(val):.10f}"
    except ValueError:
        return ""

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/extract")
async def extract_fx(target_date: str = Form(...), api_token: str = Form(...)):
    # BOT API Endpoint
    url = f"https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period={target_date}&end_period={target_date}"
    headers = {
        "X-IBM-Client-Id": api_token,
        "Authorization": api_token,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return JSONResponse(
                content={"error": f"Failed to fetch data from BOT API: {response.text}"}, 
                status_code=400
            )
        
        data = response.json()
        details = data.get("result", {}).get("data", {}).get("data_detail", [])
        
        if not details:
            return JSONResponse(
                content={"error": "No data available for the selected date."},
                status_code=400
            )
            
        records = []
        for row in details:
            currency = row.get("currency_id", "").upper().strip()
            
            # Decimal string properties
            mid_rate_str = row.get("mid_rate")
            buying_transfer_str = row.get("buying_transfer")
            selling_str = row.get("selling")
            
            # JPY Adjustment divisor
            divisor = 100.0 if currency == "JPY" else 1.0
            
            fx_rate = (float(mid_rate_str) / divisor) if mid_rate_str else None
            buying_transfer = (float(buying_transfer_str) / divisor) if buying_transfer_str else None
            selling = (float(selling_str) / divisor) if selling_str else None
            
            records.append({
                "data_date": row.get("period", target_date),
                "from_currency": currency,
                "to_currency": "THB",
                "fx_rate": format_decimal(fx_rate),
                "buying_transfer": format_decimal(buying_transfer),
                "selling": format_decimal(selling)
            })
            
        # Add THB derived record
        records.append({
            "data_date": target_date,
            "from_currency": "THB",
            "to_currency": "THB",
            "fx_rate": format_decimal(1.0),
            "buying_transfer": format_decimal(1.0),
            "selling": format_decimal(1.0)
        })
        
        # Convert to Pandas DataFrame to generate CSV output
        df = pd.DataFrame(records)
        
        # Output strictly the columns the specification mapped
        columns_order = ["data_date", "from_currency", "to_currency", "fx_rate", "buying_transfer", "selling"]
        df = df[columns_order]
        
        # Generate CSV string
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        
        return JSONResponse(content={
            "records": records,
            "csv_data": csv_string
        })
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"An internal error occurred: {str(e)}"},
            status_code=500
        )
