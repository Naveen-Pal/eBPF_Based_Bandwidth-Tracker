// API Base URL
const API_BASE = '/api';

// Global state
let refreshInterval = null;
let bandwidthChart = null;
let currentData = null;

// Utility function to format bytes
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeControls();
    loadCurrentStats();
    startAutoRefresh();
});

// Tab switching
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(tc => tc.classList.remove('active'));
            
            // Add active class to clicked tab
            tab.classList.add('active');
            
            // Show corresponding content
            const tabName = tab.getAttribute('data-tab');
            const content = document.getElementById(tabName);
            content.classList.add('active');
            
            // Load data for the tab
            loadTabData(tabName);
        });
    });
}

// Initialize controls
function initializeControls() {
    const refreshBtn = document.getElementById('refreshBtn');
    const autoRefreshCheckbox = document.getElementById('autoRefresh');
    const timeWindow = document.getElementById('timeWindow');
    const searchProcess = document.getElementById('searchProcess');
    const filterIpBtn = document.getElementById('filterIpBtn');
    const updateChartBtn = document.getElementById('updateChartBtn');
    
    refreshBtn.addEventListener('click', () => refreshAllData());
    
    autoRefreshCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    timeWindow.addEventListener('change', () => refreshAllData());
    
    if (searchProcess) {
        searchProcess.addEventListener('input', (e) => filterProcessTable(e.target.value));
    }
    
    if (filterIpBtn) {
        filterIpBtn.addEventListener('click', () => loadIpBreakdown());
    }
    
    if (updateChartBtn) {
        updateChartBtn.addEventListener('click', () => loadBandwidthChart());
    }
}

// Load data based on active tab
function loadTabData(tabName) {
    switch(tabName) {
        case 'current':
            loadCurrentStats();
            break;
        case 'history':
            loadHistoryStats();
            break;
        case 'protocol':
            loadProtocolBreakdown();
            break;
        case 'ips':
            loadIpBreakdown();
            break;
        case 'charts':
            loadBandwidthChart();
            break;
    }
}

// Refresh all data
function refreshAllData() {
    const activeTab = document.querySelector('.tab.active');
    const tabName = activeTab ? activeTab.getAttribute('data-tab') : 'current';
    loadTabData(tabName);
    loadSummaryStats();
}

