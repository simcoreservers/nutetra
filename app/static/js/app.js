/**
 * NuTetra Controller - Main Application JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initSidebar();
    initNotifications();
    initFlashMessages();
    
    // Initialize custom elements/widgets if present
    if (document.querySelector('.chart-tabs')) {
        initChartTabs();
    }
    
    // Setup interval refresh if enabled
    setupDataRefresh();
});

/**
 * Initialize sidebar behavior
 */
function initSidebar() {
    // Toggle sidebar on mobile
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('active');
        });
    }
    
    // Setup submenu toggles
    const menuItems = document.querySelectorAll('.sidebar-nav > ul > li');
    menuItems.forEach(item => {
        const submenu = item.querySelector('.submenu');
        if (submenu) {
            item.querySelector('a').addEventListener('click', function(e) {
                e.preventDefault();
                item.classList.toggle('active');
            });
        }
    });
    
    // Close sidebar when clicking outside on mobile
    document.querySelector('.main-content').addEventListener('click', function() {
        if (window.innerWidth <= 768) {
            document.querySelector('.sidebar').classList.remove('active');
        }
    });
}

/**
 * Initialize notification system
 */
function initNotifications() {
    const notificationBell = document.querySelector('.notifications-bell');
    const notificationsDrawer = document.getElementById('notifications-drawer');
    const closeDrawerBtn = document.querySelector('.close-drawer');
    
    if (notificationBell && notificationsDrawer) {
        // Open notifications drawer when clicking the bell
        notificationBell.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationsDrawer.classList.add('active');
        });
        
        // Close notifications drawer
        closeDrawerBtn.addEventListener('click', function() {
            notificationsDrawer.classList.remove('active');
        });
        
        // Close drawer when clicking outside
        document.addEventListener('click', function(e) {
            if (notificationsDrawer.classList.contains('active') && 
                !notificationsDrawer.contains(e.target) && 
                !notificationBell.contains(e.target)) {
                notificationsDrawer.classList.remove('active');
            }
        });
        
        // Reset notification count when opening drawer
        notificationBell.addEventListener('click', function() {
            document.getElementById('notification-count').textContent = '0';
            document.getElementById('notification-count').style.display = 'none';
        });
    }
}

/**
 * Initialize flash message behavior
 */
function initFlashMessages() {
    document.querySelectorAll('.alert .close-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    });
    
    // Auto-hide flash messages after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    }, 5000);
}

/**
 * Initialize chart tabs behavior
 */
function initChartTabs() {
    const tabs = document.querySelectorAll('.chart-tab');
    const panels = document.querySelectorAll('.chart-panel');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Set active tab
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding panel
            const panelId = this.getAttribute('data-chart') + '-chart-panel';
            panels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === panelId) {
                    panel.classList.add('active');
                }
            });
        });
    });
}

/**
 * Set up automatic data refresh
 */
function setupDataRefresh() {
    // Check if refresh interval is set in meta tags
    const refreshMeta = document.querySelector('meta[name="refresh-interval"]');
    const refreshInterval = refreshMeta ? parseInt(refreshMeta.getAttribute('content')) * 1000 : 10000;
    
    if (refreshInterval > 0) {
        // Set up interval to refresh data
        setInterval(() => {
            refreshSensorData();
        }, refreshInterval);
    }
}

/**
 * Refresh sensor data via API
 */
function refreshSensorData() {
    // Only refresh if we have sensor display elements on the page
    if (document.getElementById('ph-value') || document.getElementById('ec-value') || document.getElementById('temp-value')) {
        fetch('/api/sensors/read_now', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSensorDisplays(data.data);
            }
        })
        .catch(error => {
            console.error('Error refreshing sensor data:', error);
        });
    }
}

/**
 * Update sensor displays with new data
 */
function updateSensorDisplays(data) {
    // Update pH value if present
    const phDisplay = document.getElementById('ph-value');
    if (phDisplay && data.ph !== null) {
        phDisplay.textContent = parseFloat(data.ph).toFixed(2);
        // Update container class based on target range
        updateReadingCardStatus('ph', data.ph);
    }
    
    // Update EC value if present
    const ecDisplay = document.getElementById('ec-value');
    if (ecDisplay && data.ec !== null) {
        ecDisplay.textContent = parseFloat(data.ec).toFixed(2);
        // Update container class based on target range
        updateReadingCardStatus('ec', data.ec);
    }
    
    // Update temperature value if present
    const tempDisplay = document.getElementById('temp-value');
    if (tempDisplay && data.temp !== null) {
        tempDisplay.textContent = parseFloat(data.temp).toFixed(1) + '°C';
        // Update container class based on target range
        updateReadingCardStatus('temp', data.temp);
    }
    
    // Update status indicators in the header
    updateStatusIndicators(data);
}

/**
 * Update reading card status (alert or normal)
 */
function updateReadingCardStatus(sensorType, value) {
    // Find the reading card for this sensor
    const cards = document.querySelectorAll('.reading-card');
    let card = null;
    
    cards.forEach(c => {
        if (c.querySelector('h4').textContent.toLowerCase().includes(sensorType)) {
            card = c;
        }
    });
    
    if (!card) return;
    
    // Get target range from the card
    const rangeText = card.querySelector('.reading-range').textContent;
    const matches = rangeText.match(/Target: ([\d\.]+) - ([\d\.]+)/);
    
    if (matches && matches.length === 3) {
        const min = parseFloat(matches[1]);
        const max = parseFloat(matches[2]);
        
        // Update card status
        if (value < min || value > max) {
            card.classList.add('alert');
        } else {
            card.classList.remove('alert');
        }
    }
}

/**
 * Update status indicators in the header
 */
function updateStatusIndicators(data) {
    const indicators = document.querySelectorAll('.status-item');
    
    indicators.forEach(indicator => {
        const label = indicator.querySelector('.label').textContent.toLowerCase();
        const valueDisplay = indicator.querySelector('.value');
        
        // Update the value
        if (label === 'ph' && data.ph !== null) {
            valueDisplay.textContent = parseFloat(data.ph).toFixed(2);
            // Check if it's out of range
            updateStatusAlert('ph', indicator, data.ph);
        } else if (label === 'ec' && data.ec !== null) {
            valueDisplay.textContent = parseFloat(data.ec).toFixed(2);
            // Check if it's out of range
            updateStatusAlert('ec', indicator, data.ec);
        } else if (label === 'temp' && data.temp !== null) {
            valueDisplay.textContent = parseFloat(data.temp).toFixed(1) + '°C';
            // Check if it's out of range
            updateStatusAlert('temp', indicator, data.temp);
        }
    });
}

/**
 * Update status indicator alert state
 */
function updateStatusAlert(sensorType, indicator, value) {
    // Get settings from meta tag
    const settingsMeta = document.querySelector(`meta[name="${sensorType}-settings"]`);
    
    if (settingsMeta) {
        try {
            const settings = JSON.parse(settingsMeta.getAttribute('content'));
            if (value < settings.min || value > settings.max) {
                indicator.classList.add('alert');
            } else {
                indicator.classList.remove('alert');
            }
        } catch (e) {
            console.error('Error parsing settings meta tag:', e);
        }
    } else {
        // Fall back to using the dataset on the element itself
        const min = parseFloat(indicator.dataset.min);
        const max = parseFloat(indicator.dataset.max);
        
        if (!isNaN(min) && !isNaN(max)) {
            if (value < min || value > max) {
                indicator.classList.add('alert');
            } else {
                indicator.classList.remove('alert');
            }
        }
    }
} 