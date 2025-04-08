/**
 * NuTetra Controller - Sensors Page JavaScript
 * Handles the sensor management UI and real-time updates for sensor status
 */

document.addEventListener('DOMContentLoaded', function() {
    // Make sure this file only runs on the sensor page
    if (document.querySelector('.reading-card')) {
        initSensorPage();
    }
});

/**
 * Initialize the sensor page components
 */
function initSensorPage() {
    console.log("Initializing sensor page...");
    
    // Force all sensor cards to stay visible - once is enough
    forceSensorCardsVisible();
    
    // Initialize the settings form
    initSettingsForm();
}

/**
 * Force sensor cards to always be visible regardless of their state
 * Applied once during page load to ensure cards remain visible
 */
function forceSensorCardsVisible() {
    const sensorCards = document.querySelectorAll('.reading-card');
    
    sensorCards.forEach(card => {
        // Keep styles simple to avoid triggering too many repaints
        card.style.display = 'flex';
        card.style.opacity = '1';
        card.style.visibility = 'visible';
    });
}

/**
 * Socket.IO update handler (for custom implementations)
 */
function handleSensorUpdate(data) {
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
    
    // Update card values
    updateSensorDisplay('ph', phValue, sensorStatus.ph);
    updateSensorDisplay('ec', ecValue, sensorStatus.ec);
    updateSensorDisplay('temp', tempValue, sensorStatus.temp);
}

/**
 * Update sensor display values and status
 */
function updateSensorDisplay(sensorType, value, status) {
    // Get card elements
    const card = document.getElementById(`${sensorType}-sensor-card`);
    if (!card) return;
    
    // Update reading value
    const valueElement = document.getElementById(`${sensorType}-value`);
    if (valueElement) {
        if (value !== null) {
            // Format the value based on sensor type
            if (sensorType === 'ph') {
                valueElement.textContent = parseFloat(value).toFixed(2);
            } else if (sensorType === 'ec') {
                valueElement.textContent = parseFloat(value).toFixed(0) + ' μS/cm';
            } else if (sensorType === 'temp') {
                valueElement.textContent = parseFloat(value).toFixed(1) + ' °C';
            }
        } else {
            valueElement.textContent = 'N/A';
        }
    }
    
    // Update status
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