// Initialize API client
const apiClient = new ApiClient();

async function loadForecast() {
    const metric = document.getElementById('metricSelect').value;
    const method = document.getElementById('methodSelect').value;
    const periods = document.getElementById('periodsInput').value;

    document.getElementById('loading').style.display = 'block';
    document.getElementById('loading').textContent = 'Loading forecast...';
    document.getElementById('error').style.display = 'none';
    document.getElementById('chartsGrid').style.display = 'none';
    document.getElementById('forecastTable').style.display = 'none';
    document.getElementById('stats').style.display = 'none';

    try {
        const data = await apiClient.getForecast({
            metric: metric,
            method: method,
            periods: periods
        });

        if (data.success) {
            displayHistoricalChart(data);
            displayForecastChart(data);
            displayStats(data.stats);
            displayForecastTable(data.forecast);

            document.getElementById('loading').style.display = 'none';
            document.getElementById('chartsGrid').style.display = 'grid';
            document.getElementById('forecastTable').style.display = 'block';
        } else {
            throw new Error(data.error || 'API returned unsuccessful response');
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('error').textContent = `Error: ${error.message}`;
        ErrorHandler.handleApiError(error);
    }
}

function displayStats(stats) {
    document.getElementById('totalMonths').textContent = stats.total_months;
    document.getElementById('avgValue').textContent = stats.avg_value.toFixed(2);
    document.getElementById('dateRange').textContent = `${stats.date_range.start} to ${stats.date_range.end}`;
    document.getElementById('stats').style.display = 'grid';
}

function displayForecastTable(forecastData) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    forecastData.forEach(item => {
        const row = tbody.insertRow();
        const dateCell = row.insertCell(0);
        const forecastCell = row.insertCell(1);
        const lowerCell = row.insertCell(2);
        const upperCell = row.insertCell(3);

        // Handle both ds/yhat and date/value formats
        const dateField = item.ds || item.date;
        const valueField = item.yhat !== undefined ? item.yhat : item.value;
        const lowerField = item.yhat_lower !== undefined ? item.yhat_lower : item.lower_bound;
        const upperField = item.yhat_upper !== undefined ? item.yhat_upper : item.upper_bound;

        dateCell.textContent = new Date(dateField).toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
        forecastCell.textContent = valueField.toFixed(2);
        lowerCell.textContent = lowerField ? lowerField.toFixed(2) : 'N/A';
        upperCell.textContent = upperField ? upperField.toFixed(2) : 'N/A';
    });

    document.getElementById('forecastTable').style.display = 'block';
}

// Removed fallback notification - no more mock data

// Load initial forecast on page load - removed auto-load
window.addEventListener('load', () => {
    // User must click "Generate Forecast" button to load data
    console.log('Global Forecasting Dashboard loaded - click Generate Forecast to load data');
});