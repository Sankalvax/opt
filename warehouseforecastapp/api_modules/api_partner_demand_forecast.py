import pandas as pd
import numpy as np
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

class PartnerDemandForecaster:
    def __init__(self):
        self.partners = []
        self.prophet_models = {}
        self.training_data = {}
        
    def load_data(self):
        """Load historical outflow data"""
        print("📊 Loading partner demand data...")
        self.outflows = pd.read_csv('../Datasets/train_outflows(in).csv')
        self.outflows['Date'] = pd.to_datetime(self.outflows['Date'])
        
        # Extract region from address
        self.outflows['Region'] = self.outflows['Partner_Address'].str.extract(r'Region (\d+)')
        
        # Get unique partners
        self.partners = self.outflows['Partner'].unique().tolist()
        
        print(f"Loaded {len(self.outflows):,} transactions")
        print(f"Found {len(self.partners)} unique partners")
        print(f"Date range: {self.outflows['Date'].min()} to {self.outflows['Date'].max()}")
        
    def prepare_partner_training_data(self):
        """Prepare monthly time series data for each partner"""
        print("\n🔄 Preparing partner training data...")
        
        for partner in self.partners:
            partner_data = self.outflows[self.outflows['Partner'] == partner].copy()
            
            if len(partner_data) > 0:
                # Monthly aggregation by product type
                monthly_data = partner_data.groupby([
                    pd.Grouper(key='Date', freq='MS'),
                    'Product_Type'
                ])['Quantity'].sum().reset_index()
                
                self.training_data[partner] = {}
                
                for product_type in ['Footwear', 'Apparel']:
                    product_data = monthly_data[monthly_data['Product_Type'] == product_type].copy()
                    
                    if not product_data.empty:
                        # Fill missing months with 0
                        date_range = pd.date_range(
                            start=product_data['Date'].min(),
                            end=product_data['Date'].max(),
                            freq='MS'
                        )
                        
                        complete_data = pd.DataFrame({'Date': date_range})
                        complete_data = complete_data.merge(
                            product_data[['Date', 'Quantity']], 
                            on='Date', 
                            how='left'
                        ).fillna(0)
                        
                        # Prophet format
                        complete_data.columns = ['ds', 'y']
                        self.training_data[partner][product_type] = complete_data
                        
                        print(f"  ✅ {partner} {product_type}: {len(complete_data)} months of data")
                    else:
                        # Empty data - create minimal structure
                        self.training_data[partner][product_type] = pd.DataFrame(columns=['ds', 'y'])
                        print(f"  ⚠️  {partner} {product_type}: No historical data")
        
        print(f"✅ Prepared training data for {len(self.training_data)} partners")
    
    def train_prophet_models(self):
        """Train Prophet models for each partner × product combination"""
        print("\n🤖 Training Prophet models...")
        
        model_count = 0
        failed_models = 0
        
        for partner in self.partners:
            if partner in self.training_data:
                self.prophet_models[partner] = {}
                
                for product_type in ['Footwear', 'Apparel']:
                    data = self.training_data[partner][product_type]
                    
                    if len(data) >= 12:  # Need at least 12 months
                        try:
                            print(f"  Training: {partner} {product_type}")
                            
                            model = Prophet(
                                yearly_seasonality=True,
                                weekly_seasonality=False,
                                daily_seasonality=False,
                                seasonality_mode='additive',
                                changepoint_prior_scale=0.1,
                                interval_width=0.8
                            )
                            
                            model.fit(data)
                            self.prophet_models[partner][product_type] = model
                            model_count += 1
                            
                        except Exception as e:
                            print(f"    ❌ Failed: {str(e)}")
                            self.prophet_models[partner][product_type] = None
                            failed_models += 1
                    else:
                        print(f"    ⚠️  {partner} {product_type}: Insufficient data ({len(data)} months)")
                        self.prophet_models[partner][product_type] = None
                        failed_models += 1
        
        print(f"✅ Successfully trained {model_count} Prophet models")
        print(f"   Failed/Insufficient: {failed_models} models")
    
    def generate_partner_forecasts(self, horizon_months=12, partners_filter=None):
        """Generate Prophet-based forecasts for all partners"""
        print(f"\n🔮 Generating {horizon_months}-month Prophet forecasts...")
        
        if partners_filter:
            target_partners = [p for p in partners_filter if p in self.partners]
        else:
            target_partners = self.partners
        
        # Create forecast dates
        start_date = datetime(2023, 1, 1)
        forecast_dates = [start_date + relativedelta(months=i) for i in range(horizon_months)]
        future_df = pd.DataFrame({'ds': forecast_dates})
        
        results = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'forecast_horizon_months': horizon_months,
                'partners_forecasted': len(target_partners),
                'forecast_method': 'Prophet Time Series Models',
                'confidence_interval': 80
            },
            'partner_forecasts': {}
        }
        
        for partner in target_partners:
            print(f"  Forecasting: {partner}")
            
            # Get partner metadata
            partner_data = self.outflows[self.outflows['Partner'] == partner]
            partner_region = partner_data['Region'].mode()[0] if len(partner_data) > 0 else 'Unknown'
            historical_volume = partner_data['Quantity'].sum()
            
            partner_forecast = {
                'partner_info': {
                    'name': partner,
                    'region': f"Region {partner_region}",
                    'historical_total_volume': int(historical_volume),
                    'historical_monthly_avg': int(historical_volume / 72) if historical_volume > 0 else 0  # 6 years of data
                },
                'product_forecasts': {},
                'monthly_totals': {},
                'forecast_summary': {}
            }
            
            total_forecasts_by_month = {}
            
            for product_type in ['Footwear', 'Apparel']:
                if (partner in self.prophet_models and 
                    product_type in self.prophet_models[partner] and
                    self.prophet_models[partner][product_type] is not None):
                    
                    # Generate Prophet forecast
                    model = self.prophet_models[partner][product_type]
                    forecast = model.predict(future_df)
                    
                    product_forecast = {}
                    
                    for i, date in enumerate(forecast_dates):
                        month_key = date.strftime('%Y-%m')
                        
                        predicted_value = max(0, forecast['yhat'].iloc[i])
                        lower_bound = max(0, forecast['yhat_lower'].iloc[i])
                        upper_bound = max(0, forecast['yhat_upper'].iloc[i])
                        
                        product_forecast[month_key] = {
                            'forecast': round(predicted_value),
                            'lower_bound': round(lower_bound),
                            'upper_bound': round(upper_bound),
                            'confidence': 'Prophet Model'
                        }
                        
                        # Add to monthly totals
                        if month_key not in total_forecasts_by_month:
                            total_forecasts_by_month[month_key] = 0
                        total_forecasts_by_month[month_key] += predicted_value
                    
                    partner_forecast['product_forecasts'][product_type] = product_forecast
                    
                else:
                    # No model available - use zeros
                    print(f"    ⚠️  No model for {partner} {product_type}")
                    product_forecast = {}
                    
                    for date in forecast_dates:
                        month_key = date.strftime('%Y-%m')
                        product_forecast[month_key] = {
                            'forecast': 0,
                            'lower_bound': 0,
                            'upper_bound': 0,
                            'confidence': 'No Historical Data'
                        }
                    
                    partner_forecast['product_forecasts'][product_type] = product_forecast
            
            # Store monthly totals
            for month_key, total_value in total_forecasts_by_month.items():
                partner_forecast['monthly_totals'][month_key] = {
                    'total_forecast': round(total_value),
                    'footwear_percentage': 0,
                    'apparel_percentage': 0
                }
                
                # Calculate percentages
                if total_value > 0:
                    footwear_val = partner_forecast['product_forecasts']['Footwear'][month_key]['forecast']
                    apparel_val = partner_forecast['product_forecasts']['Apparel'][month_key]['forecast']
                    
                    partner_forecast['monthly_totals'][month_key]['footwear_percentage'] = round((footwear_val / total_value) * 100, 1)
                    partner_forecast['monthly_totals'][month_key]['apparel_percentage'] = round((apparel_val / total_value) * 100, 1)
            
            # Calculate forecast summary
            total_forecast = sum(total_forecasts_by_month.values())
            partner_forecast['forecast_summary'] = {
                'total_predicted_volume': round(total_forecast),
                'monthly_average': round(total_forecast / horizon_months),
                'vs_historical_monthly': round((total_forecast / horizon_months) - partner_forecast['partner_info']['historical_monthly_avg']),
                'growth_indication': 'Growing' if (total_forecast / horizon_months) > partner_forecast['partner_info']['historical_monthly_avg'] else 'Stable/Declining'
            }
            
            results['partner_forecasts'][partner] = partner_forecast
        
        return results
    
    def generate_summary_analytics(self, forecast_results):
        """Generate summary analytics across all partners"""
        print("\n📊 Generating summary analytics...")
        
        analytics = {
            'network_summary': {
                'total_partners': len(forecast_results['partner_forecasts']),
                'total_predicted_volume': 0,
                'top_5_partners': [],
                'regional_breakdown': {},
                'product_mix': {'Footwear': 0, 'Apparel': 0}
            },
            'growth_insights': {
                'growing_partners': [],
                'declining_partners': [],
                'stable_partners': []
            },
            'risk_assessment': {
                'high_confidence_partners': [],
                'low_confidence_partners': []
            }
        }
        
        # Calculate totals and rankings
        partner_totals = []
        
        for partner, data in forecast_results['partner_forecasts'].items():
            total_vol = data['forecast_summary']['total_predicted_volume']
            analytics['network_summary']['total_predicted_volume'] += total_vol
            
            partner_totals.append((partner, total_vol, data['partner_info']['region']))
            
            # Growth categorization
            growth = data['forecast_summary']['growth_indication']
            if growth == 'Growing':
                analytics['growth_insights']['growing_partners'].append(partner)
            else:
                analytics['growth_insights']['stable_partners'].append(partner)
            
            # Confidence assessment
            has_models = any([
                'Prophet Model' in str(data['product_forecasts']['Footwear']),
                'Prophet Model' in str(data['product_forecasts']['Apparel'])
            ])
            
            if has_models:
                analytics['risk_assessment']['high_confidence_partners'].append(partner)
            else:
                analytics['risk_assessment']['low_confidence_partners'].append(partner)
            
            # Product mix
            for month_data in data['monthly_totals'].values():
                total_month = month_data['total_forecast']
                footwear_pct = month_data['footwear_percentage'] / 100
                apparel_pct = month_data['apparel_percentage'] / 100
                
                analytics['network_summary']['product_mix']['Footwear'] += total_month * footwear_pct
                analytics['network_summary']['product_mix']['Apparel'] += total_month * apparel_pct
        
        # Top 5 partners
        partner_totals.sort(key=lambda x: x[1], reverse=True)
        analytics['network_summary']['top_5_partners'] = [
            {'name': name, 'predicted_volume': vol, 'region': region} 
            for name, vol, region in partner_totals[:5]
        ]
        
        # Regional breakdown
        region_totals = {}
        for name, vol, region in partner_totals:
            if region not in region_totals:
                region_totals[region] = {'volume': 0, 'partners': 0}
            region_totals[region]['volume'] += vol
            region_totals[region]['partners'] += 1
        
        analytics['network_summary']['regional_breakdown'] = region_totals
        
        return analytics

