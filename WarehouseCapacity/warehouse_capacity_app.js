let capacityData; // Holds all data from the API
let utilizationChart, scenarioChart;

document.addEventListener('DOMContentLoaded', () => {
    fetchCapacityData();
    setupScenarioToggle();
});

async function fetchCapacityData() {
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
        console.log('🔍 Full API Response:', apiData);
        
        if (!apiData.success) throw new Error(apiData.message);

        capacityData = apiData.data; // Store data globally
        renderDashboard();

        loader.classList.add('hidden');
        dashboardContent.classList.remove('hidden');
    } catch (error) {
        console.error('Fetch/Render Error:', error);
        loader.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}

function renderDashboard() {
    if (!capacityData) {
        console.error('❌ No capacity data available');
        return;
    }
    
    console.log('🔧 Rendering dashboard with data:', capacityData);
    
    // Update header timestamp
    const lastUpdated = capacityData.metadata?.generated_at ? 
        new Date(capacityData.metadata.generated_at).toLocaleString() : 
        'Unknown';
    document.getElementById('last-updated').textContent = `Analysis Generated: ${lastUpdated}`;
    
    // Render all dashboard components
    renderNetworkSummary(capacityData.network_optimization_summary);
    renderCapacityAlerts(capacityData.current_state.capacity_alerts);
    renderCurrentStateAnalysis(capacityData.current_state.capacity_analysis);
    renderTransferOpportunities(capacityData.current_state.transfer_opportunities);
    renderProductRecommendations(capacityData.current_state.product_recommendations);
    
    // Set up scenario chart with current state initially
    renderScenarioChart('current');
    
    // Update footer
    const footerElement = document.getElementById('metadata-footer');
    if (footerElement) {
        footerElement.textContent = `Analysis Type: ${capacityData.metadata.analysis_type} | Generated: ${lastUpdated}`;
    }
}

function renderNetworkSummary(summary) {
    const container = document.getElementById('network-summary-kpis');
    if (!container) return;
    
    container.innerHTML = `
        <div class="kpi-card high-util">
            <div class="value">${summary.high_utilization_warehouses}</div>
            <div class="label">High Utilization Warehouses</div>
        </div>
        <div class="kpi-card transfers">
            <div class="value">${summary.transfer_opportunities_identified}</div>
            <div class="label">Transfer Opportunities</div>
        </div>
        <div class="kpi-card alerts">
            <div class="value">${summary.high_priority_actions}</div>
            <div class="label">High Priority Actions</div>
        </div>
        <div class="kpi-card savings">
            <div class="value">$${summary.potential_cost_savings.toLocaleString()}</div>
            <div class="label">Potential Savings</div>
        </div>
        <div class="kpi-card scenarios">
            <div class="value">${summary.scenario_demonstration.scenario_transfers}</div>
            <div class="label">Scenario Transfers</div>
        </div>
    `;
}

