// Chart visualization functions

// Check if Plotly is loaded
function ensurePlotlyLoaded() {
    if (typeof Plotly === 'undefined') {
        console.error('Plotly is not loaded. Loading from CDN...');

        // Try to load Plotly from CDN
        const script = document.createElement('script');
        script.src = 'https://cdn.plot.ly/plotly-latest.min.js';
        script.onload = function() {
            console.log('Plotly loaded successfully');
        };
        script.onerror = function() {
            console.error('Failed to load Plotly from CDN, using fallback charts');
            window.PLOTLY_FALLBACK = true;
        };
        document.head.appendChild(script);

        return false;
    }
    return true;
}

function displayHistoricalChart(data) {
    // Check if we should use fallback charts
    if (window.PLOTLY_FALLBACK || !ensurePlotlyLoaded()) {
        if (window.PLOTLY_FALLBACK) {
            renderFallbackChart('historicalChart', data, 'historical');
            return;
        }

        // Show loading message and retry after a delay
        const container = document.getElementById('historicalChart');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 50px; color: #6c757d;">Loading chart library...</div>';
        }

        setTimeout(() => displayHistoricalChart(data), 2000);
        return;
    }
    const historicalDates = data.historical.map(item => item.Date);
    const historicalValues = data.historical.map(item => item.value);

    const traces = [
        {
            x: historicalDates,
            y: historicalValues,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Historical Data',
            line: { color: '#1f77b4', width: 3 },
            marker: { size: 6 }
        }
    ];

    const layout = {
        xaxis: {
            title: 'Date',
            showgrid: true,
            gridcolor: '#e9ecef'
        },
        yaxis: {
            title: data.metric,
            showgrid: true,
            gridcolor: '#e9ecef'
        },
        height: 380,
        margin: { t: 10, b: 40, l: 60, r: 40 },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        showlegend: false
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };

    Plotly.newPlot('historicalChart', traces, layout, config);
}

function displayForecastChart(data) {
    // Check if we should use fallback charts
    if (window.PLOTLY_FALLBACK || !ensurePlotlyLoaded()) {
        if (window.PLOTLY_FALLBACK) {
            renderFallbackChart('forecastChart', data, 'forecast');
            return;
        }

        // Show loading message and retry after a delay
        const container = document.getElementById('forecastChart');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 50px; color: #6c757d;">Loading chart library...</div>';
        }

        setTimeout(() => displayForecastChart(data), 2000);
        return;
    }
    // Handle both API response formats
    const forecastDates = data.forecast.map(item => item.ds || item.date);
    const forecastValues = data.forecast.map(item => item.yhat !== undefined ? item.yhat : item.value);
    const lowerBounds = data.forecast.map(item => item.yhat_lower !== undefined ? item.yhat_lower : item.lower_bound);
    const upperBounds = data.forecast.map(item => item.yhat_upper !== undefined ? item.yhat_upper : item.upper_bound);

    const traces = [
        {
            x: forecastDates,
            y: upperBounds,
            type: 'scatter',
            mode: 'lines',
            name: 'Upper Bound',
            line: { color: 'rgba(255,127,14,0.3)', width: 1 },
            fill: 'tonexty',
            fillcolor: 'rgba(255,127,14,0.15)',
            hoverinfo: 'skip'
        },
        {
            x: forecastDates,
            y: lowerBounds,
            type: 'scatter',
            mode: 'lines',
            name: 'Lower Bound',
            line: { color: 'rgba(255,127,14,0.3)', width: 1 },
            hoverinfo: 'skip'
        },
        {
            x: forecastDates,
            y: forecastValues,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Forecast',
            line: { color: '#ff7f0e', width: 3 },
            marker: { size: 8 }
        }
    ];

    const layout = {
        xaxis: {
            title: 'Date',
            showgrid: true,
            gridcolor: '#e9ecef'
        },
        yaxis: {
            title: data.metric,
            showgrid: true,
            gridcolor: '#e9ecef'
        },
        height: 380,
        margin: { t: 10, b: 40, l: 60, r: 40 },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        legend: {
            x: 0,
            y: 1,
            bgcolor: 'rgba(255,255,255,0.8)'
        }
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };

    Plotly.newPlot('forecastChart', traces, layout, config);
}