// Load current real-time stats
async function loadCurrentStats() {
    try {
        const response = await fetch(`${API_BASE}/current`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        currentData = data.processes;
        renderCurrentTable(data.processes);
        updateLastUpdate();
        
    } catch (error) {
        console.error('Failed to load current stats:', error);
        showError('currentTableBody', 'Failed to load data');
    }
}

// Render current stats table
function renderCurrentTable(processes) {
    const tbody = document.getElementById('currentTableBody');
    
    if (!processes || processes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = processes.map((proc, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td>${proc.pid}</td>
            <td><strong>${proc.process_name}</strong></td>
            <td>${proc.tx_formatted}</td>
            <td>${proc.rx_formatted}</td>
            <td><strong>${proc.total_formatted}</strong></td>
            <td>${formatBytes(proc.tcp_tx)}</td>
            <td>${formatBytes(proc.tcp_rx)}</td>
            <td>${formatBytes(proc.udp_tx)}</td>
            <td>${formatBytes(proc.udp_rx)}</td>
        </tr>
    `).join('');
}

// Filter process table
function filterProcessTable(query) {
    if (!currentData) return;
    
    const filtered = currentData.filter(proc => 
        proc.process_name.toLowerCase().includes(query.toLowerCase())
    );
    
    renderCurrentTable(filtered);
}

// Load historical stats
async function loadHistoryStats() {
    const hours = document.getElementById('timeWindow').value;
    
    try {
        const response = await fetch(`${API_BASE}/history/top?hours=${hours}&limit=50`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        renderHistoryTable(data.processes);
        
    } catch (error) {
        console.error('Failed to load history stats:', error);
        showError('historyTableBody', 'Failed to load data');
    }
}

// Render history table
function renderHistoryTable(processes) {
    const tbody = document.getElementById('historyTableBody');
    
    if (!processes || processes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = processes.map((proc, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td><strong>${proc.process_name}</strong></td>
            <td>${proc.total_tx_formatted}</td>
            <td>${proc.total_rx_formatted}</td>
            <td><strong>${proc.total_bandwidth_formatted}</strong></td>
            <td>${proc.record_count}</td>
        </tr>
    `).join('');
}

// Load protocol breakdown
async function loadProtocolBreakdown() {
    const hours = document.getElementById('timeWindow').value;
    
    try {
        const response = await fetch(`${API_BASE}/protocol/breakdown?hours=${hours}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        renderProtocolCards(data.protocols);
        
    } catch (error) {
        console.error('Failed to load protocol breakdown:', error);
        showError('protocolCards', 'Failed to load data');
    }
}

// Render protocol cards
function renderProtocolCards(protocols) {
    const container = document.getElementById('protocolCards');
    
    if (!protocols || Object.keys(protocols).length === 0) {
        container.innerHTML = '<div class="loading">No protocol data available</div>';
        return;
    }
    
    container.innerHTML = Object.entries(protocols).map(([protocol, data]) => `
        <div class="protocol-card">
            <h3>${protocol}</h3>
            <div class="protocol-stat">
                <span class="protocol-stat-label">Upload (TX):</span>
                <span class="protocol-stat-value">${data.tx_formatted}</span>
            </div>
            <div class="protocol-stat">
                <span class="protocol-stat-label">Download (RX):</span>
                <span class="protocol-stat-value">${data.rx_formatted}</span>
            </div>
            <div class="protocol-stat">
                <span class="protocol-stat-label">Total:</span>
                <span class="protocol-stat-value">${data.total_formatted}</span>
            </div>
        </div>
    `).join('');
}

// Load IP breakdown
async function loadIpBreakdown() {
    const hours = document.getElementById('timeWindow').value;
    const processFilter = document.getElementById('filterIpProcess').value;
    
    let url = `${API_BASE}/ip/breakdown?hours=${hours}`;
    if (processFilter) {
        url += `&process=${encodeURIComponent(processFilter)}`;
    }
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        renderIpTable(data.ips);
        
    } catch (error) {
        console.error('Failed to load IP breakdown:', error);
        showError('ipTableBody', 'Failed to load data');
    }
}

// Render IP table
function renderIpTable(ips) {
    const tbody = document.getElementById('ipTableBody');
    
    if (!ips || ips.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No IP data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = ips.map((ip, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td><strong>${ip.remote_ip}</strong></td>
            <td>${ip.process_name}</td>
            <td>${ip.total_tx_formatted}</td>
            <td>${ip.total_rx_formatted}</td>
            <td><strong>${ip.total_formatted}</strong></td>
        </tr>
    `).join('');
}

// Load bandwidth chart
async function loadBandwidthChart() {
    const hours = document.getElementById('timeWindow').value;
    const processFilter = document.getElementById('chartProcessFilter').value;
    
    let url = `${API_BASE}/timeseries?hours=${hours}&interval=5`;
    if (processFilter) {
        url += `&process=${encodeURIComponent(processFilter)}`;
    }
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        renderBandwidthChart(data.data);
        
    } catch (error) {
        console.error('Failed to load chart data:', error);
    }
}

// Render bandwidth chart
function renderBandwidthChart(data) {
    const ctx = document.getElementById('bandwidthChart');
    
    if (!data || data.length === 0) {
        ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
        return;
    }
    
    // Prepare data
    const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
    const txData = data.map(d => d.tx_bytes);
    const rxData = data.map(d => d.rx_bytes);
    
    // Destroy existing chart
    if (bandwidthChart) {
        bandwidthChart.destroy();
    }
    
    // Create new chart
    bandwidthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Upload (TX)',
                    data: txData,
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Download (RX)',
                    data: rxData,
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#f1f5f9'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatBytes(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#cbd5e1'
                    },
                    grid: {
                        color: 'rgba(71, 85, 105, 0.3)'
                    }
                },
                y: {
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return formatBytes(value);
                        }
                    },
                    grid: {
                        color: 'rgba(71, 85, 105, 0.3)'
                    }
                }
            }
        }
    });
}

// Load summary stats
async function loadSummaryStats() {
    const hours = document.getElementById('timeWindow').value;
    
    try {
        const response = await fetch(`${API_BASE}/summary?hours=${hours}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error:', data.error);
            return;
        }
        
        const stats = data.stats;
        document.getElementById('totalBandwidth').textContent = stats.total_bandwidth_formatted;
        document.getElementById('totalTx').textContent = stats.total_tx_formatted;
        document.getElementById('totalRx').textContent = stats.total_rx_formatted;
        document.getElementById('processCount').textContent = stats.process_count;
        
    } catch (error) {
        console.error('Failed to load summary stats:', error);
    }
}

// Auto-refresh functionality
function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    let countdown = 5;
    const timerElement = document.getElementById('refreshTimer');
    
    refreshInterval = setInterval(() => {
        countdown--;
        timerElement.textContent = countdown + 's';
        
        if (countdown <= 0) {
            refreshAllData();
            countdown = 5;
        }
    }, 1000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
        document.getElementById('refreshTimer').textContent = 'Paused';
    }
}

// Update last update timestamp
function updateLastUpdate() {
    const now = new Date();
    document.getElementById('lastUpdate').textContent = now.toLocaleString();
}

// Show error message
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<tr><td colspan="10" class="loading" style="color: var(--danger-color);">${message}</td></tr>`;
    }
}