function renderCapacityAlerts(alerts) {
    const container = document.getElementById('alerts-section');
    if (!container || !alerts || alerts.length === 0) {
        container.classList.add('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    
    const alertItems = alerts.map(alert => `
        <li class="${alert.severity}">
            <div class="alert-header">${alert.type} - ${alert.warehouse}</div>
            <div class="alert-message">${alert.message}</div>
            <div class="alert-recommendation">Recommendation: ${alert.recommendation}</div>
        </li>
    `).join('');
    
    container.innerHTML = `
        <h2>Capacity Alerts</h2>
        <ul>${alertItems}</ul>
    `;
}

function renderCurrentStateAnalysis(capacityAnalysis) {
    // Render utilization chart
    renderUtilizationChart(capacityAnalysis);
    
    // Render warehouse details table
    renderWarehouseDetailsTable(capacityAnalysis);
}

function renderUtilizationChart(capacityAnalysis) {
    const ctx = document.getElementById('utilizationChart').getContext('2d');
    if (utilizationChart) utilizationChart.destroy();
    
    const warehouses = Object.keys(capacityAnalysis);
    const utilizationData = warehouses.map(wh => 
        capacityAnalysis[wh].utilization_metrics.final_utilization
    );
    const riskColors = warehouses.map(wh => {
        const risk = capacityAnalysis[wh].risk_assessment.level;
        switch(risk) {
            case 'HIGH': return '#dc3545';
            case 'MEDIUM': return '#ffc107';
            case 'LOW': return '#17a2b8';
            default: return '#28a745';
        }
    });
    
    utilizationChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: warehouses,
            datasets: [{
                label: 'Capacity Utilization (%)',
                data: utilizationData,
                backgroundColor: riskColors,
                borderColor: riskColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Utilization Percentage'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterBody: function(context) {
                            const wh = warehouses[context[0].dataIndex];
                            const data = capacityAnalysis[wh];
                            return [
                                `Risk Level: ${data.risk_assessment.level}`,
                                `Trend: ${data.trend_analysis.trend_direction}`,
                                `Available: ${data.warehouse_info.available_capacity.toLocaleString()} units`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function renderWarehouseDetailsTable(capacityAnalysis) {
    const container = document.getElementById('warehouse-details-table');
    if (!container) return;
    
    const tableRows = Object.entries(capacityAnalysis).map(([warehouse, data]) => {
        const utilization = data.utilization_metrics.final_utilization;
        const utilizationClass = utilization > 80 ? 'high' : utilization > 50 ? 'medium' : 'low';
        
        return `
            <tr>
                <td><strong>${warehouse}</strong></td>
                <td>${data.warehouse_info.current_inventory.toLocaleString()}</td>
                <td>${data.warehouse_info.max_capacity.toLocaleString()}</td>
                <td>
                    <div class="utilization-bar">
                        <div class="utilization-fill ${utilizationClass}" style="width: ${utilization}%"></div>
                    </div>
                    ${utilization.toFixed(1)}%
                </td>
                <td>${data.warehouse_info.available_capacity.toLocaleString()}</td>
                <td><span class="risk-indicator ${data.risk_assessment.level}">${data.risk_assessment.level}</span></td>
                <td>${data.trend_analysis.trend_direction}</td>
            </tr>
        `;
    }).join('');
    
    container.innerHTML = `
        <table class="warehouse-table">
            <thead>
                <tr>
                    <th>Warehouse</th>
                    <th>Current Inventory</th>
                    <th>Max Capacity</th>
                    <th>Utilization</th>
                    <th>Available Space</th>
                    <th>Risk Level</th>
                    <th>Trend</th>
                </tr>
            </thead>
            <tbody>
                ${tableRows}
            </tbody>
        </table>
    `;
}

function renderTransferOpportunities(transfers) {
    const container = document.getElementById('transfer-opportunities');
    if (!container) return;
    
    if (!transfers || transfers.length === 0) {
        container.innerHTML = '<p>No transfer opportunities identified at this time.</p>';
        return;
    }
    
    const transferCards = transfers.map(transfer => `
        <div class="transfer-card">
            <div class="transfer-details">
                <h4>${transfer.source_warehouse} → ${transfer.destination_warehouse}</h4>
                <p><strong>Transfer Amount:</strong> ${transfer.recommended_transfer.toLocaleString()} units</p>
                <p><strong>Utilization Impact:</strong> ${transfer.impact_metrics.utilization_improvement}% improvement</p>
                <p><strong>Cost Analysis:</strong> $${transfer.cost_analysis.estimated_transfer_cost.toLocaleString()} cost, $${transfer.cost_analysis.estimated_storage_savings.toLocaleString()} savings</p>
            </div>
            <div class="transfer-metrics">
                <div class="metric-value">${transfer.cost_analysis.roi_percentage}%</div>
                <div class="metric-label">ROI</div>
            </div>
            <div class="transfer-priority ${transfer.priority}">
                ${transfer.priority}
            </div>
        </div>
    `).join('');
    
    container.innerHTML = transferCards;
}

function renderProductRecommendations(productRecs) {
    const container = document.getElementById('product-recommendations');
    if (!container) return;
    
    if (!productRecs || Object.keys(productRecs).length === 0) {
        container.innerHTML = '<p>No product-level recommendations available.</p>';
        return;
    }
    
    const productCards = Object.entries(productRecs).map(([product, data]) => {
        const warehouseLevels = Object.entries(data.warehouse_levels).map(([wh, level]) => `
            <div class="warehouse-level">
                <div class="warehouse-name">${wh}</div>
                <div class="inventory-amount">${level.current_inventory.toLocaleString()}</div>
            </div>
        `).join('');
        
        const transferSuggestions = data.transfer_suggestions.map(suggestion => `
            <div class="product-transfer-item">
                <span><strong>${suggestion.from_warehouse} → ${suggestion.to_warehouse}:</strong> ${suggestion.recommended_quantity.toLocaleString()} units</span>
                <span>${suggestion.reason}</span>
            </div>
        `).join('');
        
        return `
            <div class="product-card">
                <h4>${product} Inventory Levels</h4>
                <div class="product-levels">
                    ${warehouseLevels}
                </div>
                ${transferSuggestions ? `
                    <div class="product-transfers">
                        <h5>Transfer Suggestions:</h5>
                        ${transferSuggestions}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    container.innerHTML = productCards;
}

function setupScenarioToggle() {
    const currentBtn = document.getElementById('current-state-btn');
    const scenarioBtn = document.getElementById('scenario-state-btn');
    
    currentBtn.addEventListener('click', () => {
        currentBtn.classList.add('active');
        scenarioBtn.classList.remove('active');
        renderScenarioChart('current');
    });
    
    scenarioBtn.addEventListener('click', () => {
        scenarioBtn.classList.add('active');
        currentBtn.classList.remove('active');
        renderScenarioChart('scenario');
    });
}

function renderScenarioChart(mode) {
    const ctx = document.getElementById('scenarioChart').getContext('2d');
    if (scenarioChart) scenarioChart.destroy();
    
    let analysisData, title, summary;
    
    if (mode === 'current') {
        analysisData = capacityData.current_state.capacity_analysis;
        title = 'Current State Analysis';
        summary = `
            <h4>Current State Summary</h4>
            <p><strong>Total Warehouses:</strong> ${capacityData.network_optimization_summary.total_warehouses_analyzed}</p>
            <p><strong>High Utilization:</strong> ${capacityData.network_optimization_summary.high_utilization_warehouses} warehouses</p>
            <p><strong>Transfer Opportunities:</strong> ${capacityData.network_optimization_summary.transfer_opportunities_identified}</p>
            <p><strong>Potential Savings:</strong> $${capacityData.network_optimization_summary.potential_cost_savings.toLocaleString()}</p>
        `;
    } else {
        analysisData = capacityData.high_demand_scenario.capacity_analysis;
        title = 'High-Demand Scenario';
        summary = `
            <h4>High-Demand Scenario</h4>
            <p><strong>Description:</strong> ${capacityData.high_demand_scenario.scenario_description}</p>
            <p><strong>Scenario Transfers:</strong> ${capacityData.network_optimization_summary.scenario_demonstration.scenario_transfers}</p>
            <p><strong>Scenario Alerts:</strong> ${capacityData.network_optimization_summary.scenario_demonstration.scenario_alerts}</p>
            <p><strong>Scenario Savings:</strong> $${capacityData.network_optimization_summary.scenario_demonstration.scenario_savings.toLocaleString()}</p>
        `;
    }
    
    const warehouses = Object.keys(analysisData);
    const utilizationData = warehouses.map(wh => 
        analysisData[wh].utilization_metrics.final_utilization
    );
    
    // Create color coding based on utilization levels
    const colors = utilizationData.map(util => {
        if (util > 85) return '#dc3545'; // High risk - red
        if (util > 70) return '#ffc107'; // Medium risk - yellow
        if (util > 50) return '#17a2b8'; // Low risk - blue
        return '#28a745'; // Safe - green
    });
    
    scenarioChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: warehouses,
            datasets: [{
                label: 'Capacity Utilization (%)',
                data: utilizationData,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Utilization Percentage'
                    }
                }
            }
        }
    });
    
    // Update scenario summary
    const summaryContainer = document.getElementById('scenario-summary');
    if (summaryContainer) {
        summaryContainer.innerHTML = summary;
    }
}