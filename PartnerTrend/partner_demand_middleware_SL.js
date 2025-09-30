/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * * Middleware Suitelet for fetching Partner Demand Forecast data.
 * This acts as a proxy to call the external API securely from the server.
 */
define(['N/https', 'N/log'], (https, log) => {

    // The secure URL for your external partner demand forecast API
    const API_URL = 'https://platform.sankalvax.ai/api/partner-demand';

    /**
     * @param {Object} context The Suitelet context
     * @param {ServerRequest} context.request The incoming request
     * @param {ServerResponse} context.response The response to send
     */
    function onRequest(context) {
        const { request, response } = context;

        // Set CORS headers to allow requests from any NetSuite domain
        response.setHeader({ name: 'Access-Control-Allow-Origin', value: '*' });
        response.setHeader({ name: 'Content-Type', value: 'application/json' });

        // Handle pre-flight OPTIONS requests for CORS
        if (request.method === 'OPTIONS') {
            response.setHeader({ name: 'Access-Control-Allow-Methods', value: 'GET, OPTIONS' });
            response.setHeader({ name: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' });
            response.write('{}');
            return;
        }

        try {
            log.debug('Starting Partner Demand API Call', `URL: ${API_URL}`);

            // =================================================================
            // >> CHANGE 1: ADD YOUR BEARER TOKEN HERE <<
            // IMPORTANT: Replace 'YOUR_TOKEN_HERE' with your actual API token.
            // For better security, consider storing this as a Script Parameter.
           
            // =================================================================

            // Make the GET request to the external API
            const apiResponse = https.get({
                url: API_URL,
                headers: {
                    'Accept': 'application/json',
                    
                }
            });

            log.debug('External API Response', {
                code: apiResponse.code,
                bodyLength: apiResponse.body ? apiResponse.body.length : 0
            });

            // Check for a successful response code
            if (apiResponse.code >= 200 && apiResponse.code < 300) {
                // Forward the successful response body to the client
                response.write(apiResponse.body);
            } else {
                // Handle API errors
                log.error('External API Error', {
                    message: 'Non-2xx response received from external API.',
                    code: apiResponse.code,
                    body: apiResponse.body,
                    url: API_URL
                });

                // =================================================================
                // >> CHANGE 2: FIX THE SETSTATUS BUG <<
                response.code = apiResponse.code; // CORRECTED: Use response.code
                // =================================================================

                response.write(JSON.stringify({
                    success: false,
                    error: `API server returned status ${apiResponse.code}`,
                    details: apiResponse.body || 'No response body from server.'
                }));
            }

        } catch (e) {
            log.error('Middleware Suitelet Exception', {
                error: e.toString(),
                message: e.message,
                stack: e.stack
            });

            // Handle internal Suitelet errors
            // =================================================================
            // >> CHANGE 3: FIX THE SETSTATUS BUG IN THE CATCH BLOCK <<
            response.code = 500; // CORRECTED: Use response.code
            // =================================================================
            
            response.write(JSON.stringify({
                success: false,
                error: 'An internal error occurred in the NetSuite middleware.',
                details: e.toString()
            }));
        }
    }

    return { onRequest };
});