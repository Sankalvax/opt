# Soles4Souls Inventory Forecasting API Deployment

## 🚀 Overview
Complete deployment package for the Soles4Souls inventory forecasting and distribution optimization system with 6 core API modules and runtime Prophet forecasting capabilities.

## 📁 Package Structure
```
deployment/
├── api_modules/              # 7 Core API Python modules
│   ├── api_historical_trends.py
│   ├── api_inventory_allocation_view.py    # ⭐ Runtime Prophet forecasting
│   ├── api_partner_demand_forecast.py
│   ├── api_product_forecast.py
│   ├── api_warehouse_capacity_optimization.py
│   ├── api_warehouse_scenario_simulator.py
│   └── warehouse_product_rolling_forecast.py
├── outputs/                  # Pre-generated JSON outputs (14 files)
├── data/                     # Historical datasets (23,210+ records)
├── config/                   # Configuration files
├── app.py                    # Flask REST API server
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔧 Quick Setup

### 1. Install Dependencies
```bash
cd deployment
pip install -r requirements.txt
```

### 2. Start API Server
```bash
python app.py
```

Server starts on: **http://localhost:9002**

## 📡 API Endpoints

### Core Endpoints
- `GET /` - Health check and endpoint list
- `GET /api/historical-trends` - Historical data analysis
- `GET /api/warehouse-forecast?horizon=12` - Warehouse rolling inventory forecast
- `GET /api/partner-demand` - Partner demand forecasting (26 Prophet models)
- `GET /api/product-forecast` - Product-specific forecasting
- `GET /api/warehouse-capacity` - Capacity optimization and transfer recommendations
- `POST /api/warehouse-scenario` - What-if scenario simulation
- `GET /api/inventory-allocation` - **⭐ Runtime Prophet allocation system**
- `GET /api/all-modules` - Execute all modules and return summary

### ⭐ Featured API: Runtime Prophet Inventory Allocation
**Endpoint**: `GET /api/inventory-allocation`

**Features**:
- Trains 5 Prophet models at runtime using 23,210 historical records
- Generates specific allocation recommendations: "Send 38,042 Sneakers from NY to Company C by Oct 4th"
- Detailed size breakdowns and shipping cost analysis
- Dynamic demand calculation vs static estimates

**Response**:
```json
{
  "success": true,
  "data": {
    "allocation_recommendations": {
      "metadata": {...},
      "allocation_recommendations": [20 specific recommendations],
      "priority_summary": {...}
    },
    "runtime_forecasts": {
      "partner_forecasts": {...}
    }
  }
}
```

## 🧪 Postman Testing

### 1. Import Collection
Create Postman collection with these requests:

**Health Check**
- GET `http://localhost:5000/`

**Test Core Modules**
- GET `http://localhost:5000/api/warehouse-forecast`
- GET `http://localhost:5000/api/partner-demand`
- GET `http://localhost:5000/api/inventory-allocation`

**What-If Scenario**
- POST `http://localhost:5000/api/warehouse-scenario`
- Body (JSON):
```json
{
  "name": "High Demand Crisis Test",
  "warehouse_changes": {
    "Nashville": {
      "target_utilization": 90,
      "trend_direction": "Increasing"
    }
  }
}
```

**Run All Modules**
- GET `http://localhost:5000/api/all-modules`

### 2. Expected Performance
- **Individual modules**: 5-30 seconds
- **Runtime Prophet allocation**: ~30 seconds  
- **All modules**: 2-5 minutes

## 🌐 NetSuite Integration

### HTML/JavaScript Integration
```javascript
// NetSuite SuiteScript example
function callInventoryAPI() {
    var url = 'http://your-server:5000/api/inventory-allocation';
    
    var response = https.get({
        url: url,
        headers: {
            'Content-Type': 'application/json'
        }
    });
    
    if (response.code === 200) {
        var data = JSON.parse(response.body);
        displayAllocationRecommendations(data.data.allocation_recommendations);
    }
}
```

### Cross-Origin Setup
API includes CORS headers for browser access:
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Enables NetSuite browser calls
```

## 📊 Business Intelligence Outputs

### Key Metrics Generated
- **Total Monthly Demand**: 915,070 units (Prophet-predicted)
- **Allocation Recommendations**: 20 specific warehouse-to-partner shipments
- **Priority Distribution**: 8 HIGH, 8 MEDIUM, 4 LOW priority shipments
- **Cost Analysis**: Distance-based shipping costs with volume discounts

### Sample Allocation Recommendation
```json
{
  "from_warehouse": "NY",
  "to_partner": "Company C", 
  "partner_region": "West Africa",
  "product_details": {
    "category": "Sneakers",
    "total_quantity": 38042,
    "size_breakdown": [
      {"size": "8", "quantity": 7608, "percentage": 20},
      {"size": "7", "quantity": 5706, "percentage": 15}
    ]
  },
  "timeline": {
    "ship_by_date": "2025-10-04",
    "deliver_by_date": "2025-10-25"
  },
  "logistics": {
    "shipping_cost_estimate": 177846.35,
    "distance_factor": 2.2
  },
  "priority": "HIGH"
}
```

## 🔍 Troubleshooting

### Common Issues
1. **Prophet import errors**: Ensure cmdstan is installed
2. **File not found**: Check data files are in `data/Datasets/`
3. **Memory issues**: Runtime Prophet training requires ~2GB RAM
4. **Port conflicts**: Change port in `app.py` if 5000 is taken

### Debug Mode
```bash
export FLASK_ENV=development
python app.py
```

## 🎯 Next Steps

1. **Deploy to Server**: Upload to cloud server (AWS/GCP/Azure)
2. **Test with Postman**: Verify all endpoints work
3. **NetSuite Integration**: Connect from NetSuite environment
4. **UI Development**: Build dashboard consuming these APIs

---

## 🏆 System Capabilities Summary

**✅ 6 Core API Modules Ready for Production**
- Historical trends analysis
- Warehouse rolling inventory forecasting (20 Prophet models)  
- Partner demand intelligence (26 Prophet models)
- Product-specific forecasting
- Warehouse capacity optimization with transfer recommendations
- What-if scenario simulation
- **⭐ Runtime Prophet inventory allocation (NEW)**

**✅ Key Features**
- Real-time Prophet model training
- 23,210+ historical records processed
- Specific business recommendations
- Cost-benefit transfer analysis
- Regional demand optimization
- Interactive scenario simulation
- NetSuite-ready JSON outputs

**Ready for hackathon demonstration and production deployment!** 🚀