let forecastData; // Holds all data from the API
let mainChart; // Holds the Chart.js instance

document.addEventListener('DOMContentLoaded', () => {
    fetchWarehouseData();
});

async function fetchWarehouseData() {
    const loader = document.getElementById('loader');
    const dashboardContent = document.getElementById('dashboard-content');
    
    if (!window.NS_CONFIG || !window.NS_CONFIG.middlewareUrl) {
        loader.innerHTML = '<p style="color: red;">Error: Middleware URL not found.</p>';
        return;
    }

    try {
        const response = await fetch(window.NS_CONFIG.middlewareUrl);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        
        const apiData = await response.json();
        if (!apiData.success) throw new Error(apiData.message);

        forecastData = apiData.data; // Store data globally
        renderDashboard();

        loader.classList.add('hidden');
        dashboardContent.classList.remove('hidden');
    } catch (error) {
        console.error('Fetch/Render Error:', error);
        loader.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}

function renderDashboard() {
    document.getElementById('last-updated').textContent = `Forecast Generated: ${new Date(forecastData.metadata.generated_at).toLocaleString()}`;
    renderNetworkSummary(forecastData.network_summary);
    renderAlerts(forecastData.alerts);
    setupWarehouseSelector(forecastData.warehouses);
}

function renderNetworkSummary(summary) {
    const container = document.getElementById('network-summary-kpis');
    container.innerHTML = `
        <div class="kpi-card"><div class="value">${summary.network_projected_inflow.toLocaleString()}</div><div class="label">Projected Inflow</div></div>
        <div class="kpi-card"><div class="value">${summary.network_projected_outflow.toLocaleString()}</div><div class="label">Projected Outflow</div></div>
        <div class="kpi-card"><div class="value">${summary.network_net_position.toLocaleString()}</div><div class="label">Net Position</div></div>
        <div class="kpi-card"><div class="value">${summary.final_network_inventory.toLocaleString()}</div><div class="label">Final Inventory</div></div>
        <div class="kpi-card"><div class="value">${summary.warehouses_at_risk}</div><div class="label">Warehouses at Risk</div></div>
        <div class="kpi-card"><div class="value">${summary.total_alerts}</div><div class="label">Total Alerts</div></div>
    `;
}

function renderAlerts(alerts) {
    const container = document.getElementById('alerts-section');
    if (alerts.length === 0) {
        container.classList.add('hidden');
        return;
    }
    container.classList.remove('hidden');
    const items = alerts.map(a => `<li><strong>${a.warehouse} (${a.date}):</strong> ${a.message}</li>`).join('');
    container.innerHTML = `<h3>Network Alerts</h3><ul>${items}</ul>`;
}

function setupWarehouseSelector(warehouses) {
    const select = document.getElementById('warehouse-select');
    const warehouseNames = Object.keys(warehouses);
    select.innerHTML = `<option disabled selected>-- Select a Warehouse --</option>` + 
        warehouseNames.map(name => `<option value="${name}">${name}</option>`).join('');

    select.addEventListener('change', (e) => {
        document.getElementById('warehouse-details').classList.remove('hidden');
        renderWarehouseDetails(e.target.value);
    });
}

function renderWarehouseDetails(warehouseName) {
    const warehouseData = forecastData.warehouses[warehouseName];
    
    // Render capacity info and tabs
    document.getElementById('capacity-info-container').innerHTML = `
        <div><strong>Location:</strong> ${warehouseData.capacity_info.location}</div>
        <div><strong>Total Capacity:</strong> ${warehouseData.capacity_info.capacity.toLocaleString()} units</div>
        <div><strong>Alert Threshold:</strong> ${warehouseData.capacity_info.alert_threshold * 100}%</div>
    `;
    
    const tabs = document.querySelectorAll('.tab-button');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const product = tab.dataset.product;
            updateView(warehouseData, product);
        });
    });

    // Set default view to "Overall"
    tabs[0].classList.add('active');
    updateView(warehouseData, 'Overall');
}

function updateView(warehouseData, product) {
    if (mainChart) mainChart.destroy();
    
    if (product === 'Overall') {
        renderOverallView(warehouseData);
    } else {
        renderProductView(warehouseData, product);
    }
}

function renderOverallView(warehouseData) {
    const ctx = document.getElementById('main-chart').getContext('2d');
    const labels = warehouseData.monthly_positions.map(p => p.date);
    const capacity = warehouseData.capacity_info.capacity;
    const alertThreshold = capacity * warehouseData.capacity_info.alert_threshold;
    
    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Projected Inventory', data: warehouseData.monthly_positions.map(p => p.warehouse_total_after), borderColor: '#6f42c1', tension: 0.1, fill: true, backgroundColor: 'rgba(111, 66, 193, 0.1)' },
                { label: 'Capacity', data: Array(12).fill(capacity), borderColor: '#dc3545', borderDash: [5, 5], pointRadius: 0 },
                { label: 'Alert Threshold', data: Array(12).fill(alertThreshold), borderColor: '#fd7e14', borderDash: [5, 5], pointRadius: 0 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // Render Table
    const tableContainer = document.getElementById('details-table-container');
    const rows = warehouseData.monthly_positions.map(p => `
        <tr>
            <td>${p.date}</td>
            <td>${Math.round(p.warehouse_total_before).toLocaleString()}</td>
            <td>${Math.round(p.warehouse_total_after).toLocaleString()}</td>
            <td>${p.capacity_utilization}%</td>
        </tr>`).join('');
    tableContainer.innerHTML = `<table><thead><tr><th>Month</th><th>Start Inv.</th><th>End Inv.</th><th>Capacity Use</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderProductView(warehouseData, productName) {
    const ctx = document.getElementById('main-chart').getContext('2d');
    const productData = warehouseData.products[productName];
    const labels = Object.keys(productData.rolling_inventory);
    
    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Ending Inventory', data: labels.map(m => productData.rolling_inventory[m].ending_position), borderColor: '#6f42c1', tension: 0.1 },
                { label: 'Inflows', data: labels.map(m => productData.rolling_inventory[m].inflow), borderColor: '#28a745' },
                { label: 'Outflows', data: labels.map(m => productData.rolling_inventory[m].outflow), borderColor: '#dc3545' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
    
    // Render Table
    const tableContainer = document.getElementById('details-table-container');
    const rows = labels.map(m => {
        const monthData = productData.rolling_inventory[m];
        return `<tr>
            <td>${m}</td>
            <td>${monthData.starting_position.toLocaleString()}</td>
            <td>${monthData.inflow.toLocaleString()}</td>
            <td>${monthData.outflow.toLocaleString()}</td>
            <td>${monthData.net_flow.toLocaleString()}</td>
            <td>${monthData.ending_position.toLocaleString()}</td>
        </tr>`;
    }).join('');
    tableContainer.innerHTML = `<table><thead><tr><th>Month</th><th>Start</th><th>Inflow</th><th>Outflow</th><th>Net</th><th>End</th></tr></thead><tbody>${rows}</tbody></table>`;
}