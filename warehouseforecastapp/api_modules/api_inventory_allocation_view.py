import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

class InventoryAllocationEngine:
    def __init__(self):
        self.warehouses = ['Atlanta', 'Nashville', 'Chicago', 'NY', 'LA']
        self.products = ['Footwear', 'Apparel']
        self.categories = {
            'Footwear': ['Sneakers', 'Boots'],
            'Apparel': ['Shirts', 'Coats']
        }
        self.sizes = {
            'Footwear': ['5', '6', '7', '8', '9', '10', '11', '12'],
            'Apparel': ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        }
        
        # Initialize data containers
        self.historical_transactions = []
        self.partner_forecasts = None
        self.warehouse_forecasts = None
        
        # Partner preferences based on historical data analysis
        self.partner_preferences = {
            'Company C': {
                'region': 'West Africa',
                'preferred_products': {'Footwear': 70, 'Apparel': 30},
                'preferred_categories': {'Sneakers': 45, 'Boots': 25, 'Shirts': 20, 'Coats': 10},
                'size_distribution': {
                    'Footwear': {'7': 15, '8': 20, '9': 18, '10': 15, '11': 12, '6': 10, '12': 5, '5': 5},
                    'Apparel': {'M': 25, 'L': 20, 'XL': 15, 'S': 15, 'XXL': 15, 'XS': 10}
                },
                'delivery_schedule': 'monthly',
                'lead_time_days': 21
            },
            'Company E': {
                'region': 'Southeast Asia',
                'preferred_products': {'Footwear': 70, 'Apparel': 30},
                'preferred_categories': {'Sneakers': 40, 'Boots': 30, 'Shirts': 20, 'Coats': 10},
                'size_distribution': {
                    'Footwear': {'6': 20, '7': 18, '8': 15, '9': 15, '10': 12, '5': 10, '11': 6, '12': 4},
                    'Apparel': {'S': 30, 'M': 25, 'L': 15, 'XS': 15, 'XL': 10, 'XXL': 5}
                },
                'delivery_schedule': 'monthly',
                'lead_time_days': 18
            },
            'Company F': {
                'region': 'Eastern Europe',
                'preferred_products': {'Footwear': 70, 'Apparel': 30},
                'preferred_categories': {'Boots': 40, 'Sneakers': 30, 'Coats': 20, 'Shirts': 10},
                'size_distribution': {
                    'Footwear': {'8': 18, '9': 18, '10': 16, '7': 14, '11': 14, '6': 10, '12': 6, '5': 4},
                    'Apparel': {'L': 25, 'M': 20, 'XL': 20, 'XXL': 15, 'S': 15, 'XS': 5}
                },
                'delivery_schedule': 'monthly',
                'lead_time_days': 14
            },
            'Company H': {
                'region': 'Middle East',
                'preferred_products': {'Footwear': 69, 'Apparel': 31},
                'preferred_categories': {'Sneakers': 35, 'Boots': 34, 'Shirts': 21, 'Coats': 10},
                'size_distribution': {
                    'Footwear': {'7': 16, '8': 16, '9': 16, '10': 14, '6': 12, '11': 12, '5': 8, '12': 6},
                    'Apparel': {'M': 22, 'L': 22, 'S': 18, 'XL': 16, 'XXL': 12, 'XS': 10}
                },
                'delivery_schedule': 'monthly',
                'lead_time_days': 16
            },
            'Company I': {
                'region': 'Latin America',
                'preferred_products': {'Footwear': 70, 'Apparel': 30},
                'preferred_categories': {'Sneakers': 40, 'Boots': 30, 'Shirts': 18, 'Coats': 12},
                'size_distribution': {
                    'Footwear': {'7': 18, '8': 18, '6': 16, '9': 14, '5': 12, '10': 12, '11': 6, '12': 4},
                    'Apparel': {'S': 25, 'M': 25, 'L': 18, 'XS': 14, 'XL': 12, 'XXL': 6}
                },
                'delivery_schedule': 'monthly',
                'lead_time_days': 12
            }
        }
    
    def load_forecast_data(self):
        """Load historical data and generate runtime partner demand forecasts"""
        print("📊 Loading historical data and generating partner demand forecasts at runtime...")
        
        # Load historical transaction data for Prophet training FIRST
        try:
            # Load outflows (distribution) data for partner demand forecasting
            outflows_df = pd.read_csv('../Datasets/train_outflows(in).csv')
            # Convert to list of dictionaries for consistency
            self.historical_transactions = outflows_df.to_dict('records')
            print(f"✅ Loaded {len(self.historical_transactions):,} historical outflow records for Prophet training")
        except FileNotFoundError:
            print("⚠️  Historical transaction data not found in Datasets/")
            self.historical_transactions = []
        
        # Now generate partner demand forecasts in real-time using Prophet
        self.partner_forecasts = self._generate_runtime_partner_forecasts()
        if self.partner_forecasts:
            print("✅ Generated partner demand forecasts using Prophet models")
        else:
            print("⚠️  Prophet forecast generation failed - using fallback estimates")
        
        # Load warehouse inventory forecasts  
        try:
            with open('warehouse_product_rolling_forecast_12m.json', 'r') as f:
                self.warehouse_forecasts = json.load(f)
            print("✅ Loaded warehouse inventory forecasts")
        except FileNotFoundError:
            print("⚠️  Warehouse forecast file not found - using simulated data")
            self.warehouse_forecasts = None
    
    def _generate_runtime_partner_forecasts(self):
        """Generate partner demand forecasts using Prophet models at runtime"""
        print("🔮 Training Prophet models for runtime partner demand forecasting...")
        
        if not self.historical_transactions:
            print("⚠️  No historical data available for Prophet training")
            return None
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(self.historical_transactions)
        df['Date'] = pd.to_datetime(df['Date'])
        
        # All outflow data represents partner demand (distributions)
        demand_data = df.copy()
        
        if len(demand_data) < 50:
            print("⚠️  Insufficient distribution data for Prophet training")
            return None
        
        partner_forecasts = {}
        successful_models = 0
        
        # Get list of partners from historical data
        partners = demand_data['Partner'].unique()
        
        # Generate forecasts for each partner
        for partner in partners:
            if partner not in self.partner_preferences:
                continue  # Skip partners not in our preference list
                
            partner_data = demand_data[demand_data['Partner'] == partner]
            
            if len(partner_data) < 20:
                print(f"⚠️  Insufficient data for {partner} - skipping")
                continue
            
            try:
                # Generate separate forecasts for Sneakers and Boots
                partner_forecast = {
                    'partner_name': partner,
                    'forecasts': {},
                    'forecast_summary': {}
                }
                
                product_types = ['Sneakers', 'Boots']  # Using Category field from CSV
                monthly_totals = []
                
                for product in product_types:
                    product_data = partner_data[partner_data['Category'] == product]
                    
                    if len(product_data) < 10:
                        # Use overall partner data if product-specific data is insufficient
                        product_data = partner_data
                    
                    # Aggregate by month
                    monthly_data = product_data.groupby(
                        product_data['Date'].dt.to_period('M')
                    )['Quantity'].sum().reset_index()
                    
                    if len(monthly_data) < 8:
                        continue
                    
                    # Prepare Prophet dataset
                    monthly_data['ds'] = monthly_data['Date'].dt.start_time
                    monthly_data['y'] = monthly_data['Quantity']
                    prophet_data = monthly_data[['ds', 'y']]
                    
                    # Train Prophet model
                    model = Prophet(
                        yearly_seasonality=True,
                        weekly_seasonality=False,
                        daily_seasonality=False,
                        seasonality_mode='additive',
                        interval_width=0.8
                    )
                    
                    model.fit(prophet_data)
                    
                    # Generate 12-month forecast
                    future = model.make_future_dataframe(periods=12, freq='M')
                    forecast = model.predict(future)
                    
                    # Extract forecast results
                    future_forecast = forecast[-12:].copy()
                    future_forecast['month'] = future_forecast['ds'].dt.strftime('%Y-%m')
                    
                    product_forecast = []
                    for _, row in future_forecast.iterrows():
                        monthly_pred = max(0, int(row['yhat']))
                        product_forecast.append({
                            'month': row['month'],
                            'predicted_demand': monthly_pred,
                            'lower_bound': max(0, int(row['yhat_lower'])),
                            'upper_bound': max(0, int(row['yhat_upper'])),
                            'confidence': 'High' if monthly_pred > row['yhat_lower'] * 1.1 else 'Medium'
                        })
                        monthly_totals.append(monthly_pred)
                    
                    partner_forecast['forecasts'][product] = product_forecast
                
                # Calculate overall summary
                if monthly_totals:
                    partner_forecast['forecast_summary'] = {
                        'monthly_average': int(np.mean(monthly_totals)),
                        'monthly_min': int(np.min(monthly_totals)),
                        'monthly_max': int(np.max(monthly_totals)),
                        'total_12m_forecast': int(np.sum(monthly_totals)),
                        'forecast_trend': 'Stable',  # Simplified
                        'confidence_level': 'High',
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    partner_forecasts[partner] = partner_forecast
                    successful_models += 1
                    print(f"✅ Generated Prophet forecast for {partner}")
                
            except Exception as e:
                print(f"⚠️  Prophet model failed for {partner}: {str(e)}")
                continue
        
        if successful_models > 0:
            results = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'forecast_type': 'runtime_prophet_partner_demand',
                    'forecast_horizon_months': 12,
                    'successful_models': successful_models,
                    'total_partners_attempted': len([p for p in partners if p in self.partner_preferences])
                },
                'partner_forecasts': partner_forecasts
            }
            
            # Save runtime forecasts for reference
            with open('runtime_partner_forecasts.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"✅ Successfully generated {successful_models} Prophet models at runtime")
            return results
        else:
            print("❌ No successful Prophet models generated")
            return None
    
    def analyze_current_inventory_levels(self):
        """Analyze current inventory levels by warehouse and product"""
        print("\n📦 Analyzing current inventory levels by warehouse and product...")
        
        current_inventory = {}
        
        if self.warehouse_forecasts:
            for warehouse in self.warehouses:
                if warehouse in self.warehouse_forecasts['warehouses']:
                    warehouse_data = self.warehouse_forecasts['warehouses'][warehouse]
                    current_inventory[warehouse] = {}
                    
                    for product in self.products:
                        if product in warehouse_data['products']:
                            # Get the latest month's ending position
                            rolling_data = warehouse_data['products'][product]['rolling_inventory']
                            if rolling_data:
                                latest_month = max(rolling_data.keys())
                                current_stock = rolling_data[latest_month]['ending_position']
                            else:
                                current_stock = 0
                            
                            # Break down by category (estimated distribution)
                            current_inventory[warehouse][product] = {
                                'total': current_stock,
                                'categories': self._estimate_category_breakdown(current_stock, product)
                            }
        else:
            # Fallback to simulated inventory levels
            current_inventory = self._generate_simulated_inventory()
        
        # Print inventory summary
        print("📊 Current Inventory Distribution:")
        for warehouse, products in current_inventory.items():
            total_warehouse = sum([p['total'] for p in products.values()])
            print(f"  {warehouse}: {total_warehouse:,} units total")
            for product, details in products.items():
                print(f"    {product}: {details['total']:,} units")
        
        return current_inventory
    
    def _estimate_category_breakdown(self, total_stock, product_type):
        """Estimate category breakdown within a product type"""
        if product_type == 'Footwear':
            return {
                'Sneakers': int(total_stock * 0.65),  # 65% sneakers
                'Boots': int(total_stock * 0.35)      # 35% boots
            }
        else:  # Apparel
            return {
                'Shirts': int(total_stock * 0.60),    # 60% shirts  
                'Coats': int(total_stock * 0.40)      # 40% coats
            }
    
    def _generate_simulated_inventory(self):
        """Generate simulated inventory levels for demonstration"""
        simulated = {}
        base_inventory = {'Atlanta': 150000, 'Nashville': 170000, 'Chicago': 155000, 'NY': 160000, 'LA': 180000}
        
        for warehouse in self.warehouses:
            simulated[warehouse] = {}
            total_inventory = base_inventory[warehouse]
            
            # 70% Footwear, 30% Apparel
            footwear_total = int(total_inventory * 0.7)
            apparel_total = int(total_inventory * 0.3)
            
            simulated[warehouse]['Footwear'] = {
                'total': footwear_total,
                'categories': {
                    'Sneakers': int(footwear_total * 0.65),
                    'Boots': int(footwear_total * 0.35)
                }
            }
            
            simulated[warehouse]['Apparel'] = {
                'total': apparel_total,
                'categories': {
                    'Shirts': int(apparel_total * 0.60),
                    'Coats': int(apparel_total * 0.40)
                }
            }
        
        return simulated
    
    def calculate_partner_demand_requirements(self, horizon_months=3):
        """Calculate detailed partner requirements for the next few months"""
        print(f"\n🎯 Calculating partner demand requirements for {horizon_months} months...")
        
        partner_requirements = {}
        
        for partner, preferences in self.partner_preferences.items():
            partner_requirements[partner] = {
                'total_demand': {},
                'product_breakdown': {},
                'category_breakdown': {},
                'size_breakdown': {},
                'delivery_timeline': []
            }
            
            # Calculate monthly demand for next few months
            base_monthly_demand = self._get_partner_monthly_demand(partner)
            
            for month_idx in range(horizon_months):
                future_date = datetime.now() + relativedelta(months=month_idx+1)
                month_key = future_date.strftime('%Y-%m')
                
                # Apply seasonality (simplified)
                seasonal_factor = self._get_seasonal_factor(future_date.month, preferences['region'])
                monthly_demand = int(base_monthly_demand * seasonal_factor)
                
                partner_requirements[partner]['total_demand'][month_key] = monthly_demand
                
                # Break down by product type
                product_breakdown = {}
                for product, percentage in preferences['preferred_products'].items():
                    product_demand = int(monthly_demand * (percentage / 100))
                    product_breakdown[product] = product_demand
                
                partner_requirements[partner]['product_breakdown'][month_key] = product_breakdown
                
                # Break down by category
                category_breakdown = {}
                for category, percentage in preferences['preferred_categories'].items():
                    category_demand = int(monthly_demand * (percentage / 100))
                    category_breakdown[category] = category_demand
                
                partner_requirements[partner]['category_breakdown'][month_key] = category_breakdown
                
                # Break down by sizes (for first month only to save space)
                if month_idx == 0:
                    size_breakdown = {}
                    for product in self.products:
                        size_breakdown[product] = {}
                        product_demand = product_breakdown[product]
                        
                        for size, percentage in preferences['size_distribution'][product].items():
                            size_demand = int(product_demand * (percentage / 100))
                            if size_demand > 0:
                                size_breakdown[product][size] = size_demand
                    
                    partner_requirements[partner]['size_breakdown'] = size_breakdown
                
                # Calculate delivery deadline
                delivery_deadline = future_date - timedelta(days=preferences['lead_time_days'])
                partner_requirements[partner]['delivery_timeline'].append({
                    'month': month_key,
                    'ship_by_date': delivery_deadline.strftime('%Y-%m-%d'),
                    'deliver_by_date': future_date.strftime('%Y-%m-%d'),
                    'demand': monthly_demand
                })
        
        return partner_requirements
    
    def _get_partner_monthly_demand(self, partner):
        """Get base monthly demand for a partner"""
        if self.partner_forecasts and partner in self.partner_forecasts['partner_forecasts']:
            # Use actual forecast data
            forecast_data = self.partner_forecasts['partner_forecasts'][partner]
            return forecast_data['forecast_summary']['monthly_average']
        else:
            # Use estimated demand based on partner tier
            demand_mapping = {
                'Company C': 225000,  # Large partner
                'Company E': 195000,  # Large partner
                'Company F': 158000,  # Medium partner
                'Company H': 100000,  # Medium partner
                'Company I': 29000    # Small partner
            }
            return demand_mapping.get(partner, 50000)
    
    def _get_seasonal_factor(self, month, region):
        """Calculate seasonal demand factor"""
        # Simplified seasonal patterns by region
        seasonal_patterns = {
            'West Africa': {1: 1.2, 2: 1.1, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7, 
                           7: 0.8, 8: 0.9, 9: 1.0, 10: 1.1, 11: 1.3, 12: 1.4},
            'Southeast Asia': {1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.2, 6: 1.0,
                              7: 0.9, 8: 0.8, 9: 0.9, 10: 1.0, 11: 1.1, 12: 1.2},
            'Eastern Europe': {1: 1.3, 2: 1.2, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7,
                              7: 0.8, 8: 0.9, 9: 1.0, 10: 1.2, 11: 1.4, 12: 1.5},
            'Middle East': {1: 1.1, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.1, 6: 0.9,
                           7: 0.8, 8: 0.8, 9: 0.9, 10: 1.0, 11: 1.1, 12: 1.2},
            'Latin America': {1: 1.0, 2: 0.9, 3: 0.9, 4: 1.0, 5: 1.1, 6: 1.2,
                             7: 1.3, 8: 1.2, 9: 1.0, 10: 0.9, 11: 0.8, 12: 1.0}
        }
        
        return seasonal_patterns.get(region, {}).get(month, 1.0)
    
    def generate_allocation_recommendations(self, current_inventory, partner_requirements):
        """Generate specific allocation recommendations from warehouses to partners"""
        print("\n🚀 Generating warehouse-to-partner allocation recommendations...")
        
        recommendations = []
        
        for partner, requirements in partner_requirements.items():
            partner_prefs = self.partner_preferences[partner]
            
            # Focus on next month's requirements
            next_month = list(requirements['total_demand'].keys())[0]
            delivery_info = requirements['delivery_timeline'][0]
            
            # For each category this partner needs
            category_demands = requirements['category_breakdown'][next_month]
            
            for category, demand_quantity in category_demands.items():
                if demand_quantity < 1000:  # Skip small demands
                    continue
                
                # Find best warehouse to source from
                best_allocation = self._find_optimal_warehouse_allocation(
                    category, demand_quantity, current_inventory, partner_prefs
                )
                
                if best_allocation:
                    # Create detailed size breakdown
                    size_recommendations = self._create_size_breakdown(
                        category, demand_quantity, partner_prefs
                    )
                    
                    recommendation = {
                        'allocation_id': f"{best_allocation['warehouse']}_{partner}_{category}_{next_month}",
                        'from_warehouse': best_allocation['warehouse'],
                        'to_partner': partner,
                        'partner_region': partner_prefs['region'],
                        'product_details': {
                            'product_type': 'Footwear' if category in ['Sneakers', 'Boots'] else 'Apparel',
                            'category': category,
                            'total_quantity': demand_quantity,
                            'size_breakdown': size_recommendations,
                            'fulfillment_percentage': min(100, (best_allocation['available'] / demand_quantity) * 100)
                        },
                        'timeline': {
                            'month': next_month,
                            'ship_by_date': delivery_info['ship_by_date'],
                            'deliver_by_date': delivery_info['deliver_by_date'],
                            'lead_time_days': partner_prefs['lead_time_days']
                        },
                        'logistics': {
                            'distance_factor': self._get_distance_factor(best_allocation['warehouse'], partner_prefs['region']),
                            'shipping_cost_estimate': self._estimate_shipping_cost(demand_quantity, best_allocation['warehouse'], partner_prefs['region']),
                            'warehouse_utilization_impact': best_allocation.get('utilization_impact', 0)
                        },
                        'priority': self._calculate_allocation_priority(partner, category, demand_quantity, delivery_info),
                        'status': 'RECOMMENDED',
                        'confidence': best_allocation['confidence']
                    }
                    
                    recommendations.append(recommendation)
        
        # Sort by priority and ship date
        recommendations.sort(key=lambda x: (x['priority'], x['timeline']['ship_by_date']))
        
        print(f"✅ Generated {len(recommendations)} allocation recommendations")
        
        return recommendations
    
    def _find_optimal_warehouse_allocation(self, category, demand_quantity, current_inventory, partner_prefs):
        """Find the best warehouse to fulfill a specific category demand"""
        
        product_type = 'Footwear' if category in ['Sneakers', 'Boots'] else 'Apparel'
        warehouse_options = []
        
        for warehouse in self.warehouses:
            if (warehouse in current_inventory and 
                product_type in current_inventory[warehouse] and
                category in current_inventory[warehouse][product_type]['categories']):
                
                available_stock = current_inventory[warehouse][product_type]['categories'][category]
                
                if available_stock >= demand_quantity * 0.1:  # At least 10% of demand available
                    
                    # Calculate allocation score based on multiple factors
                    distance_score = 1.0 / self._get_distance_factor(warehouse, partner_prefs['region'])
                    availability_score = min(1.0, available_stock / demand_quantity)
                    
                    # Prefer warehouses with higher stock levels for this category
                    stock_ratio = available_stock / sum([inv[product_type]['categories'][category] 
                                                       for inv in current_inventory.values() 
                                                       if product_type in inv and category in inv[product_type]['categories']])
                    
                    combined_score = (distance_score * 0.4 + availability_score * 0.4 + stock_ratio * 0.2)
                    
                    warehouse_options.append({
                        'warehouse': warehouse,
                        'available': available_stock,
                        'score': combined_score,
                        'confidence': 'High' if available_stock >= demand_quantity else 'Medium'
                    })
        
        if warehouse_options:
            # Return the best option
            best_option = max(warehouse_options, key=lambda x: x['score'])
            return best_option
        
        return None
    
    def _create_size_breakdown(self, category, total_quantity, partner_prefs):
        """Create detailed size breakdown for allocation"""
        product_type = 'Footwear' if category in ['Sneakers', 'Boots'] else 'Apparel'
        size_distribution = partner_prefs['size_distribution'][product_type]
        
        size_breakdown = []
        
        for size, percentage in size_distribution.items():
            size_quantity = int(total_quantity * (percentage / 100))
            if size_quantity > 0:
                size_breakdown.append({
                    'size': size,
                    'quantity': size_quantity,
                    'percentage': percentage
                })
        
        return size_breakdown
    
    def _get_distance_factor(self, warehouse, partner_region):
        """Get distance factor for shipping cost calculation"""
        # Simplified distance matrix (warehouse to region)
        distance_matrix = {
            'Atlanta': {'West Africa': 2.5, 'Southeast Asia': 3.5, 'Eastern Europe': 2.8, 'Middle East': 3.0, 'Latin America': 1.8},
            'Nashville': {'West Africa': 2.6, 'Southeast Asia': 3.6, 'Eastern Europe': 2.9, 'Middle East': 3.1, 'Latin America': 1.9},
            'Chicago': {'West Africa': 2.8, 'Southeast Asia': 3.2, 'Eastern Europe': 2.5, 'Middle East': 2.9, 'Latin America': 2.2},
            'NY': {'West Africa': 2.2, 'Southeast Asia': 3.8, 'Eastern Europe': 2.0, 'Middle East': 2.8, 'Latin America': 2.5},
            'LA': {'West Africa': 3.5, 'Southeast Asia': 2.5, 'Eastern Europe': 3.8, 'Middle East': 3.5, 'Latin America': 1.5}
        }
        
        return distance_matrix.get(warehouse, {}).get(partner_region, 2.5)
    
    def _estimate_shipping_cost(self, quantity, warehouse, partner_region):
        """Estimate shipping cost for allocation"""
        base_cost_per_unit = 2.50  # Base shipping cost per unit
        distance_factor = self._get_distance_factor(warehouse, partner_region)
        
        # Volume discounts
        if quantity > 10000:
            volume_discount = 0.85
        elif quantity > 5000:
            volume_discount = 0.90
        else:
            volume_discount = 1.0
        
        total_cost = quantity * base_cost_per_unit * distance_factor * volume_discount
        return round(total_cost, 2)
    
    def _calculate_allocation_priority(self, partner, category, quantity, delivery_info):
        """Calculate priority level for allocation"""
        # High priority for large partners with urgent deadlines
        ship_date = datetime.strptime(delivery_info['ship_by_date'], '%Y-%m-%d')
        days_until_ship = (ship_date - datetime.now()).days
        
        if partner in ['Company C', 'Company E', 'Company F']:  # Large partners
            if days_until_ship <= 7:
                return 'URGENT'
            elif days_until_ship <= 14:
                return 'HIGH'
            else:
                return 'MEDIUM'
        else:
            if days_until_ship <= 7:
                return 'HIGH'
            elif days_until_ship <= 14:
                return 'MEDIUM'
            else:
                return 'LOW'

def main():
    """Main execution function for inventory allocation system"""
    print("📋 INVENTORY ALLOCATION VIEW - Warehouse to Partner Recommendations")
    print("=" * 70)
    
    allocator = InventoryAllocationEngine()
    
    # Load forecast data
    allocator.load_forecast_data()
    
    # Analyze current inventory levels
    current_inventory = allocator.analyze_current_inventory_levels()
    
    # Calculate partner requirements
    partner_requirements = allocator.calculate_partner_demand_requirements(horizon_months=3)
    
    # Generate allocation recommendations
    allocation_recommendations = allocator.generate_allocation_recommendations(
        current_inventory, partner_requirements
    )
    
    # Create comprehensive results
    results = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'forecast_horizon_months': 3,
            'allocation_type': 'warehouse_to_partner_detailed',
            'total_recommendations': len(allocation_recommendations)
        },
        'current_inventory_summary': {
            'total_warehouses': len(current_inventory),
            'warehouse_inventory': {wh: sum([p['total'] for p in products.values()]) 
                                   for wh, products in current_inventory.items()}
        },
        'partner_requirements_summary': {
            'partners_analyzed': len(partner_requirements),
            'total_monthly_demand': sum([sum(req['total_demand'].values()) for req in partner_requirements.values()]),
            'top_demand_partners': sorted(partner_requirements.keys(), 
                                        key=lambda p: sum(partner_requirements[p]['total_demand'].values()), 
                                        reverse=True)[:3]
        },
        'allocation_recommendations': allocation_recommendations,
        'priority_summary': {
            'urgent_allocations': len([r for r in allocation_recommendations if r['priority'] == 'URGENT']),
            'high_priority': len([r for r in allocation_recommendations if r['priority'] == 'HIGH']),
            'medium_priority': len([r for r in allocation_recommendations if r['priority'] == 'MEDIUM']),
            'low_priority': len([r for r in allocation_recommendations if r['priority'] == 'LOW'])
        }
    }
    
    # Save results
    output_file = 'inventory_allocation_recommendations.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Inventory allocation recommendations saved to: {output_file}")
    
    # Print executive summary
    print(f"\n📊 Executive Summary:")
    print(f"   Total Allocations: {len(allocation_recommendations)}")
    print(f"   Urgent Priority: {results['priority_summary']['urgent_allocations']}")
    print(f"   High Priority: {results['priority_summary']['high_priority']}")
    print(f"   Total Monthly Demand: {results['partner_requirements_summary']['total_monthly_demand']:,} units")
    
    if allocation_recommendations:
        print(f"\n🎯 Top 3 Allocation Recommendations:")
        for i, rec in enumerate(allocation_recommendations[:3], 1):
            details = rec['product_details']
            timeline = rec['timeline']
            print(f"   {i}. {rec['from_warehouse']} → {rec['to_partner']}")
            print(f"      Product: {details['total_quantity']:,} {details['category']}")
            print(f"      Ship by: {timeline['ship_by_date']} ({rec['priority']} priority)")
            print(f"      Cost: ${rec['logistics']['shipping_cost_estimate']:,.2f}")
            print()

if __name__ == "__main__":
    main()