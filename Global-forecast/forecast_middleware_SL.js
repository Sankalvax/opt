/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 */
define(['N/https', 'N/log'], (https, log) => {

    const API_BASE_URL = 'https://platform.sankalvax.ai/forecast';

    // Map UI metric names to API endpoints
    const METRIC_ENDPOINTS = {
        'Inventory Level': '/api/inventory-level',
        'Inflow Quantity': '/api/inflow-quantity',
        'Outflow Quantity': '/api/outflow-quantity',
        'Inflow GIK Value': '/api/inflow-gik-value',
        'Outflow GIK Value': '/api/outflow-gik-value'
    };

    /**
     * Transform API response to UI-compatible format
     */
    function transformApiResponse(apiData) {
        
        try {
            const data = typeof apiData === 'string' ? JSON.parse(apiData) : apiData;

            if (!data.success) {
                throw new Error(data.error || 'API returned unsuccessful response');
            }

            // Transform historical data format (Date -> Date, value -> value - no change needed)
            const historical = data.historical.map(item => ({
                Date: item.date || item.Date,
                value: item.value
            }));

            // Transform forecast data format (date/value -> ds/yhat for UI compatibility)
            const forecast = data.forecast.map(item => ({
                ds: item.date || item.ds,
                yhat: item.value !== undefined ? item.value : item.yhat,
                yhat_lower: item.lower_bound !== undefined ? item.lower_bound : item.yhat_lower,
                yhat_upper: item.upper_bound !== undefined ? item.upper_bound : item.yhat_upper
            }));

            return {
                success: true,
                metric: data.metric,
                historical: historical,
                forecast: forecast,
                stats: data.stats,
                fallback: false
            };

        } catch (e) {
            log.error('Error transforming API response', {
                error: e.toString(),
                rawData: apiData
            });

            return {
                success: false,
                error: 'Failed to transform API response: ' + e.toString(),
                fallback: false
            };
        }
    }

    /**
     * Make API call to external server
     */
    function callExternalApi(endpoint, queryParams) {
        const fullUrl = API_BASE_URL + endpoint + '?' + queryParams;

        log.debug('Making API call', {
            url: fullUrl,
            endpoint: endpoint,
            params: queryParams
        });

        try {
            const response = https.get({
                url: fullUrl,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            log.debug('API Response', {
                code: response.code,
                headers: response.headers,
                bodyLength: response.body ? response.body.length : 0,
                bodyPreview: response.body ? response.body.substring(0, 200) + '...' : 'No body'
            });

            if (response.code >= 200 && response.code < 300) {
                return {
                    success: true,
                    data: response.body
                };
            } else {
                log.error('API Error Response', {
                    code: response.code,
                    body: response.body,
                    url: fullUrl
                });

                return {
                    success: false,
                    error: `API server returned ${response.code}`,
                    details: response.body || 'No response body'
                };
            }

        } catch (e) {
            log.error('API Call Exception', {
                error: e.toString(),
                message: e.message,
                stack: e.stack,
                url: fullUrl
            });

            return {
                success: false,
                error: 'Failed to connect to API server',
                details: e.toString()
            };
        }
    }

    function onRequest(context) {
        const { request, response } = context;

        // Set CORS headers for all responses
        response.setHeader({ name: 'Access-Control-Allow-Origin', value: '*' });
        response.setHeader({ name: 'Access-Control-Allow-Methods', value: 'GET, POST, OPTIONS' });
        response.setHeader({ name: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' });
        response.setHeader({ name: 'Content-Type', value: 'application/json' });

        // Log all incoming requests for debugging
        log.debug('Middleware Request', {
            method: request.method,
            parameters: request.parameters,
            url: request.url,
            headers: request.headers
        });

        // Handle OPTIONS preflight requests
        if (request.method === 'OPTIONS') {
            response.write('{}');
            return;
        }

        try {
            // Get parameters from request
            const metric = request.parameters.metric || 'Inventory Level';
            const periods = request.parameters.periods || '12';
            const method = request.parameters.method || 'arima';

            // Add a test endpoint for debugging
            if (request.parameters.test === 'true') {
                response.write(JSON.stringify({
                    success: true,
                    message: 'NetSuite Middleware is working!',
                    parameters: {
                        metric: metric,
                        periods: periods,
                        method: method
                    },
                    timestamp: new Date().toISOString(),
                    script: 'forecast_middleware_SL.js'
                }));
                return;
            }

            log.debug('Processing forecast request', {
                metric: metric,
                periods: periods,
                method: method
            });

            // Validate metric
            const endpoint = METRIC_ENDPOINTS[metric];
            if (!endpoint) {
                response.setStatus(400);
                response.write(JSON.stringify({
                    success: false,
                    error: `Unknown metric: ${metric}`,
                    availableMetrics: Object.keys(METRIC_ENDPOINTS)
                }));
                return;
            }

            // Build query parameters
            const queryParams = `periods=${encodeURIComponent(periods)}&method=${encodeURIComponent(method)}`;

            // Make API call
            const apiResult = callExternalApi(endpoint, queryParams);

            if (apiResult.success) {
                // Transform response for UI compatibility
                const transformedData = transformApiResponse(apiResult.data);
                response.write(JSON.stringify(transformedData));
            } else {
                // Return API error
                response.setStatus(500);
                response.write(JSON.stringify({
                    success: false,
                    error: apiResult.error,
                    details: apiResult.details,
                    metric: metric,
                    endpoint: endpoint,
                    timestamp: new Date().toISOString()
                }));
            }

        } catch (e) {
            log.error('Suitelet Exception', {
                error: e.toString(),
                message: e.message,
                stack: e.stack,
                parameters: request.parameters
            });

            response.setStatus(500);
            response.write(JSON.stringify({
                success: false,
                error: 'Internal Suitelet error',
                details: e.toString(),
                timestamp: new Date().toISOString()
            }));
        }
    }

    return { onRequest };
});