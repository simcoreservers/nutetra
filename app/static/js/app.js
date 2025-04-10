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
    
    // Add mobile-specific enhancements
    if (window.innerWidth <= 768) {
        enhanceMobileInteraction();
    }
});

/**
 * Initialize sidebar behavior
 */
function initSidebar() {
    const body = document.body;
    const sidebar = document.querySelector('.sidebar');
    
    // Create backdrop element for mobile
    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    body.appendChild(backdrop);
    
    // Set up mobile-only sidebar backdrop behavior
    // This is separate from the navigation toggle behavior
    if (window.innerWidth <= 768) {
        // Close sidebar when clicking on backdrop (mobile only)
        backdrop.addEventListener('click', function() {
            sidebar.classList.remove('active');
            backdrop.classList.remove('active');
            body.style.overflow = '';
        });
        
        // On mobile, add a handler to close the sidebar when navigating to a new page
        document.querySelectorAll('.submenu a:not(.coming-soon)').forEach(link => {
            // We only care about actual navigation links
            if (link.getAttribute('href') !== '#' && !link.getAttribute('href').startsWith('javascript')) {
                link.addEventListener('click', function() {
                    // Use setTimeout to ensure this runs after other click handlers
                    setTimeout(() => {
                        sidebar.classList.remove('active');
                        backdrop.classList.remove('active');
                        body.style.overflow = '';
                    }, 50);
                });
            }
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            // Reset things when returning to desktop size
            sidebar.classList.remove('active');
            backdrop.classList.remove('active');
            body.style.overflow = '';
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
            
            // Prevent scrolling when drawer is open on mobile
            if (window.innerWidth <= 768) {
                document.body.style.overflow = 'hidden';
            }
        });
        
        // Close notifications drawer
        closeDrawerBtn.addEventListener('click', function() {
            notificationsDrawer.classList.remove('active');
            document.body.style.overflow = '';
        });
        
        // Close drawer when clicking outside
        document.addEventListener('click', function(e) {
            if (notificationsDrawer.classList.contains('active') && 
                !notificationsDrawer.contains(e.target) && 
                !notificationBell.contains(e.target)) {
                notificationsDrawer.classList.remove('active');
                document.body.style.overflow = '';
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
        // On mobile, show a loading state
        if (window.innerWidth <= 768) {
            const statusItems = document.querySelectorAll('.status-item');
            statusItems.forEach(item => {
                item.classList.add('loading');
            });
        }
        
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
            // Remove loading state
            document.querySelectorAll('.status-item').forEach(item => {
                item.classList.remove('loading');
            });
        })
        .catch(error => {
            console.error('Error refreshing sensor data:', error);
            // Remove loading state even on error
            document.querySelectorAll('.status-item').forEach(item => {
                item.classList.remove('loading');
            });
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

/**
 * Enhance mobile interactions with better touch handling
 */
function enhanceMobileInteraction() {
    // Add double tap protection for critical buttons
    const criticalButtons = document.querySelectorAll('.btn-danger, [data-critical="true"]');
    
    criticalButtons.forEach(button => {
        let tapped = false;
        
        button.addEventListener('click', function(e) {
            if (!tapped) {
                e.preventDefault();
                tapped = true;
                this.classList.add('confirm-action');
                
                // Show confirmation text
                const originalText = this.textContent;
                this.dataset.originalText = originalText;
                this.textContent = "Tap again to confirm";
                
                // Reset after 3 seconds if not tapped again
                setTimeout(() => {
                    tapped = false;
                    this.classList.remove('confirm-action');
                    if (this.dataset.originalText) {
                        this.textContent = this.dataset.originalText;
                    }
                }, 3000);
            }
        });
    });
    
    // Improve scrolling on touch devices
    document.addEventListener('touchstart', function() {}, {passive: true});
} 