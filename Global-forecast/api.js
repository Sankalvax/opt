// API Configuration
const API_BASE_URL = (typeof window !== 'undefined' && window.__API_BASE__) || 'https://platform.sankalvax.ai/forecast';

// API Client for direct API calls only
class ApiClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    // Generic fetch wrapper with error handling
    async fetch(endpoint, options = {}) {
        // Check if running in NetSuite environment and use proxy
        if (typeof window !== 'undefined' && window.__PROXY__) {
            const proxyUrl = `${window.__PROXY__}?action=api_call&endpoint=${encodeURIComponent(endpoint)}`;

            try {
                const response = await fetch(proxyUrl, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        ...options.headers
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            } catch (error) {
                console.error(`API Proxy Error (${endpoint}):`, error);
                throw error;
            }
        }

        // Direct API call for non-NetSuite environments
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            console.error(`[ERROR] Unable to connect to the API server. Check CORS headers and ensure the API is reachable over HTTPS with a valid certificate.`);
            throw error;
        }
    }

    // Build query string from parameters
    buildQueryString(params) {
        const searchParams = new URLSearchParams();

        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                if (Array.isArray(value)) {
                    value.forEach(v => searchParams.append(key, v));
                } else {
                    searchParams.append(key, value);
                }
            }
        });

        return searchParams.toString();
    }

    // Main forecast endpoint - calls NetSuite middleware
    async getForecast(params = {}) {
        const { metric = 'Inventory Level', periods = 12, method = 'arima' } = params;

        console.log('🔍 DEBUG: getForecast called with params:', params);
        console.log('🔍 DEBUG: window.__MIDDLEWARE_URL__:', typeof window !== 'undefined' ? window.__MIDDLEWARE_URL__ : 'undefined');
        console.log('🔍 DEBUG: window.__API_INFO__:', typeof window !== 'undefined' ? window.__API_INFO__ : 'undefined');

        // Build query parameters for NetSuite middleware
        const queryParams = new URLSearchParams({
            metric: metric,
            periods: periods.toString(),
            method: method
        });

        // Call NetSuite middleware Suitelet (will be set via window.__MIDDLEWARE_URL__)
        const middlewareUrl = (typeof window !== 'undefined' && window.__MIDDLEWARE_URL__) || '/app/site/hosting/scriptlet.nl?script=146&deploy=1';

        console.log('🔍 DEBUG: Using middleware URL:', middlewareUrl);

        // Check if middleware URL already has query parameters
        const separator = middlewareUrl.includes('?') ? '&' : '?';
        const fullUrl = `${middlewareUrl}${separator}${queryParams.toString()}`;

        console.log('🔍 DEBUG: Final URL constructed:', fullUrl);

        try {
            console.log(`Calling NetSuite middleware: ${fullUrl}`);
            console.log(`Middleware will call: https://platform.sankalvax.ai/forecast/api/* for metric: ${metric}`);

            const response = await fetch(fullUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'same-origin' // Important for NetSuite
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Middleware Response received:', result.success ? 'Success' : 'Failed');

            return result;
        } catch (error) {
            console.error('Middleware API failed:', error.message);
            console.error('Full error details:', error);
            throw error;
        }
    }

    // Get available filters/metrics
    async getMetrics() {
        return await this.fetch('/metrics');
    }

    // Additional API endpoints (compatible with ui/api.js structure)
    async getFilters() {
        return await this.fetch('/filters');
    }

    // Get historical inflow data
    async getInflows(params = {}) {
        const queryString = this.buildQueryString(params);
        const endpoint = `/data/inflows${queryString ? `?${queryString}` : ''}`;
        return await this.fetch(endpoint);
    }

    // Get historical outflow data
    async getOutflows(params = {}) {
        const queryString = this.buildQueryString(params);
        const endpoint = `/data/outflows${queryString ? `?${queryString}` : ''}`;
        return await this.fetch(endpoint);
    }

    // Get NetSuite forecast payload
    async getForecastPayload(params = {}) {
        const queryString = this.buildQueryString(params);
        const endpoint = `/payloads/forecast${queryString ? `?${queryString}` : ''}`;
        return await this.fetch(endpoint);
    }

    // Get NetSuite alert payload
    async getAlertPayload(params = {}) {
        const queryString = this.buildQueryString(params);
        const endpoint = `/payloads/alerts${queryString ? `?${queryString}` : ''}`;
        return await this.fetch(endpoint);
    }

    // Health check
    async healthCheck() {
        try {
            return await this.fetch('/health');
        } catch (error) {
            console.warn('Health check failed:', error);
            return { status: 'unavailable', timestamp: new Date().toISOString() };
        }
    }

    // Test NetSuite middleware connection
    async testMiddleware() {
        console.log('🧪 Testing NetSuite middleware connection...');

        const middlewareUrl = (typeof window !== 'undefined' && window.__MIDDLEWARE_URL__) || '/app/site/hosting/scriptlet.nl?script=146&deploy=1';
        const separator = middlewareUrl.includes('?') ? '&' : '?';
        const testUrl = `${middlewareUrl}${separator}test=true`;

        console.log('🧪 Test URL:', testUrl);

        try {
            const response = await fetch(testUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('🧪 Middleware test result:', result);
            return result;
        } catch (error) {
            console.error('🧪 Middleware test failed:', error);
            throw error;
        }
    }

    // Removed fallback data - UI will show proper error messages instead

}

// Data Management Class
class DataManager {
    constructor() {
        this.api = new ApiClient();
        this.cache = new Map();
        this.subscribers = new Map();
    }

    // Subscribe to data updates
    subscribe(event, callback) {
        if (!this.subscribers.has(event)) {
            this.subscribers.set(event, []);
        }
        this.subscribers.get(event).push(callback);
    }

    // Notify subscribers
    notify(event, data) {
        if (this.subscribers.has(event)) {
            this.subscribers.get(event).forEach(callback => callback(data));
        }
    }

    // Get data with caching
    async getData(key, fetcher, cacheTime = 5 * 60 * 1000) { // 5 minutes default cache
        const now = Date.now();
        const cached = this.cache.get(key);

        if (cached && (now - cached.timestamp) < cacheTime) {
            return cached.data;
        }

        try {
            const data = await fetcher();
            this.cache.set(key, { data, timestamp: now });
            this.notify('dataUpdated', { key, data });
            return data;
        } catch (error) {
            console.error(`Error fetching ${key}:`, error);
            throw error;
        }
    }

    // Clear cache
    clearCache(pattern = null) {
        if (pattern) {
            // Clear cache entries matching pattern
            for (const [key] of this.cache) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
        this.notify('cacheCleared', { pattern });
    }

    // Get forecast data with caching - no fallback data
    async getForecastData(params = {}) {
        const cacheKey = `forecast_${JSON.stringify(params)}`;
        return await this.getData(cacheKey, () => this.api.getForecast(params), 2 * 60 * 1000);
    }

    // Get available filters/metrics
    async getFilters() {
        return await this.getData('filters', () => this.api.getFilters(), 30 * 60 * 1000);
    }

    // Generate NetSuite payloads
    async generatePayloads(params = {}) {
        try {
            const [forecastPayload, alertPayload] = await Promise.all([
                this.api.getForecastPayload(params),
                this.api.getAlertPayload(params)
            ]);

            return { forecastPayload, alertPayload };
        } catch (error) {
            console.error('Error generating payloads:', error);
            throw error;
        }
    }
}

// Utility Functions
class ApiUtils {
    // Format date for API
    static formatDate(date) {
        if (date instanceof Date) {
            return date.toISOString().split('T')[0];
        }
        return date;
    }

    // Parse API date
    static parseDate(dateString) {
        return new Date(dateString);
    }

    // Format number with commas
    static formatNumber(num) {
        if (num === null || num === undefined) return '--';
        return new Intl.NumberFormat().format(Math.round(num));
    }

    // Format large numbers with appropriate units
    static formatLargeNumber(num) {
        if (num === null || num === undefined) return '--';

        const abs = Math.abs(num);
        if (abs >= 1e12) return (num / 1e12).toFixed(1) + 'T';
        if (abs >= 1e9) return (num / 1e9).toFixed(1) + 'B';
        if (abs >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (abs >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return Math.round(num).toString();
    }

    // Download data as CSV
    static downloadCSV(data, filename) {
        if (!data || data.length === 0) {
            console.warn('No data to download');
            return;
        }

        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => {
                const value = row[header];
                // Escape commas and quotes in CSV
                if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                    return `"${value.replace(/"/g, '""')}"`;
                }
                return value;
            }).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);

        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Copy text to clipboard
    static async copyToClipboard(text) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                textArea.remove();
            }
            return true;
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            return false;
        }
    }

    // Debounce function
    static debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Throttle function
    static throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Error Handler
