// Variable to hold the chart instance so it can be updated
let productMixChartInstance;

// Main entry point for the dashboard's client-side logic
document.addEventListener('DOMContentLoaded', () => {
    fetchPartnerDemand();
});

/**
 * Fetches the forecast data from the middleware Suitelet.
 */
async function fetchPartnerDemand() {
    const loader = document.getElementById('loader');
    const dashboardContent = document.getElementById('dashboard-content');
    
    if (!window.NS_CONFIG || !window.NS_CONFIG.middlewareUrls.partnerDemand) {
        console.error('NetSuite configuration object not found.');
        loader.innerHTML = '<p style="color: red;">Error: Could not find middleware URL. Configuration is missing.</p>';
        return;
    }

    const apiUrl = window.NS_CONFIG.middlewareUrls.partnerDemand;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`API request failed with status: ${response.status}`);
        }
        const forecastData = await response.json();

        if (!forecastData.success) {
            throw new Error(forecastData.message || 'The API returned an unsuccessful response.');
        }

        renderDashboard(forecastData.data);

        loader.classList.add('hidden');
        dashboardContent.classList.remove('hidden');

    } catch (error) {
        console.error('Failed to fetch or render partner demand data:', error);
        loader.innerHTML = `<p style="color: red;">Error loading dashboard: ${error.message}</p>`;
    }
}

/**
 * Main rendering function to populate the entire dashboard.
 */
function renderDashboard(data) {
    const { analytics, metadata, partner_forecasts } = data;
    
    document.getElementById('last-updated').textContent = `Forecast generated at: ${new Date(metadata.generated_at).toLocaleString()}`;
    
    renderKpiCards(analytics.network_summary);
    renderTopPartnersTable(analytics.network_summary.top_5_partners);
    renderProductMix(analytics.network_summary.product_mix); // This will now call the chart function
    renderRegionalBreakdown(analytics.network_summary.regional_breakdown);
    renderGrowthInsights(analytics.growth_insights);
    renderRiskAssessment(analytics.risk_assessment);
    setupPartnerSelector(partner_forecasts);
}

/**
 * Renders the main KPI cards.
 */
function renderKpiCards(summary) {
    const container = document.getElementById('kpi-cards');
    container.innerHTML = `
        <div class="kpi-card">
            <p class="value">${summary.total_predicted_volume.toLocaleString()}</p>
            <p class="label">Total Predicted Volume</p>
        </div>
        <div class="kpi-card">
            <p class="value">${summary.total_partners}</p>
            <p class="label">Total Partners Forecasted</p>
        </div>
        <div class="kpi-card">
            <p class="value">${Object.keys(summary.regional_breakdown).length}</p>
            <p class="label">Regions Covered</p>
        </div>
    `;
}

/**
 * Renders the Top 5 Partners table.
 */
