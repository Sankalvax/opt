import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

class WarehouseProductRollingForecast:
    def __init__(self):
        self.warehouses = ['Atlanta', 'Nashville', 'Chicago', 'NY', 'LA']
        self.products = ['Footwear', 'Apparel']
        self.prophet_models = {}
        self.starting_inventory = {}
        self.warehouse_capacities = {}
        self.business_rules = {}
        
    def load_data(self):
        """Load all required datasets"""
        self.inflows = pd.read_csv('../Datasets/train_inflows(in).csv')
        self.outflows = pd.read_csv('../Datasets/train_outflows(in).csv')
        self.inventory = pd.read_csv('../Datasets/train_inventory(in).csv')
        
        # Load assumptions
        with open('../outputs/warehouse_assumptions.json', 'r') as f:
            assumptions = json.load(f)
            self.warehouse_capacities = assumptions['warehouse_config']
            self.business_rules = assumptions['business_rules']
    
    def prepare_starting_inventory(self):
        """Extract starting inventory from the latest inventory data"""
        print("📦 Preparing starting inventory positions...")
        
        # Get the most recent inventory record
        self.inventory['Date'] = pd.to_datetime(self.inventory['Date'])
        latest_date = self.inventory['Date'].max()
        latest_inventory = self.inventory[self.inventory['Date'] == latest_date].iloc[0]
        
        print(f"Using inventory data from: {latest_date.strftime('%Y-%m-%d')}")
        
        # Extract starting positions for each warehouse × product combination
        for warehouse in self.warehouses:
            self.starting_inventory[warehouse] = {}
            for product in self.products:
                col_name = f"{warehouse}_{product}"
                if col_name in latest_inventory:
                    self.starting_inventory[warehouse][product] = latest_inventory[col_name]
                else:
                    print(f"⚠️  Column {col_name} not found, using 0")
                    self.starting_inventory[warehouse][product] = 0
        
        # Print starting positions
        print("\n📊 Starting Inventory Positions:")
        for warehouse in self.warehouses:
            total = sum(self.starting_inventory[warehouse].values())
            print(f"  {warehouse}: {total:,} units")
            for product in self.products:
                print(f"    - {product}: {self.starting_inventory[warehouse][product]:,}")
        
    def prepare_training_data(self):
        """Prepare time series data for Prophet models"""
        print("\n🔄 Preparing training data for Prophet models...")
        
        # Convert dates
        self.inflows['Date'] = pd.to_datetime(self.inflows['Date'])
        self.outflows['Date'] = pd.to_datetime(self.outflows['Date'])
        
        self.training_data = {}
        
        for warehouse in self.warehouses:
            self.training_data[warehouse] = {}
            
            for product in self.products:
                self.training_data[warehouse][product] = {}
                
                # Inflow data
                inflow_data = self.inflows[
                    (self.inflows['Warehouse'] == warehouse) & 
                    (self.inflows['Product_Type'] == product)
                ].groupby('Date')['Quantity'].sum().reset_index()
                
                # Resample to monthly and fill missing months with 0
                if not inflow_data.empty:
                    inflow_data.set_index('Date', inplace=True)
                    inflow_monthly = inflow_data.resample('MS').sum().fillna(0).reset_index()
                    inflow_monthly.columns = ['ds', 'y']
                    self.training_data[warehouse][product]['inflows'] = inflow_monthly
                else:
                    # Create empty dataframe with proper structure
                    self.training_data[warehouse][product]['inflows'] = pd.DataFrame(columns=['ds', 'y'])
                
                # Outflow data  
                outflow_data = self.outflows[
                    (self.outflows['Warehouse'] == warehouse) & 
                    (self.outflows['Product_Type'] == product)
                ].groupby('Date')['Quantity'].sum().reset_index()
                
                if not outflow_data.empty:
                    outflow_data.set_index('Date', inplace=True)
                    outflow_monthly = outflow_data.resample('MS').sum().fillna(0).reset_index()
                    outflow_monthly.columns = ['ds', 'y']
                    self.training_data[warehouse][product]['outflows'] = outflow_monthly
                else:
                    self.training_data[warehouse][product]['outflows'] = pd.DataFrame(columns=['ds', 'y'])
    
    def train_prophet_models(self):
        """Train Prophet models for each warehouse × product × flow type combination"""
        print("\n🤖 Training Prophet models...")
        
        total_models = len(self.warehouses) * len(self.products) * 2  # inflows + outflows
        model_count = 0
        
        for warehouse in self.warehouses:
            self.prophet_models[warehouse] = {}
            
            for product in self.products:
                self.prophet_models[warehouse][product] = {}
                
                for flow_type in ['inflows', 'outflows']:
                    model_count += 1
                    print(f"  Training model {model_count}/{total_models}: {warehouse} {product} {flow_type}")
                    
                    data = self.training_data[warehouse][product][flow_type]
                    
                    if len(data) >= 24:  # Need at least 2 years of data
                        model = Prophet(
                            yearly_seasonality=True,
                            weekly_seasonality=False, 
                            daily_seasonality=False,
                            seasonality_mode='additive'
                        )
                        
                        try:
                            model.fit(data)
                            self.prophet_models[warehouse][product][flow_type] = model
                        except Exception as e:
                            print(f"    ❌ Prophet failed: {str(e)}")
                            self.prophet_models[warehouse][product][flow_type] = None
                    else:
                        print(f"    ⚠️  Insufficient data ({len(data)} months), skipping")
                        self.prophet_models[warehouse][product][flow_type] = None
        
        print("✅ Model training completed!")
    
    def generate_rolling_forecast(self, horizon_months=12):
        """Generate rolling inventory forecast with month-by-month simulation"""
        print(f"\n📈 Generating {horizon_months}-month rolling forecast...")
        
        # Create forecast periods
        start_date = datetime(2023, 1, 1)
        forecast_dates = [start_date + relativedelta(months=i) for i in range(horizon_months)]
        
        results = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'forecast_horizon_months': horizon_months,
                'forecast_type': 'warehouse_product_rolling_inventory'
            },
            'warehouses': {},
            'network_summary': {},
            'alerts': []
        }
        
        # Initialize rolling inventory positions
        current_inventory = {}
        for warehouse in self.warehouses:
            current_inventory[warehouse] = self.starting_inventory[warehouse].copy()
        
        # Generate forecasts for each month
        monthly_forecasts = {}
        
        for warehouse in self.warehouses:
            monthly_forecasts[warehouse] = {}
            results['warehouses'][warehouse] = {
                'products': {},
                'warehouse_total': {},
                'capacity_info': self.warehouse_capacities[warehouse],
                'monthly_positions': []
            }
            
            for product in self.products:
                monthly_forecasts[warehouse][product] = {'inflows': {}, 'outflows': {}}
                results['warehouses'][warehouse]['products'][product] = {
                    'forecasts': {'inflows': {}, 'outflows': {}, 'net_flow': {}},
                    'rolling_inventory': {},
                    'alerts': []
                }
        
        # Generate predictions for each date
        for date in forecast_dates:
            month_key = date.strftime('%Y-%m')
            print(f"  Processing {month_key}...")
            
            # Predict flows for this month
            for warehouse in self.warehouses:
                for product in self.products:
                    for flow_type in ['inflows', 'outflows']:
                        model = self.prophet_models[warehouse][product][flow_type]
                        
                        if model:
                            future_df = pd.DataFrame({'ds': [date]})
                            forecast = model.predict(future_df)
                            predicted_value = max(0, forecast['yhat'].iloc[0])  # No negative flows
                            lower_bound = max(0, forecast['yhat_lower'].iloc[0])
                            upper_bound = max(0, forecast['yhat_upper'].iloc[0])
                        else:
                            # Fallback to historical average
                            hist_data = self.training_data[warehouse][product][flow_type]
                            if len(hist_data) > 0:
                                predicted_value = hist_data['y'].mean()
                                lower_bound = predicted_value * 0.8
                                upper_bound = predicted_value * 1.2
                            else:
                                predicted_value = lower_bound = upper_bound = 0
                        
                        monthly_forecasts[warehouse][product][flow_type][month_key] = {
                            'forecast': predicted_value,
                            'lower': lower_bound,
                            'upper': upper_bound
                        }
                        
                        # Store in results
                        results['warehouses'][warehouse]['products'][product]['forecasts'][flow_type][month_key] = {
                            'forecast': round(predicted_value),
                            'lower': round(lower_bound), 
                            'upper': round(upper_bound)
                        }
            
            # Update rolling inventory positions
            for warehouse in self.warehouses:
                warehouse_monthly_position = {
                    'date': month_key,
                    'products': {},
                    'warehouse_total_before': 0,
                    'warehouse_total_after': 0
                }
                
                for product in self.products:
                    inflow = monthly_forecasts[warehouse][product]['inflows'][month_key]['forecast']
                    outflow = monthly_forecasts[warehouse][product]['outflows'][month_key]['forecast']
                    net_flow = inflow - outflow
                    
                    # Current position before flows
                    before_position = current_inventory[warehouse][product]
                    
                    # New position after flows
                    after_position = max(0, before_position + net_flow)  # Can't go negative
                    
                    # Update current inventory
                    current_inventory[warehouse][product] = after_position
                    
                    # Store results
                    results['warehouses'][warehouse]['products'][product]['forecasts']['net_flow'][month_key] = {
                        'forecast': round(net_flow),
                        'status': 'SURPLUS' if net_flow > 0 else 'DEFICIT'
                    }
                    
                    results['warehouses'][warehouse]['products'][product]['rolling_inventory'][month_key] = {
                        'starting_position': round(before_position),
                        'inflow': round(inflow),
                        'outflow': round(outflow),
                        'net_flow': round(net_flow),
                        'ending_position': round(after_position),
                        'capacity_utilization': round((after_position / self.warehouse_capacities[warehouse]['capacity']) * 100, 1)
                    }
                    
                    warehouse_monthly_position['products'][product] = {
                        'before': round(before_position),
                        'after': round(after_position)
                    }
                    
                    warehouse_monthly_position['warehouse_total_before'] += before_position
                    warehouse_monthly_position['warehouse_total_after'] += after_position
                
                # Check for alerts
                total_capacity = self.warehouse_capacities[warehouse]['capacity']
                utilization = (warehouse_monthly_position['warehouse_total_after'] / total_capacity) * 100
                
                if utilization > 90:
                    alert = {
                        'warehouse': warehouse,
                        'date': month_key,
                        'type': 'OVER_CAPACITY',
                        'message': f"{warehouse} will be at {utilization:.1f}% capacity in {month_key}",
                        'severity': 'HIGH' if utilization > 95 else 'MEDIUM'
                    }
                    results['alerts'].append(alert)
                    results['warehouses'][warehouse]['products']['Overall'] = results['warehouses'][warehouse]['products'].get('Overall', {'alerts': []})
                    results['warehouses'][warehouse]['products']['Overall']['alerts'].append(alert)
                
                warehouse_monthly_position['capacity_utilization'] = round(utilization, 1)
                results['warehouses'][warehouse]['monthly_positions'].append(warehouse_monthly_position)
        
        # Generate network summary
        results['network_summary'] = self._generate_network_summary(results)
        
        return results
    
    def _generate_network_summary(self, results):
        """Generate network-level summary statistics"""
        total_network_inflow = 0
        total_network_outflow = 0
        total_network_inventory = 0
        
        warehouses_at_risk = 0
        product_alerts = {'Footwear': 0, 'Apparel': 0}
        
        for warehouse in self.warehouses:
            for product in self.products:
                # Sum all monthly forecasts
                product_data = results['warehouses'][warehouse]['products'][product]['forecasts']
                
                for month_data in product_data['inflows'].values():
                    total_network_inflow += month_data['forecast']
                
                for month_data in product_data['outflows'].values():
                    total_network_outflow += month_data['forecast']
                
                # Get final inventory position
                inventory_data = results['warehouses'][warehouse]['products'][product]['rolling_inventory']
                if inventory_data:
                    last_month = max(inventory_data.keys())
                    total_network_inventory += inventory_data[last_month]['ending_position']
        
        # Count high-utilization warehouses
        for alert in results['alerts']:
            if alert['severity'] == 'HIGH':
                warehouses_at_risk += 1
        
        return {
            'total_warehouses': len(self.warehouses),
            'total_products': len(self.products),
            'network_projected_inflow': round(total_network_inflow),
            'network_projected_outflow': round(total_network_outflow),
            'network_net_position': round(total_network_inflow - total_network_outflow),
            'final_network_inventory': round(total_network_inventory),
            'warehouses_at_risk': warehouses_at_risk,
            'total_alerts': len(results['alerts'])
        }

