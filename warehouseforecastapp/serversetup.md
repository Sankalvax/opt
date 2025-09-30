# Hackathon Forecasting Applications - Server Setup Guide

## Project Overview

This server hosts two forecasting applications for the hackathon:

1. **Global Forecast API** (current): Creates forecasts of inflow, outflow, and inventory for all available data
2. **Warehouse-wise Forecast API** (planned): Detailed warehouse-specific forecasts with advanced features

## Current Server Architecture

### Application Status
- **Global Forecast API**: ✅ Running on port 9001
- **Process ID**: 2330282
- **Direct Access**: `http://localhost:9001`
- **SSL Access**: `https://164.52.200.238:8085`
- **Active Traffic**: Receiving requests from NetSuite (150.230.98.160)

### Port Configuration
- **Port 9001**: Global FastAPI forecasting server (direct HTTP access)
- **Port 8085**: Nginx SSL reverse proxy → forwards to applications
- **Port 8001**: Legacy Docker s4s-forecast API (unhealthy, can be retired)
- **Port 5001**: Gunicorn Flask app (different service)
- **Port 80/443**: Main nginx server handling multiple domains

## Nginx Configuration Strategy

### Current Setup: `/etc/nginx/sites-enabled/new-forecast-api`

The existing nginx configuration on port 8085 is perfect for both applications. It provides:
- ✅ SSL termination with Let's Encrypt certificates
- ✅ CORS headers for NetSuite integration
- ✅ Security headers
- ✅ API documentation routes (`/docs`, `/openapi.json`)
- ✅ Proper timeout settings

### Recommended Approach: Path-based Routing

**Option 1: Path-based routing on same port (RECOMMENDED)**

Update the nginx config to route different paths to different applications:

```nginx
# Global Forecast API (current application)
location /api/v1/global/ {
    proxy_pass http://127.0.0.1:9001/api/;
    # ... existing proxy settings
}

# Warehouse-wise Forecast API (new application)
location /api/v1/warehouse/ {
    proxy_pass http://127.0.0.1:9002/api/;
    # ... existing proxy settings
}

# Backward compatibility - routes to global API
location /api/ {
    proxy_pass http://127.0.0.1:9001/api/;
    # ... existing proxy settings
}

# Default root routes to global API for now
location / {
    proxy_pass http://127.0.0.1:9001;
    # ... existing proxy settings
}
```

**Benefits:**
- ✅ Same SSL certificate and port 8085
- ✅ NetSuite can continue using existing endpoint
- ✅ Easy to add new application without infrastructure changes
- ✅ Clear API versioning and separation

### Alternative Options

**Option 2: Header-based routing**
Route based on custom headers (more complex, not recommended for this use case)

**Option 3: Subdomain routing**
Use subdomains like `global.forecast.domain.com` vs `warehouse.forecast.domain.com` (requires additional SSL certs)

## Implementation Plan

### Step 1: Prepare Current Application
```bash
# Update current API to use /api/v1/global/ prefix (optional)
# Or keep existing /api/ endpoints for backward compatibility
```

### Step 2: Develop New Warehouse Application
```bash
# Create new FastAPI application on port 9002
cd /opt/new-forecast
python3 warehouse_api.py  # runs on port 9002
```

### Step 3: Update Nginx Configuration
```bash
# Edit the existing config
sudo nano /etc/nginx/sites-enabled/new-forecast-api

# Test configuration
sudo nginx -t

# Reload nginx (zero downtime)
sudo systemctl reload nginx
```

### Step 4: NetSuite Integration
- **Global API**: Continue using `https://164.52.200.238:8085/api/inventory-level`
- **Warehouse API**: New endpoints like `https://164.52.200.238:8085/api/v1/warehouse/inventory-level?warehouse_id=WH001`

## Deployment Commands

### Start Global Forecast API (Current)
```bash
cd /opt/new-forecast
source venv/bin/activate
python3 api_main.py  # Port 9001
```

### Start Warehouse Forecast API (Future)
```bash
cd /opt/new-forecast
source venv/bin/activate
python3 warehouse_api.py  # Port 9002
```

### Check Services
```bash
# Check running APIs
netstat -tlnp | grep -E ':(9001|9002)'

# Check nginx status
systemctl status nginx

# Test endpoints
curl -k https://localhost:8085/api/inventory-level
curl -k https://localhost:8085/api/v1/warehouse/inventory-level?warehouse_id=WH001
```

## Nginx Configuration Template

### Updated `/etc/nginx/sites-enabled/new-forecast-api`
```nginx
server {
    listen 8085 ssl;
    server_name _;

    # SSL Configuration (existing)
    ssl_certificate /etc/letsencrypt/live/platform.sankalvax.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/platform.sankalvax.ai/privkey.pem;

    # SSL Security settings (existing)
    ssl_protocols TLSv1.2 TLSv1.3;
    # ... other SSL settings

    # Global Forecast API (v1)
    location /api/v1/global/ {
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;

        proxy_pass http://127.0.0.1:9001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Warehouse Forecast API (v1)
    location /api/v1/warehouse/ {
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;

        proxy_pass http://127.0.0.1:9002/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Backward compatibility - existing API routes
    location /api/ {
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;

        proxy_pass http://127.0.0.1:9001/api/;
        # ... existing proxy settings
    }

    # Documentation routes (global API for now)
    location /docs {
        proxy_pass http://127.0.0.1:9001/docs;
        # ... existing proxy settings
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:9001/openapi.json;
        # ... existing proxy settings
    }

    # Default root (global API)
    location / {
        proxy_pass http://127.0.0.1:9001;
        # ... existing proxy settings
    }

    # CORS preflight handling (existing)
    if ($request_method = 'OPTIONS') {
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
        add_header Access-Control-Max-Age 86400 always;
        add_header Content-Length 0;
        return 204;
    }

    # Security headers (existing)
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

## Benefits of This Approach

1. **Zero Downtime**: Can deploy new application without affecting current one
2. **SSL Reuse**: Same certificate and port for both applications
3. **NetSuite Compatible**: Existing integrations continue to work
4. **Scalable**: Easy to add more applications or load balance
5. **Clear Separation**: Each application has its own namespace
6. **Development Friendly**: Can develop/test new app while old one runs

## Migration Strategy

1. **Phase 1**: Deploy warehouse API on port 9002 (parallel to existing)
2. **Phase 2**: Update nginx config for path routing
3. **Phase 3**: Update NetSuite to use new warehouse endpoints when ready
4. **Phase 4**: Keep global API running for backward compatibility

This approach ensures maximum flexibility while reusing the existing SSL infrastructure that NetSuite depends on.
