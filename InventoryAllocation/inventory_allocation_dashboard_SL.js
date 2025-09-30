/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * * UI Suitelet for the Inventory Allocation View Dashboard.
 */
define(['N/file', 'N/url'], (file, url) => {

    // TODO: Update with the internal IDs of your NEW frontend files
    const FILES = {
        INDEX: 5278,   // inventory_allocation_index.html
        CSS: 5281,     // inventory_allocation_styles.css
        APP: 5282      // inventory_allocation_app.js
    };

    // TODO: Update with your NEW MIDDLEWARE script and deployment IDs
    const MIDDLEWARE_SCRIPT = {
        SCRIPT_ID: '590',
        DEPLOY_ID: '1'
    };
    
    function getFileUrl(fileId) {
        return file.load({ id: fileId }).url;
    }

    function injectConfig(html, config) {
        const snippet = `
    <script>
      window.NS_CONFIG = ${JSON.stringify(config, null, 2)};
      console.log('✅ Inventory Allocation View Dashboard Config Injected:', window.NS_CONFIG);
    </script>`;
        
        const i = html.indexOf('</head>');
        return html.slice(0, i) + snippet + '\n' + html.slice(i);
    }
    
    function onRequest(context) {
        const { response } = context;

        let html = file.load({ id: FILES.INDEX }).getContents();
        
        html = html.replace('inventory_allocation_styles.css', getFileUrl(FILES.CSS));
        html = html.replace('inventory_allocation_app.js', getFileUrl(FILES.APP));
        
        const middlewareUrl = url.resolveScript({
            scriptId: MIDDLEWARE_SCRIPT.SCRIPT_ID,
            deploymentId: MIDDLEWARE_SCRIPT.DEPLOY_ID,
            returnExternalUrl: false
        });
        
        const config = {
            middlewareUrl: middlewareUrl
        };

        html = injectConfig(html, config);
        
        response.setHeader({ name: 'Content-Type', value: 'text/html; charset=utf-8' });
        response.write(html);
    }

    return { onRequest };
});