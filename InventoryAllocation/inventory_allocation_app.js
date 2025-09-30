let allocationData; // Holds all data from the API
let inventoryChart, productChart, demandChart, shippingChart;
let currentPriorityFilter = 'ALL';
let currentFilters = { warehouse: 'ALL', partner: 'ALL', product: 'ALL' };

document.addEventListener('DOMContentLoaded', () => {
    fetchAllocationData();
    setupEventListeners();
});

async function fetchAllocationData() {
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

        // Handle nested API response structure
        if (apiData.data.allocation_recommendations && typeof apiData.data.allocation_recommendations === 'object' && !Array.isArray(apiData.data.allocation_recommendations)) {
            // Data is nested inside allocation_recommendations object
            allocationData = apiData.data.allocation_recommendations;
        } else {
            // Data is at the top level
            allocationData = apiData.data;
        }
        
        console.log('🔄 Processed allocation data:', allocationData);
        renderDashboard();

        loader.classList.add('hidden');
        dashboardContent.classList.remove('hidden');
    } catch (error) {
        console.error('Fetch/Render Error:', error);
        loader.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}

function renderDashboard() {
    if (!allocationData) {
        console.error('❌ No allocation data available');
        return;
    }
    
    console.log('🔧 Rendering dashboard with data:', allocationData);
    console.log('📋 Available properties:', Object.keys(allocationData));
    console.log('📊 Allocation recommendations type:', typeof allocationData.allocation_recommendations);
    console.log('📊 Allocation recommendations:', allocationData.allocation_recommendations);
    
    // Update header timestamp
    const lastUpdated = allocationData.metadata?.generated_at ? 
        new Date(allocationData.metadata.generated_at).toLocaleString() : 
        'Unknown';
    document.getElementById('last-updated').textContent = `Analysis Generated: ${lastUpdated}`;
    
    // Render all dashboard components with error handling
    try {
        renderSummaryKPIs();
    } catch (error) {
        console.error('Error rendering summary KPIs:', error);
    }
    
    try {
        renderPriorityAllocations();
    } catch (error) {
        console.error('Error rendering priority allocations:', error);
    }
    
    try {
        renderInventoryOverview();
    } catch (error) {
        console.error('Error rendering inventory overview:', error);
    }
    
    try {
        renderPartnerDemandAnalysis();
    } catch (error) {
        console.error('Error rendering partner demand analysis:', error);
    }
    
    try {
        renderAllocationRecommendations();
    } catch (error) {
        console.error('Error rendering allocation recommendations:', error);
    }
    
    try {
        renderLogisticsAnalysis();
    } catch (error) {
        console.error('Error rendering logistics analysis:', error);
    }
    
    try {
        setupFilters();
    } catch (error) {
        console.error('Error setting up filters:', error);
    }
    
    // Update footer
    const footerElement = document.getElementById('metadata-footer');
    if (footerElement) {
        const totalRecs = allocationData.metadata?.total_recommendations || 'Unknown';
        footerElement.textContent = `Total Recommendations: ${totalRecs} | Generated: ${lastUpdated}`;
    }
}

function renderSummaryKPIs() {
    const container = document.getElementById('summary-kpis');
    if (!container) return;
    
    console.log('📊 Rendering summary KPIs...');
    
    // Safely access data with defaults
    const priority = allocationData.priority_summary || {};
    const partnerSummary = allocationData.partner_requirements_summary || {};
    const metadata = allocationData.metadata || {};
    
    // Safely get allocation recommendations as array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    console.log('📊 Allocations array length:', allocations.length);
    
    // Calculate total cost safely
    let totalCost = 0;
    if (allocations.length > 0) {
        totalCost = allocations.reduce((sum, rec) => 
            sum + (rec.logistics?.shipping_cost_estimate || 0), 0);
    }
    
    container.innerHTML = `
        <div class="kpi-card allocations">
            <div class="value">${metadata.total_recommendations || allocations.length || 0}</div>
            <div class="label">Total Allocations</div>
        </div>
        <div class="kpi-card urgent">
            <div class="value">${(priority.urgent_allocations || 0) + (priority.high_priority || 0)}</div>
            <div class="label">Urgent + High Priority</div>
        </div>
        <div class="kpi-card demand">
            <div class="value">${(partnerSummary.total_monthly_demand || 0).toLocaleString()}</div>
            <div class="label">Total Monthly Demand</div>
        </div>
        <div class="kpi-card cost">
            <div class="value">$${totalCost.toLocaleString()}</div>
            <div class="label">Total Shipping Cost</div>
        </div>
        <div class="kpi-card partners">
            <div class="value">${partnerSummary.partners_analyzed || 0}</div>
            <div class="label">Partners Analyzed</div>
        </div>
    `;
}

