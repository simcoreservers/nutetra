/**
 * NuTetra Controller - Sensors Page JavaScript
 * Handles the sensor management UI and real-time updates for sensor status
 */

document.addEventListener('DOMContentLoaded', function() {
    initSensorPage();
});

/**
 * Initialize the sensor page components
 */
function initSensorPage() {
    // Initialize Socket.IO for real-time updates
    initSocketIO();
    
    // Initialize the sensor cards to ensure they're always visible
    ensureSensorCardsVisible();
    
    // Add event listeners for settings form
    initSettingsForm();
}

/**
 * Initialize Socket.IO connection and event handlers
 */
function initSocketIO() {
    // Check if socket is already defined (might be defined in global scope)
    if (typeof socket === 'undefined') {
        // Connect to Socket.IO server
        socket = io();
        
        // Connection events
        socket.on('connect', function() {
            console.log('Connected to NuTetra Controller');
            
            // Subscribe to sensors channel
            socket.emit('subscribe', { channel: 'sensors' });
        });
    }
    
    // Sensor update event
    socket.on('sensor_update', function(data) {
        updateSensorReadings(data);
    });
}

/**
 * Make sure all sensor cards are visible, regardless of their status
 */
function ensureSensorCardsVisible() {
    const sensorCards = document.querySelectorAll('.reading-card');
    
    // Ensure all cards have display: flex and are visible
    sensorCards.forEach(card => {
        // Add inline styles to override any CSS that might hide the card
        card.style.display = 'flex';
        card.style.opacity = '1';
        card.style.visibility = 'visible';
        
        // Monitor for DOM changes that might affect visibility
        const observer = new MutationObserver(function(mutations) {
            // Force card to be visible regardless of class changes
            card.style.display = 'flex';
            card.style.opacity = '1';
            card.style.visibility = 'visible';
        });
        
        // Observe class changes that might trigger CSS hiding the card
        observer.observe(card, { 
            attributes: true, 
            attributeFilter: ['class'] 
        });
    });
}

/**
 * Update sensor readings and statuses in the UI
 */
function updateSensorReadings(data) {
    // Extract values or set to null if not present
    const phValue = data.ph !== undefined ? data.ph : null;
    const ecValue = data.ec !== undefined ? data.ec : null;
    const tempValue = data.temp !== undefined ? data.temp : null;
    
    // Extract sensor statuses
    const sensorStatus = data.sensor_status || {
        ph: phValue === null ? 'disconnected' : 'connected',
        ec: ecValue === null ? 'disconnected' : 'connected',
        temp: tempValue === null ? 'disconnected' : 'connected'
    };
    
    // Update sensor cards with new data
    updateSensorCard('ph', phValue, sensorStatus.ph);
    updateSensorCard('ec', ecValue, sensorStatus.ec);
    updateSensorCard('temp', tempValue, sensorStatus.temp);
}

/**
 * Update a specific sensor card with new data
 */
function updateSensorCard(sensorType, value, status) {
    // Find the card
    const cards = document.querySelectorAll('.reading-card');
    let card = null;
    
    cards.forEach(c => {
        if (c.querySelector('h4').textContent.toLowerCase().includes(sensorType)) {
            card = c;
        }
    });
    
    if (!card) return;
    
    // Update sensor status
    const statusText = card.querySelector('.status-text');
    const statusIndicator = card.querySelector('.status-indicator');
    
    if (statusText) {
        statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
    
    if (statusIndicator) {
        if (status === 'connected') {
            statusIndicator.classList.add('success');
            statusIndicator.classList.remove('danger');
        } else {
            statusIndicator.classList.add('danger');
            statusIndicator.classList.remove('success');
        }
    }
    
    // Update reading value
    const readingValue = card.querySelector('.reading-value');
    if (readingValue) {
        if (value !== null) {
            // Format the value based on sensor type
            if (sensorType === 'ph') {
                readingValue.textContent = parseFloat(value).toFixed(2);
            } else if (sensorType === 'ec') {
                readingValue.textContent = parseFloat(value).toFixed(0) + ' μS/cm';
            } else if (sensorType === 'temp') {
                readingValue.textContent = parseFloat(value).toFixed(1) + ' °C';
            }
        } else {
            readingValue.textContent = 'N/A';
        }
    }
    
    // Update card alert status
    if (status === 'connected') {
        // Check if value is in target range
        const rangeText = card.querySelector('.reading-range').textContent;
        const matches = rangeText.match(/Target: ([\d\.]+) - ([\d\.]+)/);
        
        if (matches && matches.length === 3 && value !== null) {
            const min = parseFloat(matches[1]);
            const max = parseFloat(matches[2]);
            
            if (value < min || value > max) {
                card.classList.add('alert');
            } else {
                card.classList.remove('alert');
            }
        }
    } else {
        // For disconnected sensors, keep the alert class
        card.classList.add('alert');
    }
    
    // Always make sure card remains visible
    card.style.display = 'flex';
    card.style.opacity = '1';
    card.style.visibility = 'visible';
}

/**
 * Initialize settings form
 */
function initSettingsForm() {
    const settingsForm = document.querySelector('form[action*="update_settings"]');
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show saving indicator
            const saveButton = this.querySelector('button[type="submit"]');
            const originalText = saveButton.textContent;
            saveButton.textContent = 'Saving...';
            
            fetch(this.action, {
                method: 'POST',
                body: new FormData(this),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    // Show success message
                    showToast('Settings saved successfully', 'success');
                } else {
                    // Show error message
                    showToast('Failed to save settings: ' + data.message, 'error');
                }
            })
            .catch(error => {
                showToast('An error occurred while saving settings', 'error');
                console.error('Error saving settings:', error);
            })
            .finally(() => {
                // Restore button text
                saveButton.textContent = originalText;
            });
        });
    }
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info') {
    // Check if the function exists in the global scope
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        // Simple alert fallback
        alert(message);
    }
} 