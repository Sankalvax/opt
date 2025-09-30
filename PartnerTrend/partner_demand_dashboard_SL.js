/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * * UI Suitelet for the Partner Demand Forecast Dashboard.
 * This script serves the main HTML application shell.
 */
define(['N/file', 'N/url'], (file, url) => {

    // TODO: Update these with the internal IDs of your uploaded frontend files
    const FILES = {
        INDEX: 5287,   // Your dashboard's index.html
        CSS: 5286,     // Your dashboard's styles.css
        APP: 5284      // Your dashboard's app.js (for making API calls and building UI)
    };

    // TODO: Update with your MIDDLEWARE script and deployment IDs
    const MIDDLEWARE_SCRIPT = {
        SCRIPT_ID: '592',  // Script ID for partner_demand_middleware_SL.js
        DEPLOY_ID: '1'   // Deployment ID for partner_demand_middleware_SL.js
    };
    
    /**
     * Generates a full URL for a file in the File Cabinet.
     */
    function getFileUrl(fileId) {
        return file.load({ id: fileId }).url;
    }

    /**
     * Injects a script tag with a configuration object before the closing </head> tag.
     */
    function injectConfig(html, config) {
        const snippet = `
    <script>
      // Injects server-side configuration for client-side scripts
      window.NS_CONFIG = ${JSON.stringify(config, null, 2)};
      console.log('✅ NetSuite Dashboard Config Injected:', window.NS_CONFIG);
    </script>`;
        
        const headEndTag = '</head>';
        const i = html.indexOf(headEndTag);
        if (i === -1) return html + snippet; // Fallback if </head> not found
        
        return html.slice(0, i) + snippet + '\n' + html.slice(i);
    }
    
    /**
     * @param {Object} context The Suitelet context
     * @param {ServerRequest} context.request The incoming request
     * @param {ServerResponse} context.response The response to send
     */
    function onRequest(context) {
        const { response } = context;

        // 1. Load the main HTML file from the File Cabinet
        let html = file.load({ id: FILES.INDEX }).getContents();
        
        // 2. Replace placeholders in HTML with actual file URLs
        html = html.replace('styles.css', getFileUrl(FILES.CSS));
        html = html.replace('app.js', getFileUrl(FILES.APP));
        
        // 3. Resolve the URL for the middleware Suitelet
        const middlewareUrl = url.resolveScript({
            scriptId: MIDDLEWARE_SCRIPT.SCRIPT_ID,
            deploymentId: MIDDLEWARE_SCRIPT.DEPLOY_ID,
            returnExternalUrl: false // Internal URL
        });
        
        // 4. Prepare the configuration object to inject
        const config = {
            middlewareUrls: {
                partnerDemand: middlewareUrl
                // You can add more middleware URLs here for future tabs
            },
               apiInfo: {
        description: 'Fetches partner demand forecast data via NetSuite middleware.',
        endpoint: 'https://platform.sankalvax.ai/api/partner-demand' // <--- ERROR: API_URL is not defined in this file
    }
        };

        // 5. Inject the config into the HTML
        html = injectConfig(html, config);
        
        // 6. Serve the final HTML page
        response.setHeader({ name: 'Content-Type', value: 'text/html; charset=utf-8' });
        response.write(html);
    }

    return { onRequest };
});