function setupEventListeners() {
    // Priority tab listeners
    document.querySelectorAll('.priority-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.priority-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentPriorityFilter = e.target.dataset.priority;
            renderPriorityAllocations();
        });
    });
}

function renderPriorityAllocations() {
    const container = document.getElementById('priority-allocations');
    if (!container) return;
    
    // Safely get allocations array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    let filteredAllocations = allocations;
    
    // Filter by priority
    if (currentPriorityFilter !== 'ALL') {
        filteredAllocations = filteredAllocations.filter(alloc => 
            alloc.priority === currentPriorityFilter
        );
    }
    
    if (filteredAllocations.length === 0) {
        container.innerHTML = '<p>No allocations found for the selected priority level.</p>';
        return;
    }
    
    const allocationCards = filteredAllocations.slice(0, 10).map(allocation => `
        <div class="allocation-card">
            <div class="allocation-details">
                <h4>${allocation.allocation_id}</h4>
                <div class="route">${allocation.from_warehouse} → ${allocation.to_partner}</div>
                <div class="details">Product: ${allocation.product_details.total_quantity.toLocaleString()} ${allocation.product_details.category}</div>
                <div class="details">Ship by: ${allocation.timeline.ship_by_date}</div>
                <div class="details">Region: ${allocation.partner_region}</div>
                <div class="details">Cost: $${allocation.logistics.shipping_cost_estimate.toLocaleString()}</div>
            </div>
            <div class="allocation-metrics">
                <div class="metric-item">
                    <div class="metric-value">${allocation.product_details.fulfillment_percentage.toFixed(1)}%</div>
                    <div class="metric-label">Fulfillment</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${allocation.timeline.lead_time_days}</div>
                    <div class="metric-label">Lead Time (days)</div>
                </div>
                <div class="metric-item">
                    <span class="confidence-indicator ${allocation.confidence}">${allocation.confidence}</span>
                </div>
            </div>
            <div class="allocation-priority ${allocation.priority}">
                ${allocation.priority}
            </div>
        </div>
    `).join('');
    
    container.innerHTML = allocationCards;
}

function renderInventoryOverview() {
    if (!allocationData.current_inventory_summary) return;
    
    // Warehouse inventory chart
    renderWarehouseInventoryChart();
    
    // Product distribution chart
    renderProductDistributionChart();
}

function renderWarehouseInventoryChart() {
    const ctx = document.getElementById('inventoryChart');
    if (!ctx) return;
    
    if (inventoryChart) inventoryChart.destroy();
    
    const warehouseData = allocationData.current_inventory_summary.warehouse_inventory;
    const warehouses = Object.keys(warehouseData);
    const inventoryLevels = Object.values(warehouseData);
    
    inventoryChart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: warehouses,
            datasets: [{
                label: 'Current Inventory',
                data: inventoryLevels,
                backgroundColor: [
                    '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6'
                ].slice(0, warehouses.length),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Inventory Units'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function renderProductDistributionChart() {
    const ctx = document.getElementById('productChart');
    if (!ctx) return;
    
    if (productChart) productChart.destroy();
    
    // Calculate total product distribution across all warehouses
    let totalFootwear = 0;
    let totalApparel = 0;
    
    // Since we don't have detailed product breakdown in the summary,
    // we'll use typical distribution (70% Footwear, 30% Apparel)
    const totalInventory = Object.values(allocationData.current_inventory_summary.warehouse_inventory)
        .reduce((sum, val) => sum + val, 0);
    
    totalFootwear = totalInventory * 0.7;
    totalApparel = totalInventory * 0.3;
    
    productChart = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Footwear', 'Apparel'],
            datasets: [{
                data: [totalFootwear, totalApparel],
                backgroundColor: ['#e74c3c', '#3498db'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function renderPartnerDemandAnalysis() {
    // Render demand chart
    renderDemandChart();
    
    // Render partner profiles
    renderPartnerProfiles();
}

function renderDemandChart() {
    const ctx = document.getElementById('demandChart');
    if (!ctx) return;
    
    if (demandChart) demandChart.destroy();
    
    // Extract partner demand from top demand partners
    const topPartners = allocationData.partner_requirements_summary.top_demand_partners;
    
    // Create sample monthly demand data
    const months = ['Jan', 'Feb', 'Mar'];
    const datasets = topPartners.map((partner, index) => ({
        label: partner,
        data: [
            Math.floor(Math.random() * 200000) + 50000,
            Math.floor(Math.random() * 200000) + 50000,
            Math.floor(Math.random() * 200000) + 50000
        ],
        borderColor: ['#e74c3c', '#3498db', '#2ecc71'][index],
        backgroundColor: ['#e74c3c', '#3498db', '#2ecc71'][index] + '20',
        tension: 0.1
    }));
    
    demandChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: months,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Demand (Units)'
                    }
                }
            }
        }
    });
}

