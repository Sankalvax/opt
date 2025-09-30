from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
import warnings
from typing import Optional
from datetime import datetime
import logging

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Global Forecasting API", version="1.0.0")

# CORS middleware for NetSuite integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data cache
data_cache = {}

def clear_cache():
    """Clear the data cache to force reload"""
    global data_cache
    data_cache.clear()
    logger.info("Data cache cleared")

def load_data():
    """Load and process the data files"""
    if data_cache:
        return data_cache

    try:
        # Load datasets
        inflows = pd.read_csv('data/train_inflows.csv')
        inventory = pd.read_csv('data/train_inventory.csv')
        outflows = pd.read_csv('data/train_outflows.csv')

        # Convert dates
        inflows['Date'] = pd.to_datetime(inflows['Date'])
        inventory['Date'] = pd.to_datetime(inventory['Date'])
        outflows['Date'] = pd.to_datetime(outflows['Date'])

        # Aggregate daily data to monthly
        monthly_inflows = inflows.groupby(inflows['Date'].dt.to_period('M')).agg({
            'Quantity': 'sum',
            'Total_GIK': 'sum'
        }).reset_index()
        monthly_inflows['Date'] = monthly_inflows['Date'].dt.to_timestamp()

        monthly_outflows = outflows.groupby(outflows['Date'].dt.to_period('M')).agg({
            'Quantity': 'sum',
            'Total_GIK': 'sum'
        }).reset_index()
        monthly_outflows['Date'] = monthly_outflows['Date'].dt.to_timestamp()

        # Get monthly inventory (end of month)
        monthly_inventory = inventory.groupby(inventory['Date'].dt.to_period('M')).agg({
            'Inventory_Level': 'last'
        }).reset_index()
        monthly_inventory['Date'] = monthly_inventory['Date'].dt.to_timestamp()

        data_cache['monthly_inflows'] = monthly_inflows
        data_cache['monthly_outflows'] = monthly_outflows
        data_cache['monthly_inventory'] = monthly_inventory

        logger.info("Data loaded successfully")
        return data_cache
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

def create_forecast_arima(data, periods=12):
    """Create forecast using ARIMA"""
    ts = data.set_index('Date')['value']

    # Auto-select best ARIMA parameters or use default if auto fails
    try:
        from statsmodels.tsa.arima.model import ARIMA
        # Try a few common ARIMA orders and select best by AIC
        best_model = None
        best_aic = float('inf')
        orders = [(1,1,1), (2,1,2), (1,1,2), (2,1,1), (0,1,1)]

        for order in orders:
            try:
                model = ARIMA(ts, order=order).fit()
                if model.aic < best_aic:
                    best_aic = model.aic
                    best_model = model
            except:
                continue

        if best_model is None:
            model = ARIMA(ts, order=(1,1,1)).fit()
        else:
            model = best_model
    except:
        model = ARIMA(ts, order=(1,1,1)).fit()

    forecast = model.forecast(periods)

    # Continue forecast from the end of historical data
    last_date = ts.index.max()
    forecast_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=periods,
        freq='M'
    )

    # Get confidence intervals
    conf_int = model.get_forecast(periods).conf_int()

    forecast_df = pd.DataFrame({
        'Date': forecast_dates,
        'value': forecast,
        'lower_bound': conf_int.iloc[:,0],
        'upper_bound': conf_int.iloc[:,1]
    })

    return forecast_df

def create_forecast_exponential_smoothing(data, periods=12):
    """Create forecast using Exponential Smoothing"""
    ts = data.set_index('Date')['value']

    # Use simple exponential smoothing if not enough data for seasonal
    if len(ts) < 24:  # Less than 2 years of monthly data
        model = ExponentialSmoothing(
            ts,
            trend='add',
            seasonal=None
        ).fit()
    else:
        model = ExponentialSmoothing(
            ts,
            trend='add',
            seasonal='add',
            seasonal_periods=12
        ).fit()

    forecast = model.forecast(periods)
    # Continue forecast from the end of historical data
    last_date = ts.index.max()
    forecast_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=periods,
        freq='M'
    )

    forecast_df = pd.DataFrame({
        'Date': forecast_dates,
        'value': forecast,
        'lower_bound': forecast * 0.8,  # Simple confidence bounds
        'upper_bound': forecast * 1.2
    })

    return forecast_df

