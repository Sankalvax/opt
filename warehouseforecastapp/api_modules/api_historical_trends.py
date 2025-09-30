#!/usr/bin/env python3
"""
Historical Trends Data Processor for Soles4Souls Dashboard
Processes historical data with filters for UI consumption
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class HistoricalTrendsProcessor:
    """
    Process historical inflows, outflows, and inventory data with various filters
    for dashboard UI consumption
    """
    
    def __init__(self, data_dir='Datasets'):
        """Initialize with data directory"""
        self.data_dir = Path(data_dir)
        self.inflows = None
        self.outflows = None
        self.inventory = None
        self.load_data()
    
    def load_data(self):
        """Load all historical data files"""
        try:
            # Load datasets
            self.inflows = pd.read_csv(self.data_dir/'train_inflows(in).csv', parse_dates=['Date'])
            self.outflows = pd.read_csv(self.data_dir/'train_outflows(in).csv', parse_dates=['Date'])  
            self.inventory = pd.read_csv(self.data_dir/'train_inventory(in).csv', parse_dates=['Date'])
            
            print("✓ Historical data loaded successfully")
            return True
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def get_available_filters(self):
        """Return all available filter options for UI"""
        if self.inflows is None:
            return {}
        
        filter_options = {
            "date_range": {
                "min_date": self.inflows['Date'].min().strftime('%Y-%m-%d'),
                "max_date": self.inflows['Date'].max().strftime('%Y-%m-%d')
            },
            "warehouses": sorted(self.inflows['Warehouse'].unique().tolist()),
            "product_types": sorted(self.inflows['Product_Type'].unique().tolist()),
            "categories": sorted(self.inflows['Category'].unique().tolist()),
            "brands": sorted(self.inflows['Brand'].unique().tolist()),
            "grades": sorted(self.inflows['Grade'].unique().tolist()),
            "aggregation_options": ["daily", "weekly", "monthly", "quarterly", "yearly"],
            "chart_types": ["inflows", "outflows", "inventory", "net_flow", "all"]
        }
        
        return filter_options
    
    def apply_filters(self, df, filters):
        """Apply filter criteria to dataframe"""
        filtered_df = df.copy()
        
        # Date range filter
        if 'start_date' in filters and filters['start_date']:
            start_date = pd.to_datetime(filters['start_date'])
            filtered_df = filtered_df[filtered_df['Date'] >= start_date]
            
        if 'end_date' in filters and filters['end_date']:
            end_date = pd.to_datetime(filters['end_date'])
            filtered_df = filtered_df[filtered_df['Date'] <= end_date]
        
        # Warehouse filter
        if 'warehouses' in filters and filters['warehouses']:
            if isinstance(filters['warehouses'], str):
                filters['warehouses'] = [filters['warehouses']]
            filtered_df = filtered_df[filtered_df['Warehouse'].isin(filters['warehouses'])]
        
        # Product type filter
        if 'product_types' in filters and filters['product_types']:
            if isinstance(filters['product_types'], str):
                filters['product_types'] = [filters['product_types']]
            filtered_df = filtered_df[filtered_df['Product_Type'].isin(filters['product_types'])]
        
        # Category filter
        if 'categories' in filters and filters['categories']:
            if isinstance(filters['categories'], str):
                filters['categories'] = [filters['categories']]
            filtered_df = filtered_df[filtered_df['Category'].isin(filters['categories'])]
        
        # Brand filter
        if 'brands' in filters and filters['brands']:
            if isinstance(filters['brands'], str):
                filters['brands'] = [filters['brands']]
            filtered_df = filtered_df[filtered_df['Brand'].isin(filters['brands'])]
        
        # Grade filter
        if 'grades' in filters and filters['grades']:
            if isinstance(filters['grades'], str):
                filters['grades'] = [filters['grades']]
            filtered_df = filtered_df[filtered_df['Grade'].isin(filters['grades'])]
        
        return filtered_df
    
    def aggregate_data(self, df, aggregation='monthly', value_col='Quantity'):
        """Aggregate data by time period"""
        
        freq_map = {
            'daily': 'D',
            'weekly': 'W', 
            'monthly': 'M',
            'quarterly': 'Q',
            'yearly': 'Y'
        }
        
        freq = freq_map.get(aggregation, 'M')
        
        # Group by date and aggregate
        aggregated = df.groupby(pd.Grouper(key='Date', freq=freq))[value_col].sum().reset_index()
        
        # Format date for frontend
        if aggregation == 'daily':
            aggregated['date_label'] = aggregated['Date'].dt.strftime('%Y-%m-%d')
        elif aggregation == 'weekly':
            aggregated['date_label'] = aggregated['Date'].dt.strftime('%Y-W%U')
        elif aggregation == 'monthly':
            aggregated['date_label'] = aggregated['Date'].dt.strftime('%Y-%m')
        elif aggregation == 'quarterly':
            aggregated['date_label'] = aggregated['Date'].dt.to_period('Q').astype(str)
        else:  # yearly
            aggregated['date_label'] = aggregated['Date'].dt.strftime('%Y')
        
        return aggregated
    
    def get_inventory_trends(self, filters=None):
        """Get inventory level trends with filters"""
        if filters is None:
            filters = {}
        
        aggregation = filters.get('aggregation', 'monthly')
        
        # For inventory, we can't filter by product attributes since it's aggregated
        # Just apply date filters
        filtered_inventory = self.inventory.copy()
        
        if 'start_date' in filters and filters['start_date']:
            start_date = pd.to_datetime(filters['start_date'])
            filtered_inventory = filtered_inventory[filtered_inventory['Date'] >= start_date]
            
        if 'end_date' in filters and filters['end_date']:
            end_date = pd.to_datetime(filters['end_date'])
            filtered_inventory = filtered_inventory[filtered_inventory['Date'] <= end_date]
        
        # Aggregate total inventory
        freq_map = {'daily': 'D', 'weekly': 'W', 'monthly': 'M', 'quarterly': 'Q', 'yearly': 'Y'}
        freq = freq_map.get(aggregation, 'M')
        
        # For inventory, take average within period (not sum)
        aggregated = filtered_inventory.groupby(pd.Grouper(key='Date', freq=freq)).agg({
            'Inventory_Level': 'mean',
            'Atlanta_Inventory': 'mean',
            'Nashville_Inventory': 'mean', 
            'NY_Inventory': 'mean',
            'LA_Inventory': 'mean',
            'Chicago_Inventory': 'mean'
        }).reset_index()
        
        # Format dates
        if aggregation == 'monthly':
            aggregated['date_label'] = aggregated['Date'].dt.strftime('%Y-%m')
        else:
            aggregated['date_label'] = aggregated['Date'].dt.strftime('%Y-%m-%d')
        
        return aggregated
    
    def process_historical_trends(self, filters=None):
        """
        Main function to process historical trends with filters
        Returns data ready for UI consumption
        """
        if filters is None:
            filters = {}
        
        # Default values
        aggregation = filters.get('aggregation', 'monthly')
        chart_type = filters.get('chart_type', 'all')
        
        result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "filters_applied": filters,
                "data_source": "Historical transaction data 2017-2022"
            },
            "chart_data": {},
            "summary_stats": {}
        }
        
        try:
            # Process inflows
            if chart_type in ['inflows', 'all']:
                filtered_inflows = self.apply_filters(self.inflows, filters)
                inflow_trends = self.aggregate_data(filtered_inflows, aggregation, 'Quantity')
                
                result["chart_data"]["inflows"] = {
                    "dates": inflow_trends['date_label'].tolist(),
                    "values": inflow_trends['Quantity'].tolist(),
                    "label": "Inflows (Donations Received)",
                    "color": "#28a745"
                }
                
                result["summary_stats"]["inflows"] = {
                    "total": float(filtered_inflows['Quantity'].sum()),
                    "average_per_period": float(inflow_trends['Quantity'].mean()),
                    "peak_period": inflow_trends.loc[inflow_trends['Quantity'].idxmax(), 'date_label'],
                    "peak_value": float(inflow_trends['Quantity'].max())
                }
            
            # Process outflows
            if chart_type in ['outflows', 'all']:
                filtered_outflows = self.apply_filters(self.outflows, filters)
                outflow_trends = self.aggregate_data(filtered_outflows, aggregation, 'Quantity')
                
                result["chart_data"]["outflows"] = {
                    "dates": outflow_trends['date_label'].tolist(),
                    "values": outflow_trends['Quantity'].tolist(),
                    "label": "Outflows (Items Distributed)",
                    "color": "#dc3545"
                }
                
                result["summary_stats"]["outflows"] = {
                    "total": float(filtered_outflows['Quantity'].sum()),
                    "average_per_period": float(outflow_trends['Quantity'].mean()),
                    "peak_period": outflow_trends.loc[outflow_trends['Quantity'].idxmax(), 'date_label'],
                    "peak_value": float(outflow_trends['Quantity'].max())
                }
            
            # Process inventory
            if chart_type in ['inventory', 'all']:
                inventory_trends = self.get_inventory_trends(filters)
                
                result["chart_data"]["inventory"] = {
                    "dates": inventory_trends['date_label'].tolist(),
                    "values": inventory_trends['Inventory_Level'].tolist(),
                    "label": "Total Inventory Level",
                    "color": "#007bff"
                }
                
                # Warehouse-specific inventory trends
                result["chart_data"]["inventory_by_warehouse"] = {}
                warehouse_colors = {
                    "Atlanta": "#ff6384",
                    "Nashville": "#36a2eb", 
                    "NY": "#cc65fe",
                    "LA": "#ffce56",
                    "Chicago": "#4bc0c0"
                }
                
                for warehouse in ['Atlanta', 'Nashville', 'NY', 'LA', 'Chicago']:
                    col_name = f'{warehouse}_Inventory'
                    result["chart_data"]["inventory_by_warehouse"][warehouse] = {
                        "dates": inventory_trends['date_label'].tolist(),
                        "values": inventory_trends[col_name].tolist(),
                        "label": f"{warehouse} Warehouse",
                        "color": warehouse_colors.get(warehouse, "#666666")
                    }
                
                result["summary_stats"]["inventory"] = {
                    "current_level": float(inventory_trends['Inventory_Level'].iloc[-1]) if len(inventory_trends) > 0 else 0,
                    "average_level": float(inventory_trends['Inventory_Level'].mean()),
                    "peak_level": float(inventory_trends['Inventory_Level'].max()),
                    "low_level": float(inventory_trends['Inventory_Level'].min())
                }
            
            # Calculate net flow if both inflows and outflows requested
            if chart_type in ['net_flow', 'all'] and 'inflows' in result["chart_data"] and 'outflows' in result["chart_data"]:
                inflow_vals = result["chart_data"]["inflows"]["values"]
                outflow_vals = result["chart_data"]["outflows"]["values"]
                
                # Ensure same length (pad shorter with zeros)
                max_len = max(len(inflow_vals), len(outflow_vals))
                inflow_vals += [0] * (max_len - len(inflow_vals))
                outflow_vals += [0] * (max_len - len(outflow_vals))
                
                net_flow = [inf - out for inf, out in zip(inflow_vals, outflow_vals)]
                
                result["chart_data"]["net_flow"] = {
                    "dates": result["chart_data"]["inflows"]["dates"][:len(net_flow)],
                    "values": net_flow,
                    "label": "Net Flow (Inflows - Outflows)",
                    "color": "#fd7e14"
                }
                
                result["summary_stats"]["net_flow"] = {
                    "average": float(np.mean(net_flow)),
                    "positive_periods": sum(1 for x in net_flow if x > 0),
                    "negative_periods": sum(1 for x in net_flow if x < 0)
                }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Error processing trends: {str(e)}",
                "metadata": result["metadata"]
            }

# API-style functions for NetSuite integration
def get_filter_options():
    """API endpoint: Get all available filter options"""
    processor = HistoricalTrendsProcessor()
    return processor.get_available_filters()

def get_historical_trends(filters=None):
    """API endpoint: Get historical trends with filters"""
    processor = HistoricalTrendsProcessor()
    return processor.process_historical_trends(filters)

def get_warehouse_comparison(filters=None):
    """API endpoint: Get warehouse comparison data"""
    processor = HistoricalTrendsProcessor()
    if filters is None:
        filters = {}
    
    filters['chart_type'] = 'all'  # Get all data types
    trends = processor.process_historical_trends(filters)
    
    # Extract warehouse-specific data
    warehouse_comparison = {
        "metadata": trends["metadata"],
        "warehouses": {}
    }
    
    if "inventory_by_warehouse" in trends["chart_data"]:
        for warehouse, data in trends["chart_data"]["inventory_by_warehouse"].items():
            warehouse_comparison["warehouses"][warehouse] = {
                "current_inventory": data["values"][-1] if data["values"] else 0,
                "average_inventory": np.mean(data["values"]) if data["values"] else 0,
                "trend_data": {
                    "dates": data["dates"],
                    "values": data["values"],
                    "color": data["color"]
                }
            }
    
    return warehouse_comparison

# Test function
if __name__ == "__main__":
    print("=== Testing Historical Trends Processor ===")
    
    # Test 1: Get available filters
    print("\n1. Available Filters:")
    filters = get_filter_options()
    for key, value in filters.items():
        if isinstance(value, list):
            print(f"   {key}: {len(value)} options")
        else:
            print(f"   {key}: {value}")
    
    # Test 2: Get monthly trends for all data
    print("\n2. Monthly Trends (All Data):")
    trends = get_historical_trends({
        "aggregation": "monthly",
        "chart_type": "all"
    })
    
    if "error" not in trends:
        print(f"   ✓ Generated {len(trends['chart_data'])} chart datasets")
        for chart_name, chart_data in trends['chart_data'].items():
            if isinstance(chart_data, dict) and 'values' in chart_data:
                print(f"   ✓ {chart_name}: {len(chart_data['values'])} data points")
    else:
        print(f"   ❌ Error: {trends['error']}")
    
    # Test 3: Filtered trends (Atlanta warehouse only, Footwear only)
    print("\n3. Filtered Trends (Atlanta + Footwear):")
    filtered_trends = get_historical_trends({
        "aggregation": "monthly",
        "warehouses": ["Atlanta"],
        "product_types": ["Footwear"],
        "chart_type": "all"
    })
    
    if "error" not in filtered_trends:
        print("   ✓ Filtered trends generated successfully")
        if "inflows" in filtered_trends["summary_stats"]:
            stats = filtered_trends["summary_stats"]["inflows"]
            print(f"   ✓ Atlanta Footwear Total Inflows: {stats['total']:,.0f} units")
    
    # Save sample output
    with open('sample_historical_trends_output.json', 'w') as f:
        json.dump(trends, f, indent=2)
    
    print(f"\n✅ Sample output saved to 'sample_historical_trends_output.json'")