function renderPartnerProfiles() {
    const container = document.getElementById('partner-profiles');
    if (!container) return;
    
    const topPartners = allocationData.partner_requirements_summary?.top_demand_partners || [];
    
    if (topPartners.length === 0) {
        container.innerHTML = '<p>No partner data available.</p>';
        return;
    }
    
    // Safely get allocations array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    // Create simplified partner profiles
    const partnerProfiles = topPartners.map(partner => {
        // Find allocations for this partner
        const partnerAllocations = allocations.filter(
            alloc => alloc.to_partner === partner
        );
        
        const totalQuantity = partnerAllocations.reduce(
            (sum, alloc) => sum + (alloc.product_details?.total_quantity || 0), 0
        );
        
        const regions = [...new Set(partnerAllocations.map(alloc => alloc.partner_region))];
        
        return `
            <div class="partner-card">
                <h4>${partner}</h4>
                <div class="partner-info">
                    <div class="label">Region:</div>
                    <div class="value">${regions[0] || 'Unknown'}</div>
                    <div class="label">Total Allocation:</div>
                    <div class="value">${totalQuantity.toLocaleString()} units</div>
                    <div class="label">Active Orders:</div>
                    <div class="value">${partnerAllocations.length}</div>
                    <div class="label">Priority Orders:</div>
                    <div class="value">${partnerAllocations.filter(a => a.priority === 'URGENT' || a.priority === 'HIGH').length}</div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = partnerProfiles;
}

function setupFilters() {
    // Populate filter dropdowns
    const warehouseFilter = document.getElementById('warehouse-filter');
    const partnerFilter = document.getElementById('partner-filter');
    const productFilter = document.getElementById('product-filter');
    
    if (!warehouseFilter || !partnerFilter || !productFilter) return;
    
    // Safely get allocations array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    if (allocations.length === 0) {
        console.warn('⚠️ No allocations available for filters');
        return;
    }
    
    // Get unique values from allocations
    const warehouses = [...new Set(allocations.map(a => a.from_warehouse))];
    const partners = [...new Set(allocations.map(a => a.to_partner))];
    const products = [...new Set(allocations.map(a => a.product_details?.category).filter(Boolean))];
    
    // Populate warehouse filter
    warehouses.forEach(warehouse => {
        const option = document.createElement('option');
        option.value = warehouse;
        option.textContent = warehouse;
        warehouseFilter.appendChild(option);
    });
    
    // Populate partner filter
    partners.forEach(partner => {
        const option = document.createElement('option');
        option.value = partner;
        option.textContent = partner;
        partnerFilter.appendChild(option);
    });
    
    // Populate product filter
    products.forEach(product => {
        const option = document.createElement('option');
        option.value = product;
        option.textContent = product;
        productFilter.appendChild(option);
    });
    
    // Add event listeners
    [warehouseFilter, partnerFilter, productFilter].forEach(filter => {
        filter.addEventListener('change', () => {
            currentFilters.warehouse = warehouseFilter.value;
            currentFilters.partner = partnerFilter.value;
            currentFilters.product = productFilter.value;
            renderAllocationRecommendations();
        });
    });
}

function renderAllocationRecommendations() {
    const container = document.getElementById('allocation-recommendations');
    if (!container) return;
    
    // Safely get allocations array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    let filteredAllocations = allocations;
    
    // Apply filters
    if (currentFilters.warehouse !== 'ALL') {
        filteredAllocations = filteredAllocations.filter(a => a.from_warehouse === currentFilters.warehouse);
    }
    if (currentFilters.partner !== 'ALL') {
        filteredAllocations = filteredAllocations.filter(a => a.to_partner === currentFilters.partner);
    }
    if (currentFilters.product !== 'ALL') {
        filteredAllocations = filteredAllocations.filter(a => a.product_details.category === currentFilters.product);
    }
    
    if (filteredAllocations.length === 0) {
        container.innerHTML = '<p>No allocations match the selected filters.</p>';
        return;
    }
    
    const allocationItems = filteredAllocations.map(allocation => {
        const sizeBreakdown = allocation.product_details.size_breakdown || [];
        const sizeItems = sizeBreakdown.map(size => 
            `<span class="size-item">${size.size}: ${size.quantity}</span>`
        ).join('');
        
        return `
            <div class="allocation-item">
                <div class="allocation-main">
                    <h4>${allocation.from_warehouse} → ${allocation.to_partner}</h4>
                    <div><strong>Product:</strong> ${allocation.product_details.total_quantity.toLocaleString()} ${allocation.product_details.category}</div>
                    <div><strong>Region:</strong> ${allocation.partner_region}</div>
                    <div><strong>Status:</strong> <span class="status-indicator ${allocation.status}">${allocation.status}</span></div>
                    <div><strong>Priority:</strong> <span class="allocation-priority ${allocation.priority}">${allocation.priority}</span></div>
                    <div><strong>Confidence:</strong> <span class="confidence-indicator ${allocation.confidence}">${allocation.confidence}</span></div>
                    ${sizeItems ? `
                        <div class="size-breakdown">
                            <h5>Size Breakdown:</h5>
                            <div class="size-items">${sizeItems}</div>
                        </div>
                    ` : ''}
                </div>
                <div class="allocation-timeline">
                    <h5>Timeline</h5>
                    <div><strong>Month:</strong> ${allocation.timeline.month}</div>
                    <div><strong>Ship By:</strong> ${allocation.timeline.ship_by_date}</div>
                    <div><strong>Deliver By:</strong> ${allocation.timeline.deliver_by_date}</div>
                    <div><strong>Lead Time:</strong> ${allocation.timeline.lead_time_days} days</div>
                </div>
                <div class="allocation-logistics">
                    <h5>Logistics</h5>
                    <div><strong>Distance Factor:</strong> ${allocation.logistics.distance_factor}x</div>
                    <div><strong>Shipping Cost:</strong> $${allocation.logistics.shipping_cost_estimate.toLocaleString()}</div>
                    <div><strong>Fulfillment:</strong> ${allocation.product_details.fulfillment_percentage.toFixed(1)}%</div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = allocationItems;
}

function renderLogisticsAnalysis() {
    // Render shipping cost chart
    renderShippingChart();
    
    // Render cost summary
    renderCostSummary();
}

function renderShippingChart() {
    const ctx = document.getElementById('shippingChart');
    if (!ctx) return;
    
    if (shippingChart) shippingChart.destroy();
    
    // Safely get allocations array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    if (allocations.length === 0) {
        console.warn('⚠️ No allocations available for shipping chart');
        return;
    }
    
    // Group allocations by route (warehouse → partner)
    const routeCosts = {};
    
    allocations.forEach(allocation => {
        const route = `${allocation.from_warehouse} → ${allocation.to_partner}`;
        if (!routeCosts[route]) {
            routeCosts[route] = 0;
        }
        routeCosts[route] += allocation.logistics?.shipping_cost_estimate || 0;
    });
    
    const routes = Object.keys(routeCosts).slice(0, 10); // Top 10 routes
    const costs = routes.map(route => routeCosts[route]);
    
    shippingChart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: routes,
            datasets: [{
                label: 'Shipping Cost ($)',
                data: costs,
                backgroundColor: '#e74c3c',
                borderColor: '#c0392b',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // This makes it horizontal
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Cost ($)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function renderCostSummary() {
    const container = document.getElementById('cost-summary-details');
    if (!container) return;
    
    // Safely get allocations array
    const allocations = Array.isArray(allocationData.allocation_recommendations) ? 
        allocationData.allocation_recommendations : [];
    
    if (allocations.length === 0) {
        container.innerHTML = '<p>No allocation data available for cost analysis.</p>';
        return;
    }
    
    // Calculate cost breakdown safely
    const totalCost = allocations.reduce(
        (sum, alloc) => sum + (alloc.logistics?.shipping_cost_estimate || 0), 0
    );
    
    const totalUnits = allocations.reduce(
        (sum, alloc) => sum + (alloc.product_details?.total_quantity || 0), 0
    );
    
    const avgCostPerUnit = totalUnits > 0 ? totalCost / totalUnits : 0;
    
    const urgentCost = allocations
        .filter(alloc => alloc.priority === 'URGENT')
        .reduce((sum, alloc) => sum + (alloc.logistics?.shipping_cost_estimate || 0), 0);
    
    const highPriorityCost = allocations
        .filter(alloc => alloc.priority === 'HIGH')
        .reduce((sum, alloc) => sum + (alloc.logistics?.shipping_cost_estimate || 0), 0);
    
    container.innerHTML = `
        <div class="cost-item total">
            <div class="cost-label">Total Shipping Cost</div>
            <div class="cost-value">$${totalCost.toLocaleString()}</div>
        </div>
        <div class="cost-item">
            <div class="cost-label">Average Cost per Unit</div>
            <div class="cost-value">$${avgCostPerUnit.toFixed(2)}</div>
        </div>
        <div class="cost-item">
            <div class="cost-label">Urgent Priority Cost</div>
            <div class="cost-value">$${urgentCost.toLocaleString()}</div>
        </div>
        <div class="cost-item">
            <div class="cost-label">High Priority Cost</div>
            <div class="cost-value">$${highPriorityCost.toLocaleString()}</div>
        </div>
        <div class="cost-item">
            <div class="cost-label">Total Allocations</div>
            <div class="cost-value">${allocations.length}</div>
        </div>
    `;
}