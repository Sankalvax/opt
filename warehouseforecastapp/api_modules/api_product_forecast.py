#!/usr/bin/env python3
"""
Product-Wise Forecasting API for Soles4Souls Dashboard
Separate Prophet models for different product types/categories
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Suppress Prophet's verbose logging
import logging
logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

class ProductForecastProcessor:
    """
    Product-specific forecasting using separate Prophet models
    """
    
    def __init__(self, data_dir='Datasets'):
        """Initialize with data directory"""
        self.data_dir = Path(data_dir)
        self.inflows = None
        self.outflows = None
        self.models = {}
        self.load_data()
    
    def load_data(self):
        """Load historical data"""
        try:
            self.inflows = pd.read_csv(self.data_dir/'train_inflows(in).csv', parse_dates=['Date'])
            self.outflows = pd.read_csv(self.data_dir/'train_outflows(in).csv', parse_dates=['Date'])
            print("✓ Product forecast data loaded successfully")
            return True
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def get_available_products(self):
        """Return available product hierarchies for filtering"""
        if self.inflows is None:
            return {}
        
        return {
            "product_types": sorted(self.inflows['Product_Type'].unique().tolist()),
            "categories": sorted(self.inflows['Category'].unique().tolist()),
            "brands": sorted(self.inflows['Brand'].unique().tolist()),
            "grades": sorted(self.inflows['Grade'].unique().tolist()),
            "warehouses": sorted(self.inflows['Warehouse'].unique().tolist()),
            "forecast_horizons": [3, 6, 9, 12],
            "forecast_types": ["inflows", "outflows", "net_flow", "all"]
        }
    
    def aggregate_product_data(self, df, product_filter, freq='M'):
        """Aggregate data by product and time period"""
        
        # Apply product filter
        filtered_df = df.copy()
        
        if 'product_types' in product_filter:
            filtered_df = filtered_df[filtered_df['Product_Type'].isin(product_filter['product_types'])]
        
        if 'categories' in product_filter:
            filtered_df = filtered_df[filtered_df['Category'].isin(product_filter['categories'])]
            
        if 'brands' in product_filter:
            filtered_df = filtered_df[filtered_df['Brand'].isin(product_filter['brands'])]
            
        if 'warehouses' in product_filter and product_filter['warehouses'] != ['All']:
            filtered_df = filtered_df[filtered_df['Warehouse'].isin(product_filter['warehouses'])]
        
        # Group by time period and sum quantities
        aggregated = filtered_df.groupby(pd.Grouper(key='Date', freq=freq))['Quantity'].sum().reset_index()
        
        # Prophet requires 'ds' and 'y' columns
        aggregated = aggregated.rename(columns={'Date': 'ds', 'Quantity': 'y'})
        
        # Remove zero/negative values
        aggregated = aggregated[aggregated['y'] > 0].reset_index(drop=True)
        
        return aggregated
    
    def train_product_prophet_model(self, data, product_name, flow_type):
        """Train Prophet model for specific product and flow type"""
        
        if len(data) < 12:  # Need at least 12 months of data
            print(f"⚠️ Insufficient data for {product_name} {flow_type}: {len(data)} months")
            return None
        
        try:
            from prophet import Prophet
            
            # Create Prophet model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                seasonality_mode='additive',
                growth='linear',
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10,
                n_changepoints=15,
                interval_width=0.80,
                mcmc_samples=0
            )
            
            # Fit model
            model.fit(data)
            
            print(f"✓ Trained {product_name} {flow_type} model ({len(data)} months)")
            return model
            
        except Exception as e:
            print(f"❌ Error training {product_name} {flow_type} model: {e}")
            return None
    
    def generate_product_forecast(self, model, horizon_months):
        """Generate forecast for specified horizon"""
        if model is None:
            return None
        
        try:
            # Create future dataframe
            future = model.make_future_dataframe(periods=horizon_months, freq='M')
            
            # Generate forecast
            forecast = model.predict(future)
            
            # Extract only future periods
            last_historical_date = model.history['ds'].max()
            future_forecast = forecast[forecast['ds'] > last_historical_date].reset_index(drop=True)
            
            return future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
            
        except Exception as e:
            print(f"❌ Error generating forecast: {e}")
            return None
    
    def calculate_model_performance(self, data, model, product_name, flow_type):
        """Calculate model performance metrics"""
        if model is None or len(data) < 24:
            return {"accuracy": "Insufficient data", "confidence": "Low", "mape": None}
        
        try:
            # Simple backtest on last 6 months
            train_data = data.iloc[:-6]
            test_data = data.iloc[-6:]
            
            # Retrain on training data
            temp_model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False, 
                daily_seasonality=False,
                mcmc_samples=0
            )
            temp_model.fit(train_data)
            
            # Predict test period
            future = temp_model.make_future_dataframe(periods=6, freq='M')
            forecast = temp_model.predict(future)
            
            # Compare predictions to actuals
            test_forecast = forecast.iloc[-6:]
            
            # Calculate MAPE
            actual_values = test_data['y'].values
            predicted_values = test_forecast['yhat'].values
            
            # Ensure same length
            min_len = min(len(actual_values), len(predicted_values))
            actual_values = actual_values[:min_len]
            predicted_values = predicted_values[:min_len]
            
            if len(actual_values) > 0:
                mape = np.mean(np.abs((actual_values - predicted_values) / (actual_values + 1e-9))) * 100
                
                if mape < 15:
                    accuracy = "High"
                elif mape < 25:
                    accuracy = "Medium"
                else:
                    accuracy = "Low"
                
                confidence = "High" if mape < 20 else "Medium" if mape < 30 else "Low"
                
                return {
                    "accuracy": accuracy,
                    "confidence": confidence,
                    "mape": round(float(mape), 1)
                }
            else:
                return {"accuracy": "Unable to calculate", "confidence": "Medium", "mape": None}
                
        except Exception as e:
            print(f"⚠️ Error calculating performance for {product_name} {flow_type}: {e}")
            return {"accuracy": "Error in calculation", "confidence": "Low", "mape": None}
    
    def process_product_forecasts(self, filters=None):
        """
        Main function to generate product-wise forecasts
        """
        if filters is None:
            filters = {}
        
        # Default parameters
        product_level = filters.get('product_level', 'product_type')
        horizon_months = filters.get('horizon_months', 6)
        forecast_type = filters.get('forecast_type', 'all')
        warehouses = filters.get('warehouses', ['All'])
        
        result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "filters_applied": filters,
                "product_level": product_level,
                "horizon_months": horizon_months,
                "data_source": "Product-specific historical data 2017-2022"
            },
            "forecasts": {},
            "model_performance": {},
            "summary": {}
        }
        
        try:
            # Determine products to forecast based on level
            if product_level == 'product_type':
                products = self.inflows['Product_Type'].unique()
                filter_key = 'product_types'
            elif product_level == 'category':
                products = self.inflows['Category'].unique()
                filter_key = 'categories'
            elif product_level == 'brand':
                products = self.inflows['Brand'].unique() 
                filter_key = 'brands'
            else:
                products = self.inflows['Product_Type'].unique()
                filter_key = 'product_types'
            
            # Process each product
            for product in products:
                print(f"\n--- Processing {product} ---")
                
                # Create product filter
                product_filter = {
                    filter_key: [product],
                    'warehouses': warehouses
                }
                
                product_result = {
                    "inflows": {},
                    "outflows": {},
                    "net_flow": {},
                    "metrics": {}
                }
                
                # Process inflows
                if forecast_type in ['inflows', 'all']:
                    inflow_data = self.aggregate_product_data(self.inflows, product_filter)
                    inflow_model = self.train_product_prophet_model(inflow_data, product, 'inflows')
                    inflow_forecast = self.generate_product_forecast(inflow_model, horizon_months)
                    
                    if inflow_forecast is not None:
                        # Convert to dictionary format
                        inflow_dict = {}
                        for _, row in inflow_forecast.iterrows():
                            month_key = row['ds'].strftime('%Y-%m')
                            inflow_dict[month_key] = {
                                "forecast": round(float(row['yhat']), 0),
                                "lower": round(float(row['yhat_lower']), 0),
                                "upper": round(float(row['yhat_upper']), 0)
                            }
                        
                        product_result["inflows"] = inflow_dict
                        
                        # Calculate performance
                        performance = self.calculate_model_performance(inflow_data, inflow_model, product, 'inflows')
                        if product not in result["model_performance"]:
                            result["model_performance"][product] = {}
                        result["model_performance"][product]["inflows"] = performance
                
                # Process outflows
                if forecast_type in ['outflows', 'all']:
                    outflow_data = self.aggregate_product_data(self.outflows, product_filter)
                    outflow_model = self.train_product_prophet_model(outflow_data, product, 'outflows')
                    outflow_forecast = self.generate_product_forecast(outflow_model, horizon_months)
                    
                    if outflow_forecast is not None:
                        # Convert to dictionary format
                        outflow_dict = {}
                        for _, row in outflow_forecast.iterrows():
                            month_key = row['ds'].strftime('%Y-%m')
                            outflow_dict[month_key] = {
                                "forecast": round(float(row['yhat']), 0),
                                "lower": round(float(row['yhat_lower']), 0),
                                "upper": round(float(row['yhat_upper']), 0)
                            }
                        
                        product_result["outflows"] = outflow_dict
                        
                        # Calculate performance
                        performance = self.calculate_model_performance(outflow_data, outflow_model, product, 'outflows')
                        if product not in result["model_performance"]:
                            result["model_performance"][product] = {}
                        result["model_performance"][product]["outflows"] = performance
                
                # Calculate net flow if both available
                if forecast_type in ['net_flow', 'all'] and product_result["inflows"] and product_result["outflows"]:
                    net_flow_dict = {}
                    for month in product_result["inflows"].keys():
                        if month in product_result["outflows"]:
                            inflow_val = product_result["inflows"][month]["forecast"]
                            outflow_val = product_result["outflows"][month]["forecast"]
                            net_flow_dict[month] = {
                                "forecast": round(inflow_val - outflow_val, 0),
                                "status": "SURPLUS" if inflow_val > outflow_val else "DEFICIT"
                            }
                    
                    product_result["net_flow"] = net_flow_dict
                
                # Add product metrics
                if product_result["inflows"] or product_result["outflows"]:
                    total_inflow = sum([v["forecast"] for v in product_result["inflows"].values()])
                    total_outflow = sum([v["forecast"] for v in product_result["outflows"].values()])
                    
                    product_result["metrics"] = {
                        "total_projected_inflow": total_inflow,
                        "total_projected_outflow": total_outflow,
                        "net_position": total_inflow - total_outflow,
                        "avg_monthly_inflow": round(total_inflow / horizon_months, 0) if horizon_months > 0 else 0,
                        "avg_monthly_outflow": round(total_outflow / horizon_months, 0) if horizon_months > 0 else 0
                    }
                
                result["forecasts"][product] = product_result
            
            # Generate summary
            total_inflow = sum([prod["metrics"].get("total_projected_inflow", 0) for prod in result["forecasts"].values()])
            total_outflow = sum([prod["metrics"].get("total_projected_outflow", 0) for prod in result["forecasts"].values()])
            
            result["summary"] = {
                "total_products_forecasted": len(result["forecasts"]),
                "forecast_horizon_months": horizon_months,
                "network_projected_inflow": total_inflow,
                "network_projected_outflow": total_outflow,
                "network_net_position": total_inflow - total_outflow,
                "products_with_surplus": len([p for p in result["forecasts"].values() if p["metrics"].get("net_position", 0) > 0]),
                "products_with_deficit": len([p for p in result["forecasts"].values() if p["metrics"].get("net_position", 0) < 0])
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Error processing product forecasts: {str(e)}",
                "metadata": result["metadata"]
            }

# API Functions
def get_product_filter_options():
    """API endpoint: Get product filtering options"""
    processor = ProductForecastProcessor()
    return processor.get_available_products()

def get_product_forecasts(filters=None):
    """API endpoint: Get product-specific forecasts"""
    processor = ProductForecastProcessor()
    return processor.process_product_forecasts(filters)

def get_product_comparison(filters=None):
    """API endpoint: Get product comparison data"""
    if filters is None:
        filters = {}
    
    # Set to get all forecast types for comparison
    filters['forecast_type'] = 'all'
    
    result = get_product_forecasts(filters)
    
    if "error" in result:
        return result
    
    # Extract comparison data
    comparison = {
        "metadata": result["metadata"],
        "product_comparison": {},
        "ranking": {
            "by_total_inflow": [],
            "by_total_outflow": [],
            "by_net_position": []
        }
    }
    
    for product, data in result["forecasts"].items():
        if "metrics" in data:
            comparison["product_comparison"][product] = {
                "projected_inflow": data["metrics"]["total_projected_inflow"],
                "projected_outflow": data["metrics"]["total_projected_outflow"], 
                "net_position": data["metrics"]["net_position"],
                "status": "SURPLUS" if data["metrics"]["net_position"] > 0 else "DEFICIT",
                "model_accuracy": result["model_performance"].get(product, {}).get("inflows", {}).get("accuracy", "Unknown")
            }
    
    # Generate rankings
    products_data = [(prod, data["metrics"]) for prod, data in result["forecasts"].items() if "metrics" in data]
    
    comparison["ranking"]["by_total_inflow"] = sorted(products_data, key=lambda x: x[1]["total_projected_inflow"], reverse=True)
    comparison["ranking"]["by_total_outflow"] = sorted(products_data, key=lambda x: x[1]["total_projected_outflow"], reverse=True)
    comparison["ranking"]["by_net_position"] = sorted(products_data, key=lambda x: x[1]["net_position"], reverse=True)
    
    return comparison

# Test function
if __name__ == "__main__":
    print("=== Testing Product Forecasting Processor ===")
    
    # Test 1: Get available products
    print("\n1. Available Product Options:")
    options = get_product_filter_options()
    for key, value in options.items():
        if isinstance(value, list):
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: {value}")
    
    # Test 2: Product-type level forecast (6 months)
    print("\n2. Product-Type Forecast (6 months):")
    forecast = get_product_forecasts({
        "product_level": "product_type",
        "horizon_months": 6,
        "forecast_type": "all",
        "warehouses": ["All"]
    })
    
    if "error" not in forecast:
        print(f"   ✓ Generated forecasts for {forecast['summary']['total_products_forecasted']} products")
        print(f"   ✓ Network projected inflow: {forecast['summary']['network_projected_inflow']:,.0f}")
        print(f"   ✓ Network projected outflow: {forecast['summary']['network_projected_outflow']:,.0f}")
        print(f"   ✓ Network net position: {forecast['summary']['network_net_position']:,.0f}")
        
        # Show sample forecast for first product
        first_product = list(forecast['forecasts'].keys())[0]
        first_forecast = forecast['forecasts'][first_product]
        print(f"\n   Sample {first_product} Forecast:")
        if first_forecast['inflows']:
            first_month = list(first_forecast['inflows'].keys())[0]
            inflow_val = first_forecast['inflows'][first_month]['forecast']
            print(f"   {first_month}: {inflow_val:,.0f} inflow units")
    else:
        print(f"   ❌ Error: {forecast['error']}")
    
    # Save sample output
    with open('sample_product_forecast_output.json', 'w') as f:
        json.dump(forecast, f, indent=2, default=str)
    
    print(f"\n✅ Sample output saved to 'sample_product_forecast_output.json'")