// Fallback chart rendering using HTML5 Canvas
function renderFallbackChart(containerId, data, chartType) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Create canvas element
    const canvas = document.createElement('canvas');
    canvas.width = 500;
    canvas.height = 300;
    canvas.style.width = '100%';
    canvas.style.height = '300px';
    canvas.style.border = '1px solid #e9ecef';
    canvas.style.borderRadius = '8px';

    container.innerHTML = '';
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const padding = 50;
    const chartWidth = canvas.width - 2 * padding;
    const chartHeight = canvas.height - 2 * padding;

    // Clear canvas
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (chartType === 'historical') {
        drawHistoricalFallback(ctx, data, padding, chartWidth, chartHeight);
    } else if (chartType === 'forecast') {
        drawForecastFallback(ctx, data, padding, chartWidth, chartHeight);
    }
}

function drawHistoricalFallback(ctx, data, padding, chartWidth, chartHeight) {
    if (!data.historical || data.historical.length === 0) {
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No historical data available', chartWidth / 2 + padding, chartHeight / 2 + padding);
        return;
    }

    const values = data.historical.map(item => item.value);
    const maxValue = Math.max(...values);
    const minValue = Math.min(...values);
    const range = maxValue - minValue;

    // Draw axes
    ctx.strokeStyle = '#666';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, padding + chartHeight);
    ctx.lineTo(padding + chartWidth, padding + chartHeight);
    ctx.stroke();

    // Draw data points and line
    ctx.strokeStyle = '#1f77b4';
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let i = 0; i < values.length; i++) {
        const x = padding + (i / (values.length - 1)) * chartWidth;
        const y = padding + chartHeight - ((values[i] - minValue) / range) * chartHeight;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }

        // Draw point
        ctx.fillStyle = '#1f77b4';
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
    }
    ctx.stroke();

    // Add title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Historical Data', chartWidth / 2 + padding, 20);
}

function drawForecastFallback(ctx, data, padding, chartWidth, chartHeight) {
    if (!data.forecast || data.forecast.length === 0) {
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No forecast data available', chartWidth / 2 + padding, chartHeight / 2 + padding);
        return;
    }

    // Handle both API response formats
    const values = data.forecast.map(item => item.yhat !== undefined ? item.yhat : item.value);
    const upperBounds = data.forecast.map(item => item.yhat_upper !== undefined ? item.yhat_upper : item.upper_bound);
    const lowerBounds = data.forecast.map(item => item.yhat_lower !== undefined ? item.yhat_lower : item.lower_bound);

    const allValues = [...values, ...upperBounds, ...lowerBounds];
    const maxValue = Math.max(...allValues);
    const minValue = Math.min(...allValues);
    const range = maxValue - minValue;

    // Draw axes
    ctx.strokeStyle = '#666';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, padding + chartHeight);
    ctx.lineTo(padding + chartWidth, padding + chartHeight);
    ctx.stroke();

    // Draw confidence interval
    ctx.fillStyle = 'rgba(255, 127, 14, 0.15)';
    ctx.beginPath();
    for (let i = 0; i < values.length; i++) {
        const x = padding + (i / (values.length - 1)) * chartWidth;
        const yUpper = padding + chartHeight - ((upperBounds[i] - minValue) / range) * chartHeight;
        if (i === 0) ctx.moveTo(x, yUpper);
        else ctx.lineTo(x, yUpper);
    }
    for (let i = values.length - 1; i >= 0; i--) {
        const x = padding + (i / (values.length - 1)) * chartWidth;
        const yLower = padding + chartHeight - ((lowerBounds[i] - minValue) / range) * chartHeight;
        ctx.lineTo(x, yLower);
    }
    ctx.closePath();
    ctx.fill();

    // Draw forecast line
    ctx.strokeStyle = '#ff7f0e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < values.length; i++) {
        const x = padding + (i / (values.length - 1)) * chartWidth;
        const y = padding + chartHeight - ((values[i] - minValue) / range) * chartHeight;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }

        // Draw point
        ctx.fillStyle = '#ff7f0e';
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
    }
    ctx.stroke();

    // Add title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Forecast Data', chartWidth / 2 + padding, 20);
}