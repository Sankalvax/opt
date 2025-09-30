from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
import json
import subprocess
from datetime import datetime

# Add the api_modules directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'api_modules'))

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'endpoints': [
            '/api/historical-trends',
            '/api/warehouse-forecast',
            '/api/partner-demand',
            '/api/product-forecast', 
            '/api/warehouse-capacity',
            '/api/warehouse-scenario',
            '/api/inventory-allocation'
        ]
    })

@app.route('/api/historical-trends', methods=['GET', 'POST'])
def historical_trends():
    """Historical trends analysis API"""
    try:
        # Import and run the historical trends module
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'api_historical_trends.py'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        if result.returncode == 0:
            # Load the generated output
            with open('outputs/sample_historical_trends_output.json', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Historical trends analysis completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Historical trends analysis failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running historical trends analysis'
        }), 500

@app.route('/api/warehouse-forecast', methods=['GET', 'POST'])
def warehouse_forecast():
    """Warehouse rolling inventory forecast API"""
    try:
        horizon = request.args.get('horizon', '12')  # Default 12 months
        
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'warehouse_product_rolling_forecast.py'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        if result.returncode == 0:
            # Load the appropriate forecast file
            filename = f'warehouse_product_rolling_forecast_{horizon}m.json'
            with open(f'outputs/{filename}', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data,
                'horizon_months': horizon,
                'message': f'Warehouse forecast ({horizon} months) completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Warehouse forecast failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running warehouse forecast'
        }), 500

@app.route('/api/partner-demand', methods=['GET', 'POST'])
def partner_demand():
    """Partner demand forecast API"""
    try:
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'api_partner_demand_forecast.py'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        if result.returncode == 0:
            with open('outputs/partner_demand_forecast_12m.json', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Partner demand forecast completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Partner demand forecast failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running partner demand forecast'
        }), 500

@app.route('/api/product-forecast', methods=['GET', 'POST'])
def product_forecast():
    """Product-specific forecast API"""
    try:
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'api_product_forecast.py'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        if result.returncode == 0:
            with open('outputs/product_forecast_12m.json', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Product forecast completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Product forecast failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running product forecast'
        }), 500

@app.route('/api/warehouse-capacity', methods=['GET', 'POST'])
def warehouse_capacity():
    """Warehouse capacity optimization API"""
    try:
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'api_warehouse_capacity_optimization.py'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        if result.returncode == 0:
            with open('outputs/warehouse_capacity_optimization.json', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Warehouse capacity analysis completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Warehouse capacity analysis failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running warehouse capacity analysis'
        }), 500

@app.route('/api/warehouse-scenario', methods=['POST'])
def warehouse_scenario():
    """Warehouse what-if scenario simulation API"""
    try:
        # Get scenario configuration from request body
        scenario_config = request.get_json()
        
        if not scenario_config:
            return jsonify({
                'success': False,
                'error': 'No scenario configuration provided',
                'message': 'Please provide scenario parameters in request body'
            }), 400
        
        # Save scenario config to temp file
        with open('api_modules/temp_scenario_config.json', 'w') as f:
            json.dump(scenario_config, f, indent=2)
        
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'api_warehouse_scenario_simulator.py', 
                               '--config', 'temp_scenario_config.json'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        # Clean up temp file
        os.remove('api_modules/temp_scenario_config.json')
        
        if result.returncode == 0:
            with open('outputs/warehouse_scenario_results.json', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data,
                'scenario_config': scenario_config,
                'message': 'Warehouse scenario simulation completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Warehouse scenario simulation failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running warehouse scenario simulation'
        }), 500

@app.route('/api/inventory-allocation', methods=['GET', 'POST'])
def inventory_allocation():
    """Inventory allocation recommendations with runtime Prophet forecasting API"""
    try:
        os.chdir('api_modules')
        result = subprocess.run([sys.executable, 'api_inventory_allocation_view.py'], 
                              capture_output=True, text=True, cwd='.')
        os.chdir('..')
        
        if result.returncode == 0:
            # Load both the allocation recommendations and runtime forecasts
            with open('outputs/inventory_allocation_recommendations.json', 'r') as f:
                allocation_data = json.load(f)
            
            runtime_forecasts = None
            try:
                with open('outputs/runtime_partner_forecasts.json', 'r') as f:
                    runtime_forecasts = json.load(f)
            except FileNotFoundError:
                pass  # Runtime forecasts may not be generated if fallback is used
            
            return jsonify({
                'success': True,
                'data': {
                    'allocation_recommendations': allocation_data,
                    'runtime_forecasts': runtime_forecasts
                },
                'message': 'Inventory allocation with runtime Prophet forecasting completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'message': 'Inventory allocation failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running inventory allocation'
        }), 500

@app.route('/api/all-modules', methods=['GET'])
def run_all_modules():
    """Run all API modules and return summary"""
    try:
        results = {}
        modules = [
            ('historical_trends', 'api_historical_trends.py'),
            ('warehouse_forecast', 'warehouse_product_rolling_forecast.py'),
            ('partner_demand', 'api_partner_demand_forecast.py'),
            ('product_forecast', 'api_product_forecast.py'),
            ('warehouse_capacity', 'api_warehouse_capacity_optimization.py'),
            ('inventory_allocation', 'api_inventory_allocation_view.py')
        ]
        
        os.chdir('api_modules')
        
        for module_name, script_name in modules:
            try:
                result = subprocess.run([sys.executable, script_name], 
                                      capture_output=True, text=True, cwd='.', timeout=300)
                results[module_name] = {
                    'success': result.returncode == 0,
                    'output': result.stdout[-500:] if result.stdout else '',  # Last 500 chars
                    'error': result.stderr[-500:] if result.stderr else ''    # Last 500 chars
                }
            except subprocess.TimeoutExpired:
                results[module_name] = {
                    'success': False,
                    'error': 'Module execution timed out (>300s)',
                    'output': ''
                }
            except Exception as e:
                results[module_name] = {
                    'success': False,
                    'error': str(e),
                    'output': ''
                }
        
        os.chdir('..')
        
        successful_modules = sum(1 for r in results.values() if r['success'])
        total_modules = len(modules)
        
        return jsonify({
            'success': True,
            'summary': {
                'successful_modules': successful_modules,
                'total_modules': total_modules,
                'success_rate': f"{(successful_modules/total_modules)*100:.1f}%"
            },
            'module_results': results,
            'message': f'Executed all {total_modules} modules - {successful_modules} successful'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running all modules'
        }), 500

if __name__ == '__main__':
    print("🚀 Soles4Souls Inventory Forecasting API Server")
    print("=" * 50)
    print("Available endpoints:")
    print("  GET  /                     - Health check")
    print("  GET  /api/historical-trends - Historical data analysis")
    print("  GET  /api/warehouse-forecast - Warehouse rolling forecast")
    print("  GET  /api/partner-demand    - Partner demand forecasting")
    print("  GET  /api/product-forecast  - Product-specific forecasts")
    print("  GET  /api/warehouse-capacity - Capacity optimization")
    print("  POST /api/warehouse-scenario - What-if scenario simulation")
    print("  GET  /api/inventory-allocation - Runtime Prophet allocation")
    print("  GET  /api/all-modules       - Run all modules")
    print("=" * 50)
    print("Starting server on http://localhost:9002")
    print("Ready for Postman testing and NetSuite integration!")

    app.run(host='0.0.0.0', port=9002, debug=True)