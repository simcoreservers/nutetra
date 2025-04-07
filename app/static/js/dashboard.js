/**
 * NuTetra Controller - Dashboard JavaScript
 * Handles real-time updates and interaction for the dashboard
 */

// Initialize Socket.IO connection
let socket;

// Chart instances (defined globally for access from socket events)
let phChart, ecChart, tempChart;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});

/**
 * Initialize the dashboard components
 */
function initDashboard() {
    // Initialize Socket.IO
    initSocketIO();
    
    // Initialize dashboard components
    initSensorCharts();
    initQuickActions();
    initRecentActivity();
}

/**
 * Initialize Socket.IO connection and event handlers
 */
function initSocketIO() {
    // Connect to Socket.IO server
    socket = io();
    
    // Connection events
    socket.on('connect', function() {
        console.log('Connected to NuTetra Controller');
        
        // Subscribe to channels
        socket.emit('subscribe', { channel: 'sensors' });
        socket.emit('subscribe', { channel: 'notifications' });
        socket.emit('subscribe', { channel: 'dosing' });
        socket.emit('subscribe', { channel: 'system' });
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from NuTetra Controller');
    });
    
    // Sensor update event
    socket.on('sensor_update', function(data) {
        updateSensorReadings(data);
        updateSensorCharts(data);
    });
    
    // Notification event
    socket.on('new_notification', function(data) {
        addNotification(data);
    });
    
    // Dosing event
    socket.on('dosing_event', function(data) {
        addDosingEvent(data);
    });
    
    // System alert event
    socket.on('system_alert', function(data) {
        showSystemAlert(data);
    });
}

/**
 * Initialize sensor charts
 */
function initSensorCharts() {
    // Initialize the charts if present
    if (document.getElementById('ph-chart')) {
        createChart('ph-chart', 'ph');
    }
    
    if (document.getElementById('ec-chart')) {
        createChart('ec-chart', 'ec');
    }
    
    if (document.getElementById('temp-chart')) {
        createChart('temp-chart', 'temp');
    }
    
    // Add event listeners to timeframe buttons
    const timeframeButtons = document.querySelectorAll('[data-time]');
    timeframeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const timeframe = this.getAttribute('data-time');
            
            // Remove active class from all buttons
            timeframeButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Load chart data for the selected timeframe
            loadSensorData(timeframe);
        });
    });
    
    // Default to 24 hour view
    if (timeframeButtons.length > 0) {
        document.querySelector('[data-time="24h"]').click();
    }
}

/**
 * Initialize quick actions
 */
function initQuickActions() {
    // Toggle auto-dosing
    const autodosingToggle = document.getElementById('autodosing-toggle');
    if (autodosingToggle) {
        autodosingToggle.addEventListener('change', function() {
            fetch('/api/dosing/auto', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    enabled: this.checked
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    showToast('Auto-dosing ' + (this.checked ? 'enabled' : 'disabled'), 'success');
                } else {
                    showToast('Failed to update auto-dosing', 'error');
                    this.checked = !this.checked; // Revert the toggle
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Failed to update auto-dosing', 'error');
                this.checked = !this.checked; // Revert the toggle
            });
        });
    }
    
    // Manual dosing button
    const manualDoseBtn = document.getElementById('manual-dose-btn');
    if (manualDoseBtn) {
        manualDoseBtn.addEventListener('click', function() {
            // Load pumps and show the manual dosing modal
            loadPumps();
            
            // Show the modal
            const modal = document.getElementById('manual-dose-modal');
            if (modal) {
                modal.classList.add('active');
            }
        });
    }
    
    // Close modal button
    const closeModalBtn = document.querySelector('.modal-close');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function() {
            const modal = document.getElementById('manual-dose-modal');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    }
    
    // Export data buttons
    const exportCsvBtn = document.getElementById('export-csv-btn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            window.location.href = '/api/export?format=csv';
        });
    }
    
    const exportJsonBtn = document.getElementById('export-json-btn');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', function() {
            window.location.href = '/api/export?format=json';
        });
    }
}

/**
 * Load available pumps for manual dosing
 */