def format_response(data, forecast_df, metric_name):
    """Format response to match NetSuite frontend needs"""
    # Historical data
    historical = []
    for _, row in data.iterrows():
        historical.append({
            "date": row['Date'].strftime('%Y-%m'),
            "value": float(row['value'])
        })

    # Forecast data
    forecast = []
    for _, row in forecast_df.iterrows():
        forecast.append({
            "date": row['Date'].strftime('%Y-%m'),
            "value": float(row['value']),
            "lower_bound": float(row['lower_bound']),
            "upper_bound": float(row['upper_bound'])
        })

    # Statistics
    stats = {
        "total_months": len(data),
        "avg_value": float(data['value'].mean()),
        "date_range": {
            "start": data['Date'].min().strftime('%Y-%m'),
            "end": data['Date'].max().strftime('%Y-%m')
        }
    }

    return {
        "success": True,
        "metric": metric_name,
        "historical": historical,
        "forecast": forecast,
        "stats": stats,
        "fallback": False
    }

@app.get("/")
async def root():
    return {"message": "Global Forecasting API", "version": "1.0.0"}

@app.post("/api/clear-cache")
async def clear_data_cache():
    """Clear the data cache to force reload"""
    clear_cache()
    return {"message": "Data cache cleared successfully"}

@app.get("/api/inventory-level")
async def get_inventory_level_forecast(
    periods: int = Query(12, ge=6, le=24),
    method: str = Query("arima", regex="^(arima|exponential_smoothing)$")
):
    """Get inventory level forecast"""
    try:
        data = load_data()
        df = data['monthly_inventory'].rename(columns={'Inventory_Level': 'value'})

        if method == "arima":
            forecast_df = create_forecast_arima(df, periods)
        else:
            forecast_df = create_forecast_exponential_smoothing(df, periods)

        return format_response(df, forecast_df, "Inventory Level")
    except Exception as e:
        logger.error(f"Error in inventory level forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inflow-quantity")
async def get_inflow_quantity_forecast(
    periods: int = Query(12, ge=6, le=24),
    method: str = Query("arima", regex="^(arima|exponential_smoothing)$")
):
    """Get inflow quantity forecast"""
    try:
        data = load_data()
        df = data['monthly_inflows'].rename(columns={'Quantity': 'value'})

        if method == "arima":
            forecast_df = create_forecast_arima(df, periods)
        else:
            forecast_df = create_forecast_exponential_smoothing(df, periods)

        return format_response(df, forecast_df, "Inflow Quantity")
    except Exception as e:
        logger.error(f"Error in inflow quantity forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/outflow-quantity")
async def get_outflow_quantity_forecast(
    periods: int = Query(12, ge=6, le=24),
    method: str = Query("arima", regex="^(arima|exponential_smoothing)$")
):
    """Get outflow quantity forecast"""
    try:
        data = load_data()
        df = data['monthly_outflows'].rename(columns={'Quantity': 'value'})

        if method == "arima":
            forecast_df = create_forecast_arima(df, periods)
        else:
            forecast_df = create_forecast_exponential_smoothing(df, periods)

        return format_response(df, forecast_df, "Outflow Quantity")
    except Exception as e:
        logger.error(f"Error in outflow quantity forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inflow-gik-value")
async def get_inflow_gik_value_forecast(
    periods: int = Query(12, ge=6, le=24),
    method: str = Query("arima", regex="^(arima|exponential_smoothing)$")
):
    """Get inflow GIK value forecast"""
    try:
        data = load_data()
        df = data['monthly_inflows'].rename(columns={'Total_GIK': 'value'})

        if method == "arima":
            forecast_df = create_forecast_arima(df, periods)
        else:
            forecast_df = create_forecast_exponential_smoothing(df, periods)

        return format_response(df, forecast_df, "Inflow GIK Value")
    except Exception as e:
        logger.error(f"Error in inflow GIK value forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/outflow-gik-value")
async def get_outflow_gik_value_forecast(
    periods: int = Query(12, ge=6, le=24),
    method: str = Query("arima", regex="^(arima|exponential_smoothing)$")
):
    """Get outflow GIK value forecast"""
    try:
        data = load_data()
        df = data['monthly_outflows'].rename(columns={'Total_GIK': 'value'})

        if method == "arima":
            forecast_df = create_forecast_arima(df, periods)
        else:
            forecast_df = create_forecast_exponential_smoothing(df, periods)

        return format_response(df, forecast_df, "Outflow GIK Value")
    except Exception as e:
        logger.error(f"Error in outflow GIK value forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)