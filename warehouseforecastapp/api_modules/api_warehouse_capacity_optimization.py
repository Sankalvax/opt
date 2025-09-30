import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')

class WarehouseCapacityOptimizer:
    def __init__(self):
        self.warehouses = ['Atlanta', 'Nashville', 'Chicago', 'NY', 'LA']
        self.products = ['Footwear', 'Apparel']
        self.warehouse_capacities = {}
        self.business_rules = {}
        
    def load_existing_forecasts(self):
        """Load existing warehouse forecasts and capacity data"""
        print("📊 Loading existing warehouse forecasts and capacity data...")
        
        # Load warehouse capacity assumptions
        with open('../outputs/warehouse_assumptions.json', 'r') as f:
            assumptions = json.load(f)
            self.warehouse_capacities = assumptions['warehouse_config']
            self.business_rules = assumptions['business_rules']
        
        # Load existing warehouse forecast results
        try:
            with open('warehouse_product_rolling_forecast_12m.json', 'r') as f:
                self.warehouse_forecasts = json.load(f)
            print("✅ Loaded 12-month warehouse forecasts")
        except FileNotFoundError:
            print("⚠️  12-month forecast not found, trying 6-month...")
            with open('warehouse_product_rolling_forecast_6m.json', 'r') as f:
                self.warehouse_forecasts = json.load(f)
            print("✅ Loaded 6-month warehouse forecasts")
        
        horizon = self.warehouse_forecasts['metadata']['forecast_horizon_months']
        print(f"📈 Analyzing {horizon}-month forecast horizon")
        
    def analyze_capacity_utilization(self):
        """Analyze capacity utilization patterns for each warehouse"""
        print("\n🏭 Analyzing warehouse capacity utilization patterns...")
        
        capacity_analysis = {}
        
        for warehouse in self.warehouses:
            warehouse_data = self.warehouse_forecasts['warehouses'][warehouse]
            monthly_positions = warehouse_data['monthly_positions']
            
            if not monthly_positions:
                continue
                
            # Extract capacity utilization timeline
            utilization_timeline = []
            inventory_timeline = []
            months = []
            
            for position in monthly_positions:
                months.append(position['date'])
                utilization_timeline.append(position['capacity_utilization'])
                inventory_timeline.append(position['warehouse_total_after'])
            
            # Calculate capacity metrics
            max_capacity = self.warehouse_capacities[warehouse]['capacity']
            avg_utilization = np.mean(utilization_timeline)
            max_utilization = np.max(utilization_timeline)
            min_utilization = np.min(utilization_timeline)
            final_utilization = utilization_timeline[-1] if utilization_timeline else 0
            
            # Trend analysis
            if len(utilization_timeline) > 1:
                trend_slope = np.polyfit(range(len(utilization_timeline)), utilization_timeline, 1)[0]
                trend = 'Increasing' if trend_slope > 0.5 else 'Decreasing' if trend_slope < -0.5 else 'Stable'
            else:
                trend = 'Stable'
                trend_slope = 0
            
            # Risk assessment
            risk_level = self._assess_capacity_risk(avg_utilization, max_utilization, trend_slope)
            
            # Available capacity calculation
            current_inventory = inventory_timeline[-1] if inventory_timeline else 0
            available_capacity = max_capacity - current_inventory
            available_capacity_pct = (available_capacity / max_capacity) * 100
            
            capacity_analysis[warehouse] = {
                'warehouse_info': {
                    'name': warehouse,
                    'max_capacity': max_capacity,
                    'current_inventory': round(current_inventory),
                    'available_capacity': round(available_capacity),
                    'available_capacity_pct': round(available_capacity_pct, 1)
                },
                'utilization_metrics': {
                    'average_utilization': round(avg_utilization, 1),
                    'max_utilization': round(max_utilization, 1),
                    'min_utilization': round(min_utilization, 1),
                    'final_utilization': round(final_utilization, 1),
                    'utilization_range': round(max_utilization - min_utilization, 1)
                },
                'trend_analysis': {
                    'trend_direction': trend,
                    'trend_slope': round(trend_slope, 2),
                    'volatility': round(np.std(utilization_timeline), 1)
                },
                'risk_assessment': risk_level,
                'timeline_data': {
                    'months': months,
                    'utilization_pct': [round(u, 1) for u in utilization_timeline],
                    'inventory_levels': [round(i) for i in inventory_timeline]
                }
            }
            
            print(f"  ✅ {warehouse}: {final_utilization:.1f}% utilized, {trend} trend, {risk_level['level']} risk")
        
        return capacity_analysis
    
    def _assess_capacity_risk(self, avg_util, max_util, trend_slope):
        """Assess capacity risk level for a warehouse"""
        risk_score = 0
        risk_factors = []
        
        # High utilization risk
        if avg_util > 80:
            risk_score += 3
            risk_factors.append('High average utilization')
        elif avg_util > 60:
            risk_score += 1
            risk_factors.append('Moderate utilization')
        
        # Peak capacity risk
        if max_util > 95:
            risk_score += 3
            risk_factors.append('Near capacity peaks')
        elif max_util > 85:
            risk_score += 2
            risk_factors.append('High peak utilization')
        
        # Trend risk
        if trend_slope > 1.0:
            risk_score += 2
            risk_factors.append('Rapidly increasing trend')
        elif trend_slope > 0.5:
            risk_score += 1
            risk_factors.append('Increasing trend')
        
        # Determine risk level
        if risk_score >= 5:
            level = 'HIGH'
        elif risk_score >= 3:
            level = 'MEDIUM'
        elif risk_score >= 1:
            level = 'LOW'
        else:
            level = 'MINIMAL'
        
        return {
            'level': level,
            'score': risk_score,
            'factors': risk_factors if risk_factors else ['Low risk profile']
        }
    
    def identify_transfer_opportunities(self, capacity_analysis):
        """Identify optimal transfer opportunities between warehouses"""
        print("\n🔄 Identifying inter-warehouse transfer opportunities...")
        
        transfer_opportunities = []
        
        # Sort warehouses by utilization
        warehouses_by_util = sorted(
            capacity_analysis.items(), 
            key=lambda x: x[1]['utilization_metrics']['final_utilization'],
            reverse=True
        )
        
        high_util_warehouses = [w for w, data in warehouses_by_util[:3] 
                               if data['utilization_metrics']['final_utilization'] > 70]
        low_util_warehouses = [w for w, data in warehouses_by_util[-3:] 
                              if data['utilization_metrics']['final_utilization'] < 50]
        
        print(f"  High utilization warehouses: {high_util_warehouses}")
        print(f"  Low utilization warehouses: {low_util_warehouses}")
        
        # Generate transfer recommendations
        for source_warehouse in high_util_warehouses:
            source_data = capacity_analysis[source_warehouse]
            
            for dest_warehouse in low_util_warehouses:
                dest_data = capacity_analysis[dest_warehouse]
                
                if source_warehouse == dest_warehouse:
                    continue
                
                # Calculate optimal transfer amount
                transfer_analysis = self._calculate_optimal_transfer(
                    source_warehouse, source_data,
                    dest_warehouse, dest_data
                )
                
                if transfer_analysis['recommended_transfer'] > 0:
                    transfer_opportunities.append(transfer_analysis)
        
        # Sort by impact/priority
        transfer_opportunities.sort(key=lambda x: x['impact_metrics']['utilization_improvement'], reverse=True)
        
        print(f"  ✅ Identified {len(transfer_opportunities)} transfer opportunities")
        
        return transfer_opportunities
    
    def _calculate_optimal_transfer(self, source_wh, source_data, dest_wh, dest_data):
        """Calculate optimal transfer amount between two warehouses"""
        
        # Current state
        source_util = source_data['utilization_metrics']['final_utilization']
        dest_util = dest_data['utilization_metrics']['final_utilization']
        source_inventory = source_data['warehouse_info']['current_inventory']
        dest_inventory = dest_data['warehouse_info']['current_inventory']
        source_capacity = source_data['warehouse_info']['max_capacity']
        dest_capacity = dest_data['warehouse_info']['max_capacity']
        
        # Target utilization levels (from business rules)
        target_util = self.business_rules['capacity_utilization']['optimal_range'][1] * 100  # 80%
        max_transfer_pct = self.business_rules['transfer_recommendations']['max_transfer_percentage']  # 50%
        min_transfer_size = self.business_rules['transfer_recommendations']['minimum_transfer_size']  # 10,000
        
        # Calculate transfer amounts to balance utilization
        # Goal: Bring source down to target, dest up towards target
        
        source_excess = (source_util - target_util) / 100 * source_capacity
        dest_deficit = (target_util - dest_util) / 100 * dest_capacity
        
        # Maximum transferable amount (don't exceed limits)
        max_transferable = min(
            source_inventory * max_transfer_pct,  # Max % of source inventory
            dest_capacity - dest_inventory,       # Available space in destination
            source_excess,                        # Amount to reduce source to target
            dest_deficit                          # Amount to bring dest to target
        )
        
        # Recommended transfer amount
        recommended_transfer = max(0, min(max_transferable, source_excess * 0.7))  # 70% of excess
        
        if recommended_transfer < min_transfer_size:
            recommended_transfer = 0  # Too small to be worth it
        
        # Calculate post-transfer state
        new_source_inventory = source_inventory - recommended_transfer
        new_dest_inventory = dest_inventory + recommended_transfer
        new_source_util = (new_source_inventory / source_capacity) * 100
        new_dest_util = (new_dest_inventory / dest_capacity) * 100
        
        # Impact metrics
        utilization_improvement = (source_util - new_source_util) + (new_dest_util - dest_util)
        risk_reduction = self._calculate_risk_reduction(source_data, new_source_util)
        
        # Cost estimation (simplified)
        distance_factor = self._get_distance_factor(source_wh, dest_wh)
        transfer_cost = recommended_transfer * 0.10 * distance_factor  # $0.10 per unit base cost
        capacity_savings = (source_util - new_source_util) / 100 * source_capacity * 0.05  # $0.05 per unit storage cost saved
        
        return {
            'transfer_id': f"{source_wh}_to_{dest_wh}",
            'source_warehouse': source_wh,
            'destination_warehouse': dest_wh,
            'recommended_transfer': round(recommended_transfer),
            'current_state': {
                'source_utilization': round(source_util, 1),
                'dest_utilization': round(dest_util, 1),
                'source_inventory': source_inventory,
                'dest_inventory': dest_inventory
            },
            'projected_state': {
                'source_utilization': round(new_source_util, 1),
                'dest_utilization': round(new_dest_util, 1),
                'source_inventory': round(new_source_inventory),
                'dest_inventory': round(new_dest_inventory)
            },
            'impact_metrics': {
                'utilization_improvement': round(utilization_improvement, 1),
                'risk_reduction': risk_reduction,
                'source_util_change': round(new_source_util - source_util, 1),
                'dest_util_change': round(new_dest_util - dest_util, 1)
            },
            'cost_analysis': {
                'estimated_transfer_cost': round(transfer_cost, 2),
                'estimated_storage_savings': round(capacity_savings, 2),
                'net_benefit': round(capacity_savings - transfer_cost, 2),
                'roi_percentage': round(((capacity_savings - transfer_cost) / transfer_cost * 100), 1) if transfer_cost > 0 else 0
            },
            'priority': 'HIGH' if utilization_improvement > 10 else 'MEDIUM' if utilization_improvement > 5 else 'LOW',
            'urgency': 'IMMEDIATE' if source_util > 90 else 'PLANNED'
        }
    
    def _calculate_risk_reduction(self, source_data, new_utilization):
        """Calculate risk reduction from transfer"""
        old_risk_score = source_data['risk_assessment']['score']
        
        # Simulate new risk assessment
        new_risk_score = 0
        if new_utilization > 80:
            new_risk_score += 3
        elif new_utilization > 60:
            new_risk_score += 1
            
        return max(0, old_risk_score - new_risk_score)
    
    def _get_distance_factor(self, source_wh, dest_wh):
        """Get distance factor for transfer cost calculation"""
        # Simplified distance matrix (in reality, would use actual distances)
        distance_factors = {
            ('Atlanta', 'Nashville'): 1.0,
            ('Atlanta', 'Chicago'): 1.5,
            ('Atlanta', 'NY'): 2.0,
            ('Atlanta', 'LA'): 3.0,
            ('Nashville', 'Chicago'): 1.2,
            ('Nashville', 'NY'): 1.8,
            ('Nashville', 'LA'): 2.5,
            ('Chicago', 'NY'): 1.5,
            ('Chicago', 'LA'): 2.2,
            ('NY', 'LA'): 3.5
        }
        
        key = (source_wh, dest_wh)
        reverse_key = (dest_wh, source_wh)
        
        return distance_factors.get(key, distance_factors.get(reverse_key, 2.0))
    
    def generate_capacity_alerts(self, capacity_analysis):
        """Generate capacity-related alerts and recommendations"""
        print("\n🚨 Generating capacity alerts...")
        
        alerts = []
        
        for warehouse, data in capacity_analysis.items():
            util_metrics = data['utilization_metrics']
            risk = data['risk_assessment']
            
            # Over-capacity alerts
            if util_metrics['max_utilization'] > 95:
                alerts.append({
                    'type': 'OVER_CAPACITY_RISK',
                    'severity': 'HIGH',
                    'warehouse': warehouse,
                    'message': f"{warehouse} reached {util_metrics['max_utilization']:.1f}% capacity - immediate action required",
                    'recommendation': 'Initiate emergency transfers or expand storage',
                    'priority': 1
                })
            elif util_metrics['final_utilization'] > 85:
                alerts.append({
                    'type': 'HIGH_UTILIZATION',
                    'severity': 'MEDIUM',
                    'warehouse': warehouse,
                    'message': f"{warehouse} operating at {util_metrics['final_utilization']:.1f}% capacity",
                    'recommendation': 'Plan transfers to optimize capacity utilization',
                    'priority': 2
                })
            
            # Under-utilization alerts
            elif util_metrics['final_utilization'] < 30:
                alerts.append({
                    'type': 'UNDER_UTILIZATION',
                    'severity': 'LOW',
                    'warehouse': warehouse,
                    'message': f"{warehouse} only {util_metrics['final_utilization']:.1f}% utilized - opportunity for optimization",
                    'recommendation': 'Consider accepting transfers from high-utilization warehouses',
                    'priority': 3
                })
            
            # Trend alerts
            if data['trend_analysis']['trend_direction'] == 'Increasing' and util_metrics['final_utilization'] > 70:
                alerts.append({
                    'type': 'CAPACITY_TREND_WARNING',
                    'severity': 'MEDIUM',
                    'warehouse': warehouse,
                    'message': f"{warehouse} showing increasing utilization trend - monitor closely",
                    'recommendation': 'Prepare contingency plans for capacity management',
                    'priority': 2
                })
        
        # Sort by priority
        alerts.sort(key=lambda x: x['priority'])
        
        print(f"  ✅ Generated {len(alerts)} capacity alerts")
        
        return alerts
    
    def generate_product_level_recommendations(self):
        """Generate product-specific transfer recommendations"""
        print("\n👟 Generating product-level optimization recommendations...")
        
        product_recommendations = {}
        
        for product in self.products:
            product_recommendations[product] = {
                'warehouse_levels': {},
                'transfer_suggestions': []
            }
            
            # Extract product-specific inventory levels
            for warehouse in self.warehouses:
                warehouse_data = self.warehouse_forecasts['warehouses'][warehouse]
                if warehouse in warehouse_data['products'] and product in warehouse_data['products'][warehouse]:
                    
                    rolling_inventory = warehouse_data['products'][warehouse]['products'][product]['rolling_inventory']
                    if rolling_inventory:
                        # Get final month's data
                        final_month = max(rolling_inventory.keys())
                        final_inventory = rolling_inventory[final_month]['ending_position']
                        utilization = rolling_inventory[final_month]['capacity_utilization']
                        
                        product_recommendations[product]['warehouse_levels'][warehouse] = {
                            'current_inventory': final_inventory,
                            'utilization_contribution': utilization,
                            'monthly_net_flow': rolling_inventory[final_month]['net_flow']
                        }
            
            # Generate product-specific transfer suggestions
            levels = product_recommendations[product]['warehouse_levels']
            
            if len(levels) > 1:
                # Find high and low inventory warehouses for this product
                sorted_warehouses = sorted(levels.items(), key=lambda x: x[1]['current_inventory'], reverse=True)
                
                high_inventory_wh = sorted_warehouses[0]
                low_inventory_wh = sorted_warehouses[-1]
                
                if (high_inventory_wh[1]['current_inventory'] > low_inventory_wh[1]['current_inventory'] * 2 and
                    high_inventory_wh[1]['current_inventory'] > 10000):
                    
                    transfer_amount = (high_inventory_wh[1]['current_inventory'] - low_inventory_wh[1]['current_inventory']) // 4
                    
                    product_recommendations[product]['transfer_suggestions'].append({
                        'from_warehouse': high_inventory_wh[0],
                        'to_warehouse': low_inventory_wh[0],
                        'recommended_quantity': transfer_amount,
                        'reason': f'Balance {product} inventory distribution',
                        'impact': f'Reduces {high_inventory_wh[0]} {product} surplus'
                    })
        
        return product_recommendations

    def simulate_high_demand_scenario(self, capacity_analysis):
        """Simulate a high-demand scenario to demonstrate transfer capabilities"""
        print("\n🎯 Simulating high-demand scenario for demonstration...")
        
        # Create a scenario where some warehouses are overloaded
        scenario_analysis = {}
        
        for warehouse, data in capacity_analysis.items():
            scenario_data = data.copy()
            
            # Simulate different load scenarios
            if warehouse == 'Atlanta':
                # Simulate 85% utilization
                new_inventory = data['warehouse_info']['max_capacity'] * 0.85
                scenario_data['warehouse_info']['current_inventory'] = round(new_inventory)
                scenario_data['utilization_metrics']['final_utilization'] = 85.0
                scenario_data['trend_analysis']['trend_direction'] = 'Increasing'
                scenario_data['risk_assessment'] = self._assess_capacity_risk(85.0, 87.0, 1.2)
            elif warehouse == 'Nashville':
                # Simulate 90% utilization
                new_inventory = data['warehouse_info']['max_capacity'] * 0.90
                scenario_data['warehouse_info']['current_inventory'] = round(new_inventory)
                scenario_data['utilization_metrics']['final_utilization'] = 90.0
                scenario_data['trend_analysis']['trend_direction'] = 'Increasing'
                scenario_data['risk_assessment'] = self._assess_capacity_risk(90.0, 92.0, 1.5)
            elif warehouse == 'Chicago':
                # Simulate 30% utilization (can accept transfers)
                new_inventory = data['warehouse_info']['max_capacity'] * 0.30
                scenario_data['warehouse_info']['current_inventory'] = round(new_inventory)
                scenario_data['utilization_metrics']['final_utilization'] = 30.0
            elif warehouse == 'LA':
                # Simulate 25% utilization (can accept transfers)
                new_inventory = data['warehouse_info']['max_capacity'] * 0.25
                scenario_data['warehouse_info']['current_inventory'] = round(new_inventory)
                scenario_data['utilization_metrics']['final_utilization'] = 25.0
            
            # Recalculate available capacity
            scenario_data['warehouse_info']['available_capacity'] = (
                scenario_data['warehouse_info']['max_capacity'] - 
                scenario_data['warehouse_info']['current_inventory']
            )
            scenario_data['warehouse_info']['available_capacity_pct'] = (
                scenario_data['warehouse_info']['available_capacity'] / 
                scenario_data['warehouse_info']['max_capacity'] * 100
            )
            
            scenario_analysis[warehouse] = scenario_data
        
        return scenario_analysis