class ErrorHandler {
    static show(message, type = 'error') {
        console.error('API Error:', message);

        // Show user-friendly message
        const toastContainer = document.getElementById('toastContainer');
        if (toastContainer) {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `<span>${message}</span>`;

            toastContainer.appendChild(toast);

            // Auto remove after 5 seconds
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 5000);
        }
    }

    static handleApiError(error) {
        let message = 'An unexpected error occurred';

        if (error.message.includes('fetch')) {
            message = 'Unable to connect to the API server. Please check if the server is running.';
        } else if (error.message.includes('HTTP 404')) {
            message = 'Requested data not found.';
        } else if (error.message.includes('HTTP 500')) {
            message = 'Server error occurred. Please try again later.';
        } else if (error.message.includes('HTTP')) {
            message = `Server error: ${error.message}`;
        }

        this.show(message, 'error');
    }
}

// Export for use in other files
window.ApiClient = ApiClient;
window.DataManager = DataManager;
window.ApiUtils = ApiUtils;
window.ErrorHandler = ErrorHandler;

// Create global test function for debugging
window.testMiddleware = async function() {
    const api = new ApiClient();
    return await api.testMiddleware();
};

// Create global debug function to check configuration
window.debugNetSuiteConfig = function() {
    console.log('🔍 DEBUG: NetSuite Configuration Check:');
    console.log('  - window.__MIDDLEWARE_URL__:', window.__MIDDLEWARE_URL__);
    console.log('  - window.__API_INFO__:', window.__API_INFO__);
    console.log('  - typeof window:', typeof window);
    console.log('  - window keys:', Object.keys(window).filter(k => k.startsWith('__')));
};