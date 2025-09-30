/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * * Middleware for fetching Warehouse Capacity Optimization data.
 */
define(['N/https', 'N/log'], (https, log) => {

    // Warehouse capacity optimization API endpoint
    const API_URL = 'https://platform.sankalvax.ai/api/warehouse-capacity';

    function onRequest(context) {
        const { request, response } = context;

        response.setHeader({ name: 'Access-Control-Allow-Origin', value: '*' });
        response.setHeader({ name: 'Content-Type', value: 'application/json' });

        if (request.method === 'OPTIONS') {
            response.setHeader({ name: 'Access-Control-Allow-Methods', value: 'GET, OPTIONS' });
            response.setHeader({ name: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' });
            response.write('{}');
            return;
        }

        try {
            log.debug('Starting Warehouse Capacity Optimization API Call', { url: API_URL });
            
            // This endpoint may require authentication like the previous one.
            // If you get a 401 Unauthorized error, you will need to add
            // a Bearer Token here or whitelist NetSuite's IP addresses.
            const apiResponse = https.get({
                url: API_URL
            });

            log.debug('External API Response', { code: apiResponse.code });

            response.code = apiResponse.code;
            response.write(apiResponse.body);

        } catch (e) {
            log.error('Warehouse Capacity Optimization Middleware Exception', { error: e.toString() });
            response.code = 500;
            response.write(JSON.stringify({
                success: false,
                error: 'An internal error occurred in the NetSuite warehouse capacity optimization middleware.',
                details: e.toString()
            }));
        }
    }

    return { onRequest };
});