def main():
    """Main execution function for warehouse capacity optimization"""
    print("🏭 WAREHOUSE CAPACITY OPTIMIZATION & TRANSFER RECOMMENDATIONS")
    print("=" * 70)
    
    optimizer = WarehouseCapacityOptimizer()
    
    # Load existing forecasts and capacity data
    optimizer.load_existing_forecasts()
    
    # Analyze capacity utilization patterns
    capacity_analysis = optimizer.analyze_capacity_utilization()
    
    # Identify transfer opportunities
    transfer_opportunities = optimizer.identify_transfer_opportunities(capacity_analysis)
    
    # Generate capacity alerts
    capacity_alerts = optimizer.generate_capacity_alerts(capacity_analysis)
    
    # Generate product-level recommendations
    product_recommendations = optimizer.generate_product_level_recommendations()
    
    # Simulate high-demand scenario for demonstration
    scenario_analysis = optimizer.simulate_high_demand_scenario(capacity_analysis)
    scenario_transfers = optimizer.identify_transfer_opportunities(scenario_analysis)
    scenario_alerts = optimizer.generate_capacity_alerts(scenario_analysis)
    
    # Create comprehensive results
    results = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'analysis_type': 'warehouse_capacity_optimization',
            'forecast_source': 'warehouse_product_rolling_forecast',
            'optimization_focus': 'capacity_utilization_and_transfers'
        },
        'current_state': {
            'capacity_analysis': capacity_analysis,
            'transfer_opportunities': transfer_opportunities,
            'capacity_alerts': capacity_alerts,
            'product_recommendations': product_recommendations
        },
        'high_demand_scenario': {
            'scenario_description': 'Simulated high-demand situation with Atlanta at 85% and Nashville at 90% capacity',
            'capacity_analysis': scenario_analysis,
            'transfer_opportunities': scenario_transfers,
            'capacity_alerts': scenario_alerts
        },
        'network_optimization_summary': {
            'total_warehouses_analyzed': len(capacity_analysis),
            'high_utilization_warehouses': len([w for w, data in capacity_analysis.items() 
                                               if data['utilization_metrics']['final_utilization'] > 80]),
            'transfer_opportunities_identified': len(transfer_opportunities),
            'total_alerts_generated': len(capacity_alerts),
            'high_priority_actions': len([a for a in capacity_alerts if a['priority'] <= 2]),
            'potential_cost_savings': sum([t['cost_analysis']['net_benefit'] 
                                         for t in transfer_opportunities if t['cost_analysis']['net_benefit'] > 0]),
            'scenario_demonstration': {
                'scenario_transfers': len(scenario_transfers),
                'scenario_alerts': len(scenario_alerts),
                'scenario_savings': sum([t['cost_analysis']['net_benefit'] 
                                       for t in scenario_transfers if t['cost_analysis']['net_benefit'] > 0])
            }
        }
    }
    
    # Save results
    output_file = 'warehouse_capacity_optimization.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Warehouse capacity optimization analysis saved to: {output_file}")
    
    # Print executive summary
    summary = results['network_optimization_summary']
    print(f"\n📊 Executive Summary:")
    print(f"   Warehouses Analyzed: {summary['total_warehouses_analyzed']}")
    print(f"   High Utilization: {summary['high_utilization_warehouses']} warehouses")
    print(f"   Transfer Opportunities: {summary['transfer_opportunities_identified']}")
    print(f"   Critical Alerts: {summary['high_priority_actions']}")
    print(f"   Potential Savings: ${summary['potential_cost_savings']:,.2f}")
    
    if transfer_opportunities:
        print(f"\n🔄 Top Transfer Recommendation:")
        top_transfer = transfer_opportunities[0]
        print(f"   {top_transfer['source_warehouse']} → {top_transfer['destination_warehouse']}")
        print(f"   Amount: {top_transfer['recommended_transfer']:,} units")
        print(f"   Impact: {top_transfer['impact_metrics']['utilization_improvement']:.1f}% utilization improvement")
        print(f"   ROI: {top_transfer['cost_analysis']['roi_percentage']:.1f}%")
    
    # Show scenario results
    print(f"\n🎯 High-Demand Scenario Results:")
    print(f"   Scenario Transfers: {len(scenario_transfers)}")
    print(f"   Scenario Alerts: {len(scenario_alerts)}")
    if scenario_transfers:
        top_scenario_transfer = scenario_transfers[0]
        print(f"   Top Scenario Transfer: {top_scenario_transfer['source_warehouse']} → {top_scenario_transfer['destination_warehouse']}")
        print(f"   Amount: {top_scenario_transfer['recommended_transfer']:,} units")
        print(f"   ROI: {top_scenario_transfer['cost_analysis']['roi_percentage']:.1f}%")

if __name__ == "__main__":
    main()