function renderTopPartnersTable(topPartners) {
    const container = document.getElementById('top-partners-table-container');
    const rows = topPartners.map(partner => `
        <tr>
            <td>${partner.name}</td>
            <td>${partner.predicted_volume.toLocaleString()}</td>
        </tr>
    `).join('');

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Partner Name</th>
                    <th>Predicted Volume</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

/**
 * Renders the product mix data as a pie chart.
 */
function renderProductMix(productMix) {
    const canvas = document.getElementById('productMixChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = Object.keys(productMix);
    const data = Object.values(productMix);

    if (productMixChartInstance) {
        productMixChartInstance.destroy();
    }

    productMixChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: 'Volume',
                data: data,
                backgroundColor: ['rgba(54, 162, 235, 0.8)', 'rgba(255, 99, 132, 0.8)'],
                borderColor: ['rgba(54, 162, 235, 1)', 'rgba(255, 99, 132, 1)'],
                borderWidth: 1,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let value = context.parsed || 0;
                            return `${context.label}: ${value.toLocaleString()}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Renders the regional breakdown table.
 */
function renderRegionalBreakdown(regionalData) {
    const container = document.getElementById('regional-breakdown-container');
    const sortedRegions = Object.entries(regionalData).sort((a, b) => b[1].volume - a[1].volume);
    const rows = sortedRegions.map(([region, data]) => `
        <tr>
            <td>${region}</td>
            <td>${data.volume.toLocaleString()}</td>
        </tr>
    `).join('');

    container.innerHTML = `
        <table>
            <thead>
                <tr><th>Region</th><th>Predicted Volume</th></tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

/**
 * Renders the growth insights lists.
 */
function renderGrowthInsights(growthData) {
    const container = document.getElementById('growth-insights-container');
    container.innerHTML = `
        <div class="insight-category">
            <h4>Growth Insights</h4>
            <ul>${growthData.growing_partners.map(p => `<li>${p} (Growing)</li>`).join('')}</ul>
            <ul>${growthData.stable_partners.map(p => `<li>${p} (Stable)</li>`).join('')}</ul>
            <ul>${growthData.declining_partners.map(p => `<li>${p} (Declining)</li>`).join('')}</ul>
        </div>
    `;
}

/**
 * Renders the risk assessment lists.
 */
function renderRiskAssessment(riskData) {
    const container = document.getElementById('risk-assessment-container');
    container.innerHTML = `
        <div class="insight-category">
            <h4>Risk Assessment</h4>
            <ul>${riskData.high_confidence_partners.map(p => `<li>${p} (High Confidence)</li>`).join('')}</ul>
            <ul>${riskData.low_confidence_partners.map(p => `<li>${p} (Low Confidence)</li>`).join('')}</ul>
        </div>
    `;
}

/**
 * Populates the partner dropdown and sets up an event listener.
 */
function setupPartnerSelector(partnerForecasts) {
    const selectElement = document.getElementById('partner-select');
    const partnerNames = Object.keys(partnerForecasts).sort();
    
    selectElement.innerHTML = '<option value="" disabled selected>Choose a partner...</option>';
    
    partnerNames.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        selectElement.appendChild(option);
    });

    selectElement.addEventListener('change', (event) => {
        const selectedPartnerName = event.target.value;
        if (selectedPartnerName) {
            const partnerData = partnerForecasts[selectedPartnerName];
            renderPartnerSummary(partnerData);
            renderDetailedMonthlyTable(partnerData);
        }
    });
}

/**
 * Renders the summary card for a selected partner.
 */
function renderPartnerSummary(partnerData) {
    const container = document.getElementById('partner-summary-container');
    const summary = partnerData.forecast_summary;
    const info = partnerData.partner_info;
    
    const vsHist = summary.vs_historical_monthly;
    const vsHistClass = vsHist >= 0 ? 'growth-positive' : 'growth-negative';
    const vsHistSign = vsHist >= 0 ? '+' : '';

    container.innerHTML = `
        <div class="summary-item">
            <div class="label">Growth Indication</div>
            <div class="value">${summary.growth_indication}</div>
        </div>
        <div class="summary-item">
            <div class="label">Forecast Monthly Avg.</div>
            <div class="value">${summary.monthly_average.toLocaleString()}</div>
        </div>
        <div class="summary-item">
            <div class="label">Historical Monthly Avg.</div>
            <div class="value">${info.historical_monthly_avg.toLocaleString()}</div>
        </div>
        <div class="summary-item">
            <div class="label">vs. Historical</div>
            <div class="value ${vsHistClass}">${vsHistSign}${vsHist.toLocaleString()}</div>
        </div>
    `;
}

/**
 * Renders the detailed monthly table for a selected partner.
 */
function renderDetailedMonthlyTable(partnerData) {
    const container = document.getElementById('monthly-forecast-container');
    const monthlyTotals = partnerData.monthly_totals;
    const productForecasts = partnerData.product_forecasts;

    const rows = Object.entries(monthlyTotals).map(([month, data]) => {
        const apparel = productForecasts.Apparel[month];
        const footwear = productForecasts.Footwear[month];
        
        return `
            <tr>
                <td>${month}</td>
                <td>${apparel.forecast.toLocaleString()}</td>
                <td>${footwear.forecast.toLocaleString()}</td>
                <td>${(apparel.lower_bound + footwear.lower_bound).toLocaleString()} - ${(apparel.upper_bound + footwear.upper_bound).toLocaleString()}</td>
                <td><strong>${data.total_forecast.toLocaleString()}</strong></td>
            </tr>
        `;
    }).join('');

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Month</th>
                    <th>Apparel Volume</th>
                    <th>Footwear Volume</th>
                    <th>Confidence Range (80%)</th>
                    <th>Total Predicted Volume</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}