def main():
    """Main execution function"""
    print("🏢 PARTNER DEMAND FORECAST - Prophet Models Only")
    print("=" * 60)
    
    forecaster = PartnerDemandForecaster()
    
    # Load data
    forecaster.load_data()
    
    # Prepare training data
    forecaster.prepare_partner_training_data()
    
    # Train Prophet models
    forecaster.train_prophet_models()
    
    # Generate forecasts
    forecast_results = forecaster.generate_partner_forecasts(horizon_months=12)
    
    # Generate analytics
    analytics = forecaster.generate_summary_analytics(forecast_results)
    
    # Combine results
    final_results = {**forecast_results, 'analytics': analytics}
    
    # Save results
    output_file = 'partner_demand_forecast_12m.json'
    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"\n✅ Partner demand forecast saved to: {output_file}")
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"   Partners Forecasted: {len(forecast_results['partner_forecasts'])}")
    print(f"   Total Predicted Volume: {analytics['network_summary']['total_predicted_volume']:,}")
    print(f"   High Confidence Partners: {len(analytics['risk_assessment']['high_confidence_partners'])}")
    print(f"   Growing Partners: {len(analytics['growth_insights']['growing_partners'])}")
    print(f"   Top Partner: {analytics['network_summary']['top_5_partners'][0]['name'] if analytics['network_summary']['top_5_partners'] else 'None'}")

if __name__ == "__main__":
    main()