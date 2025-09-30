import json
import sys
from datetime import datetime
from api_warehouse_capacity_optimization import WarehouseCapacityOptimizer

class WarehouseScenarioSimulator:
    def __init__(self):
        self.optimizer = WarehouseCapacityOptimizer()
        
    def run_custom_scenario(self, scenario_config):
        """Run a custom what-if scenario based on UI parameters"""
        print(f"🎯 Running custom scenario: {scenario_config.get('name', 'Unnamed Scenario')}")
        
        # Load base data
        self.optimizer.load_existing_forecasts()
        base_analysis = self.optimizer.analyze_capacity_utilization()
        
        # Apply scenario modifications
        scenario_analysis = self.apply_scenario_changes(base_analysis, scenario_config)
        
        # Generate recommendations
        transfer_opportunities = self.optimizer.identify_transfer_opportunities(scenario_analysis)
        capacity_alerts = self.optimizer.generate_capacity_alerts(scenario_analysis)
        
        # Create results
        results = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'scenario_name': scenario_config.get('name', 'Custom Scenario'),
                'scenario_type': scenario_config.get('type', 'custom'),
                'applied_changes': scenario_config.get('changes', [])
            },
            'scenario_comparison': {
                'baseline': {
                    'capacity_analysis': base_analysis,
                    'transfer_opportunities': self.optimizer.identify_transfer_opportunities(base_analysis),
                    'capacity_alerts': self.optimizer.generate_capacity_alerts(base_analysis)
                },
                'scenario': {
                    'capacity_analysis': scenario_analysis,
                    'transfer_opportunities': transfer_opportunities,
                    'capacity_alerts': capacity_alerts
                }
            },
            'impact_summary': self.calculate_scenario_impact(base_analysis, scenario_analysis, transfer_opportunities)
        }
        
        return results
    
    def apply_scenario_changes(self, base_analysis, scenario_config):
        """Apply user-defined changes to create scenario"""
        scenario_analysis = {}
        
        for warehouse, data in base_analysis.items():
            scenario_data = self.deep_copy_dict(data)
            
            # Apply warehouse-specific changes from UI
            warehouse_changes = scenario_config.get('warehouse_changes', {}).get(warehouse, {})
            
            if warehouse_changes:
                # Update inventory level
                if 'target_utilization' in warehouse_changes:
                    target_util = warehouse_changes['target_utilization'] / 100
                    new_inventory = scenario_data['warehouse_info']['max_capacity'] * target_util
                    scenario_data['warehouse_info']['current_inventory'] = round(new_inventory)
                    scenario_data['utilization_metrics']['final_utilization'] = warehouse_changes['target_utilization']
                
                # Update trend direction
                if 'trend_direction' in warehouse_changes:
                    scenario_data['trend_analysis']['trend_direction'] = warehouse_changes['trend_direction']
                
                # Update risk assessment based on new utilization
                new_util = scenario_data['utilization_metrics']['final_utilization']
                scenario_data['risk_assessment'] = self.optimizer._assess_capacity_risk(
                    new_util, new_util + 2, 1.0 if warehouse_changes.get('trend_direction') == 'Increasing' else 0
                )
                
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
        
        # Apply network-wide changes
        network_changes = scenario_config.get('network_changes', {})
        if 'large_donation_event' in network_changes:
            donation_event = network_changes['large_donation_event']
            target_warehouse = donation_event['warehouse']
            additional_inventory = donation_event['quantity']
            
            if target_warehouse in scenario_analysis:
                current_inventory = scenario_analysis[target_warehouse]['warehouse_info']['current_inventory']
                new_inventory = current_inventory + additional_inventory
                max_capacity = scenario_analysis[target_warehouse]['warehouse_info']['max_capacity']
                
                scenario_analysis[target_warehouse]['warehouse_info']['current_inventory'] = new_inventory
                scenario_analysis[target_warehouse]['utilization_metrics']['final_utilization'] = (new_inventory / max_capacity) * 100
        
        return scenario_analysis
    
    def deep_copy_dict(self, original):
        """Deep copy dictionary to avoid reference issues"""
        import copy
        return copy.deepcopy(original)
    
    def calculate_scenario_impact(self, base_analysis, scenario_analysis, transfers):
        """Calculate the impact of the scenario vs baseline"""
        
        impact_metrics = {
            'utilization_changes': {},
            'new_alerts_generated': 0,
            'transfer_opportunities_created': len(transfers),
            'total_utilization_improvement': 0,
            'cost_impact': {
                'transfer_costs': sum([t['cost_analysis']['estimated_transfer_cost'] for t in transfers]),
                'storage_savings': sum([t['cost_analysis']['estimated_storage_savings'] for t in transfers]),
                'net_impact': sum([t['cost_analysis']['net_benefit'] for t in transfers])
            }
        }
        
        # Calculate utilization changes
        for warehouse in base_analysis.keys():
            base_util = base_analysis[warehouse]['utilization_metrics']['final_utilization']
            scenario_util = scenario_analysis[warehouse]['utilization_metrics']['final_utilization']
            
            impact_metrics['utilization_changes'][warehouse] = {
                'baseline': base_util,
                'scenario': scenario_util,
                'change': round(scenario_util - base_util, 1)
            }
            
            impact_metrics['total_utilization_improvement'] += abs(scenario_util - base_util)
        
        return impact_metrics

def main():
    """Main function to handle command line scenario execution"""
    simulator = WarehouseScenarioSimulator()
    
    # Parse command line arguments or read from stdin
    if len(sys.argv) > 1 and sys.argv[1] == '--config':
        # Read scenario config from file
        with open(sys.argv[2], 'r') as f:
            scenario_config = json.load(f)
    else:
        # Default demo scenarios
        scenario_config = {
            'name': 'High Demand Crisis Simulation',
            'type': 'crisis_simulation',
            'warehouse_changes': {
                'Atlanta': {
                    'target_utilization': 85,
                    'trend_direction': 'Increasing'
                },
                'Nashville': {
                    'target_utilization': 90,
                    'trend_direction': 'Increasing'
                },
                'Chicago': {
                    'target_utilization': 30,
                    'trend_direction': 'Stable'
                },
                'LA': {
                    'target_utilization': 25,
                    'trend_direction': 'Stable'
                }
            },
            'network_changes': {
                'large_donation_event': {
                    'warehouse': 'Nashville',
                    'quantity': 50000,
                    'description': 'Large corporate donation received'
                }
            }
        }
    
    # Run the scenario
    results = simulator.run_custom_scenario(scenario_config)
    
    # Save results
    output_file = 'warehouse_scenario_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Scenario results saved to: {output_file}")
    
    # Print summary
    impact = results['impact_summary']
    print(f"\n📊 Scenario Impact Summary:")
    print(f"   Transfer Opportunities: {impact['transfer_opportunities_created']}")
    print(f"   Total Utilization Change: {impact['total_utilization_improvement']:.1f}%")
    print(f"   Transfer Costs: ${impact['cost_impact']['transfer_costs']:,.2f}")
    print(f"   Net Impact: ${impact['cost_impact']['net_impact']:,.2f}")
    
    print(f"\n🏭 Warehouse Utilization Changes:")
    for warehouse, change in impact['utilization_changes'].items():
        print(f"   {warehouse}: {change['baseline']:.1f}% → {change['scenario']:.1f}% ({change['change']:+.1f}%)")

if __name__ == "__main__":
    main()