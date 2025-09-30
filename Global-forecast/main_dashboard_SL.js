/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 */
define(['N/file', 'N/url', 'N/runtime'], (file, url, runtime) => {

  // TODO: replace with your File Cabinet internal IDs
  const FILES = {
    INDEX: 5268,       // index.html
    CSS: 5267,         // styles.css
    APP: 5266,         // app.js
    CHARTS: 5272,      // charts.js
    API: 5271          // api.js
  };

  // TODO: replace with your middleware Suitelet script and deployment IDs
  const MIDDLEWARE_SCRIPT = {
    SCRIPT_ID: '586',  // Your middleware script ID (just the number)
    DEPLOY_ID: '1'     // Your middleware deployment ID (just the number)
  };

  function mediaUrl(id) {
    const appDomain = url.resolveDomain({ hostType: url.HostType.APPLICATION });
    const base = 'https://' + appDomain;
    return base + file.load({ id }).url;
  }

  function rewriteAssetPaths(html, map) {
    // Re-point relative asset references to File Cabinet URLs
    let updatedHtml = html
      .replace(/(href|src)=["']styles\.css["']/g, `$1="${map.css}"`)
      .replace(/(href|src)=["']app\.js["']/g, `$1="${map.app}"`)
      .replace(/(href|src)=["']charts\.js["']/g, `$1="${map.charts}"`)
      .replace(/(href|src)=["']api\.js["']/g, `$1="${map.api}"`);

    // Ensure Plotly CDN is properly referenced
    if (!updatedHtml.includes('cdn.plot.ly')) {
      updatedHtml = updatedHtml.replace(/(src)=["'].*plotly.*\.js["']/g, '$1="https://cdn.plot.ly/plotly-latest.min.js"');
    }

    return updatedHtml;
  }

  function injectBeforeHeadClose(html, snippet) {
    const i = html.indexOf('</head>');
    if (i === -1) return html + '\n' + snippet;
    return html.slice(0, i) + '\n' + snippet + '\n' + html.slice(i);
  }

  function onRequest(context) {
    const { request, response } = context;

    // Load index.html and compute FC URLs for assets
    const htmlRaw = file.load({ id: FILES.INDEX }).getContents();
    const map = {
      css: mediaUrl(FILES.CSS),
      app: mediaUrl(FILES.APP),
      charts: mediaUrl(FILES.CHARTS),
      api: mediaUrl(FILES.API)
    };

    let html = rewriteAssetPaths(htmlRaw, map);

    // Create middleware Suitelet URL
    const middlewareUrl = url.resolveScript({
      scriptId: MIDDLEWARE_SCRIPT.SCRIPT_ID,
      deploymentId: MIDDLEWARE_SCRIPT.DEPLOY_ID,
      returnExternalUrl: false
    });

    // Inject configuration for NetSuite environment
    const config = {
      __MIDDLEWARE_URL__: middlewareUrl,
      __API_INFO__: {
        description: 'Using NetSuite middleware to call platform.sankalvax.ai',
        middlewareScript: MIDDLEWARE_SCRIPT.SCRIPT_ID,
        middlewareDeploy: MIDDLEWARE_SCRIPT.DEPLOY_ID,
        externalApi: 'https://platform.sankalvax.ai/forecast'
      }
    };

    const inject = `
    <script>
      // Configure middleware URL
      Object.assign(window, ${JSON.stringify(config)});
      console.log('🏗️ NetSuite Dashboard Config Injected:', window.__API_INFO__);
      console.log('🏗️ Middleware URL Configured:', window.__MIDDLEWARE_URL__);
      console.log('🏗️ Full window config check:', {
        __MIDDLEWARE_URL__: window.__MIDDLEWARE_URL__,
        __API_INFO__: window.__API_INFO__
      });
    </script>`;

    html = injectBeforeHeadClose(html, inject);

    response.setHeader({ name: 'Content-Type', value: 'text/html; charset=utf-8' });
    response.write(html);
  }

  return { onRequest };
});