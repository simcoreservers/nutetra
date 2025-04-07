// NuTetra Controller - Chart.js Integration
// Handles rendering and updating sensor data charts

// Chart configuration objects
const chartConfigs = {
    ph: {
        borderColor: '#F4736B',
        backgroundColor: 'rgba(244, 115, 107, 0.2)',
        label: 'pH',
        yAxisMin: 4,
        yAxisMax: 8,
        targetRange: [5.5, 6.5],
        decimals: 1
    },
    ec: {
        borderColor: '#FFD166',
        backgroundColor: 'rgba(255, 209, 102, 0.2)',
        label: 'EC (μS/cm)',
        yAxisMin: 500,
        yAxisMax: 2000,
        targetRange: [1000, 1500],
        decimals: 0
    },
    temp: {
        borderColor: '#4FACFE',
        backgroundColor: 'rgba(79, 172, 254, 0.2)',
        label: 'Temperature (°C)',
        yAxisMin: 15,
        yAxisMax: 30,
        targetRange: [20, 25],
        decimals: 1
    }
};

// Chart instances
let charts = {};

/**
 * Initialize all sensor charts
 */
function initCharts() {
    createChart('ph-chart', 'ph');
    createChart('ec-chart', 'ec');
    createChart('temp-chart', 'temp');
    
    // Set the default active tab
    if (document.getElementById('sensor-tabs')) {
        document.querySelector('[data-time="24h"]').click();
    }
}

/**
 * Create a Chart.js instance for the specified sensor type
 * @param {string} canvasId - The ID of the canvas element
 * @param {string} sensorType - One of: 'ph', 'ec', 'temp'
 */
function createChart(canvasId, sensorType) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const config = chartConfigs[sensorType];
    
    charts[sensorType] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: config.label,
                data: [],
                borderColor: config.borderColor,
                backgroundColor: config.backgroundColor,
                tension: 0.3,
                borderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += parseFloat(context.raw).toFixed(config.decimals);
                            return label;
                        }
                    }
                },
                legend: {
                    display: false
                },
                annotation: {
                    annotations: {
                        targetRangeBox: {
                            type: 'box',
                            xMin: 0,
                            xMax: 100,
                            yMin: config.targetRange[0],
                            yMax: config.targetRange[1],
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            borderColor: 'rgba(75, 192, 192, 0.5)',
                            borderWidth: 1
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#9ca3af',
                        maxRotation: 0
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                y: {
                    min: config.yAxisMin,
                    max: config.yAxisMax,
                    ticks: {
                        color: '#9ca3af'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                }
            }
        }
    });
}

/**
 * Load sensor data for a specific time period
 * @param {string} timeframe - One of: '1h', '6h', '24h', '7d'
 */
function loadSensorData(timeframe) {
    fetch(`/api/sensor-history?timeframe=${timeframe}`)
        .then(response => response.json())
        .then(data => {
            updateChartData('ph', data.ph.values, data.ph.timestamps);
            updateChartData('ec', data.ec.values, data.ec.timestamps);
            updateChartData('temp', data.temp.values, data.temp.timestamps);
        })
        .catch(error => {
            console.error('Error fetching sensor data:', error);
        });
}

/**
 * Update chart data with new values
 * @param {string} sensorType - One of: 'ph', 'ec', 'temp' 
 * @param {Array} values - Array of sensor values
 * @param {Array} timestamps - Array of timestamps
 */
function updateChartData(sensorType, values, timestamps) {
    const chart = charts[sensorType];
    if (!chart) return;
    
    // Format timestamps based on length
    const formattedLabels = formatTimestamps(timestamps);
    
    chart.data.labels = formattedLabels;
    chart.data.datasets[0].data = values;
    
    // Update x-axis annotation
    if (chart.options.plugins.annotation?.annotations?.targetRangeBox) {
        chart.options.plugins.annotation.annotations.targetRangeBox.xMax = values.length - 1;
    }
    
    chart.update();
}

/**
 * Format timestamps based on data density
 * @param {Array} timestamps - Array of ISO timestamp strings
 * @returns {Array} - Formatted time strings
 */
function formatTimestamps(timestamps) {
    // For intervals less than 24 hours, show only time
    // For intervals >= 24 hours, show date and time
    const isShortInterval = timestamps.length > 0 &&
        (new Date(timestamps[timestamps.length - 1]) - new Date(timestamps[0])) < 24 * 60 * 60 * 1000;
        
    return timestamps.map(ts => {
        const date = new Date(ts);
        if (isShortInterval) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + 
                   ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    });
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.chart-container')) {
        initCharts();
    }
}); 