def main():
    """Main execution function"""
    print("🚀 Starting Warehouse × Product Rolling Inventory Forecast")
    print("=" * 60)
    
    forecaster = WarehouseProductRollingForecast()
    
    # Load data
    forecaster.load_data()
    forecaster.prepare_starting_inventory()
    forecaster.prepare_training_data()
    
    # Train models
    forecaster.train_prophet_models()
    
    # Generate forecasts for different horizons
    horizons = [6, 12]
    
    for horizon in horizons:
        print(f"\n🔮 Generating {horizon}-month forecast...")
        results = forecaster.generate_rolling_forecast(horizon_months=horizon)
        
        # Save results
        output_file = f'warehouse_product_rolling_forecast_{horizon}m.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✅ Results saved to: {output_file}")
        
        # Print summary
        summary = results['network_summary']
        print(f"\n📊 {horizon}-Month Network Summary:")
        print(f"   Network Projected Inflow: {summary['network_projected_inflow']:,}")
        print(f"   Network Projected Outflow: {summary['network_projected_outflow']:,}")
        print(f"   Network Net Position: {summary['network_net_position']:,}")
        print(f"   Final Network Inventory: {summary['final_network_inventory']:,}")
        print(f"   Warehouses at Risk: {summary['warehouses_at_risk']}")
        print(f"   Total Alerts: {summary['total_alerts']}")

if __name__ == "__main__":
    main()