function loadPumps() {
    fetch('/api/pumps')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // Clear existing pumps
                const pumpContainer = document.getElementById('pump-controls');
                if (pumpContainer) {
                    pumpContainer.innerHTML = '';
                    
                    // Add each pump
                    data.pumps.forEach(pump => {
                        if (pump.is_enabled) {
                            const pumpControl = document.createElement('div');
                            pumpControl.classList.add('pump-control');
                            pumpControl.innerHTML = `
                                <h4>${pump.name}</h4>
                                <div class="dose-control">
                                    <input type="number" id="dose-${pump.id}" min="1" max="100" value="10" class="dose-amount">
                                    <span class="unit">ml</span>
                                    <button class="dose-btn" data-pump-id="${pump.id}">Dose</button>
                                </div>
                            `;
                            pumpContainer.appendChild(pumpControl);
                            
                            // Add event listener to the dose button
                            const doseBtn = pumpControl.querySelector('.dose-btn');
                            doseBtn.addEventListener('click', function() {
                                const pumpId = this.getAttribute('data-pump-id');
                                const amountEl = document.getElementById(`dose-${pumpId}`);
                                const amount = parseFloat(amountEl.value);
                                
                                if (isNaN(amount) || amount <= 0) {
                                    showToast('Please enter a valid amount', 'error');
                                    return;
                                }
                                
                                // Disable button to prevent multiple doses
                                this.disabled = true;
                                this.textContent = 'Dosing...';
                                
                                // Send the dosing request
                                manualDose(pumpId, amount, this);
                            });
                        }
                    });
                    
                    // If no enabled pumps, show message
                    if (data.pumps.filter(p => p.is_enabled).length === 0) {
                        pumpContainer.innerHTML = '<p>No enabled pumps available for dosing</p>';
                    }
                }
            } else {
                showToast('Failed to load pumps', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Failed to load pumps', 'error');
        });
}

/**
 * Perform manual dosing
 */
function manualDose(pumpId, amount, button) {
    fetch('/api/dose', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            pump_id: pumpId,
            amount_ml: amount
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showToast(data.message, 'success');
            
            // Close the modal after successful dosing
            setTimeout(function() {
                const modal = document.getElementById('manual-dose-modal');
                if (modal) {
                    modal.classList.remove('active');
                }
            }, 1500);
        } else {
            showToast(data.message || 'Failed to dose', 'error');
        }
        
        // Re-enable the button
        button.disabled = false;
        button.textContent = 'Dose';
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Failed to dose', 'error');
        
        // Re-enable the button
        button.disabled = false;
        button.textContent = 'Dose';
    });
}

/**
 * Initialize recent activity panel
 */
function initRecentActivity() {
    // Load recent dosing events
    fetch('/api/dosing/recent')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                updateRecentActivity(data.events);
            }
        })
        .catch(error => {
            console.error('Error loading recent activity:', error);
        });
}

/**
 * Update recent activity with dosing events
 */
function updateRecentActivity(events) {
    const activityList = document.getElementById('recent-activity-list');
    if (!activityList) return;
    
    // Clear existing items
    activityList.innerHTML = '';
    
    // Add new events
    events.forEach(event => {
        const listItem = document.createElement('li');
        listItem.classList.add('activity-item');
        
        // Format timestamp
        const eventDate = new Date(event.timestamp);
        const formattedDate = eventDate.toLocaleString();
        
        listItem.innerHTML = `
            <div class="activity-icon ${event.type}">
                <i class="fas fa-tint"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${event.pump_name}: ${event.amount_ml}ml</div>
                <div class="activity-time">${formattedDate}</div>
            </div>
        `;
        
        activityList.appendChild(listItem);
    });
    
    // Show message if no events
    if (events.length === 0) {
        const listItem = document.createElement('li');
        listItem.textContent = 'No recent activity';
        activityList.appendChild(listItem);
    }
}

/**
 * Add a new dosing event to the recent activity
 */
function addDosingEvent(event) {
    fetch('/api/dosing/recent')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                updateRecentActivity(data.events);
            }
        })
        .catch(error => {
            console.error('Error updating recent activity:', error);
        });
}

/**
 * Update sensor readings display
 */
function updateSensorReadings(data) {
    // Update pH reading
    const phReading = document.getElementById('ph-reading');
    if (phReading) phReading.textContent = data.ph.toFixed(1);
    
    // Update EC reading
    const ecReading = document.getElementById('ec-reading');
    if (ecReading) ecReading.textContent = data.ec.toFixed(0);
    
    // Update temperature reading
    const tempReading = document.getElementById('temp-reading');
    if (tempReading) tempReading.textContent = data.temp.toFixed(1);
    
    // Update last updated timestamp
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) {
        const date = new Date(data.timestamp);
        lastUpdated.textContent = date.toLocaleTimeString();
    }
    
    // Update status indicators
    updateStatusIndicators();
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.classList.add('toast', type);
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${getIconForToastType(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close"><i class="fas fa-times"></i></button>
    `;
    
    // Add to document
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        // Create container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
        container.appendChild(toast);
    } else {
        toastContainer.appendChild(toast);
    }
    
    // Add close button handler
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', function() {
        toast.classList.add('closing');
        setTimeout(() => {
            toast.remove();
        }, 300);
    });
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        if (document.body.contains(toast)) {
            toast.classList.add('closing');
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    toast.remove();
                }
            }, 300);
        }
    }, 4000);
}

/**
 * Get appropriate icon for toast notification type
 */
function getIconForToastType(type) {
    switch (type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        case 'info':
        default: return 'fa-info-circle';
    }
}

/**
 * Show system alert
 */
function showSystemAlert(data) {
    showToast(data.message, data.level);
} 