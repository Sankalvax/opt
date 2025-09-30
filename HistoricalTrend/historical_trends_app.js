// Chart.js instances
let overallActivityChart, inventoryByWarehouseChart;

document.addEventListener('DOMContentLoaded', () => {
    fetchHistoricalData();
});

async function fetchHistoricalData() {
    const loader = document.getElementById('loader');
    const dashboardContent = document.getElementById('dashboard-content');
    
    if (!window.NS_CONFIG || !window.NS_CONFIG.middlewareUrl) {
        loader.innerHTML = '<p style="color: red;">Error: Could not find middleware URL.</p>';
        return;
    }

    try {
        const response = await fetch(window.NS_CONFIG.middlewareUrl);
        if (!response.ok) throw new Error(`API request failed with status: ${response.status}`);
        
        const apiData = await response.json();
        if (!apiData.success) throw new Error(apiData.message || 'API returned an error.');

        renderDashboard(apiData.data);

        loader.classList.add('hidden');
        dashboardContent.classList.remove('hidden');

    } catch (error) {
        console.error('Failed to fetch or render data:', error);
        loader.innerHTML = `<p style="color: red;">Error loading dashboard: ${error.message}</p>`;
    }
}

function renderDashboard(data) {
    document.getElementById('last-updated').textContent = `Data Generated: ${new Date(data.metadata.generated_at).toLocaleString()}`;
    renderSummaryStats(data.summary_stats);
    renderOverallChart(data.chart_data);
    renderWarehouseChart(data.chart_data.inventory_by_warehouse);
    document.getElementById('metadata-footer').textContent = `Data Source: ${data.metadata.data_source}`;
}

/**
 * Renders the four main summary stat cards with enhanced styling.
 */
function renderSummaryStats(stats) {
    const container = document.getElementById('kpi-cards');
    container.innerHTML = `
        <div class="kpi-card border-inflows">
            <div class="kpi-title">Inflows</div>
            <div class="kpi-main-value">${stats.inflows.total.toLocaleString()}</div>
            <div class="kpi-subtext">Total Donations Received</div>
            <hr>
            <div class="kpi-stat">
                <span class="label">Average / Month:</span>
                <span class="value">${Math.round(stats.inflows.average_per_period).toLocaleString()}</span>
            </div>
            <div class="kpi-stat">
                <span class="label">Peak Month:</span>
                <span class="value">${stats.inflows.peak_value.toLocaleString()} (${stats.inflows.peak_period})</span>
            </div>
        </div>

        <div class="kpi-card border-outflows">
            <div class="kpi-title">Outflows</div>
            <div class="kpi-main-value">${stats.outflows.total.toLocaleString()}</div>
            <div class="kpi-subtext">Total Items Distributed</div>
            <hr>
            <div class="kpi-stat">
                <span class="label">Average / Month:</span>
                <span class="value">${Math.round(stats.outflows.average_per_period).toLocaleString()}</span>
            </div>
            <div class="kpi-stat">
                <span class="label">Peak Month:</span>
                <span class="value">${stats.outflows.peak_value.toLocaleString()} (${stats.outflows.peak_period})</span>
            </div>
        </div>

        <div class="kpi-card border-inventory">
            <div class="kpi-title">Inventory Level</div>
            <div class="kpi-main-value">${Math.round(stats.inventory.current_level).toLocaleString()}</div>
            <div class="kpi-subtext">Current On-Hand</div>
            <hr>
            <div class="kpi-stat">
                <span class="label">Average Level:</span>
                <span class="value">${Math.round(stats.inventory.average_level).toLocaleString()}</span>
            </div>
            <div class="kpi-stat">
                <span class="label">Peak Level:</span>
                <span class="value">${Math.round(stats.inventory.peak_level).toLocaleString()}</span>
            </div>
        </div>

        <div class="kpi-card border-netflow">
            <div class="kpi-title">Net Flow</div>
            <div class="kpi-main-value">${Math.round(stats.net_flow.average).toLocaleString()}</div>
            <div class="kpi-subtext">Average Monthly Net</div>
            <hr>
            <div class="kpi-stat">
                <span class="label">Positive Months:</span>
                <span class="value">${stats.net_flow.positive_periods}</span>
            </div>
            <div class="kpi-stat">
                <span class="label">Negative Months:</span>
                <span class="value">${stats.net_flow.negative_periods}</span>
            </div>
        </div>
    `;
}
function renderOverallChart(chartData) {
    const ctx = document.getElementById('overallActivityChart').getContext('2d');
    if (overallActivityChart) overallActivityChart.destroy();

    overallActivityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.inflows.dates,
            datasets: [
                { type: 'line', label: chartData.inflows.label, data: chartData.inflows.values, borderColor: chartData.inflows.color, tension: 0.1, yAxisID: 'y' },
                { type: 'line', label: chartData.outflows.label, data: chartData.outflows.values, borderColor: chartData.outflows.color, tension: 0.1, yAxisID: 'y' },
                { type: 'line', label: chartData.inventory.label, data: chartData.inventory.values, borderColor: chartData.inventory.color, tension: 0.1, yAxisID: 'y' },
                { type: 'bar', label: chartData.net_flow.label, data: chartData.net_flow.values, backgroundColor: chartData.net_flow.color, yAxisID: 'y1' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { position: 'left' }, y1: { position: 'right', grid: { drawOnChartArea: false } } } }
    });
}

function renderWarehouseChart(warehouseData) {
    const ctx = document.getElementById('inventoryByWarehouseChart').getContext('2d');
    if (inventoryByWarehouseChart) inventoryByWarehouseChart.destroy();

    const datasets = Object.values(warehouseData).map(warehouse => ({
        label: warehouse.label,
        data: warehouse.values,
        borderColor: warehouse.color,
        tension: 0.1,
        fill: false
    }));

    inventoryByWarehouseChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: warehouseData.Atlanta.dates, // Use any warehouse for dates, they are all the same
            datasets: datasets
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}