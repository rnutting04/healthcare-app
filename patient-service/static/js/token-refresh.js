/**
 * Activity-based token refresh handler
 * Include this script in all pages that need JWT token refresh based on user activity
 */
(function() {
    'use strict';
    
    let refreshTimer = null;
    const REFRESH_INTERVAL = 8 * 60 * 1000; // 8 minutes - check for refresh
    const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click', 'mousemove'];
    let lastActivity = Date.now();
    
    // Track user activity
    function updateActivity() {
        lastActivity = Date.now();
    }
    
    // Add activity listeners
    ACTIVITY_EVENTS.forEach(event => {
        document.addEventListener(event, updateActivity, { passive: true, capture: true });
    });
    
    // Function to refresh token
    async function attemptTokenRefresh() {
        try {
            const response = await fetch('/api/auth/refresh-if-active/', {
                method: 'POST',
                credentials: 'include', // Include cookies
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.refreshed) {
                console.log('Token refreshed successfully');
                // Update any auth headers if your app uses them
                if (window.updateAuthHeaders && typeof window.updateAuthHeaders === 'function') {
                    window.updateAuthHeaders(data.access_token);
                }
            } else if (response.status === 401) {
                console.warn('Token expired or invalid, redirecting to login');
                // Clear any stored auth data
                window.location.href = '/login?expired=true';
            }
            
            return response.ok;
        } catch (error) {
            // Don't log abort errors - these happen when the page is navigating away
            if (error.name !== 'AbortError') {
                console.error('Error refreshing token:', error);
            }
            return false;
        }
    }
    
    // Check and refresh token periodically
    function startTokenRefresh() {
        // Clear any existing timer
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
        
        // Set up periodic refresh check
        refreshTimer = setInterval(() => {
            const timeSinceActivity = Date.now() - lastActivity;
            
            // Only refresh if user has been active in the last 15 minutes
            if (timeSinceActivity < 15 * 60 * 1000) {
                attemptTokenRefresh();
            } else {
                console.log('User inactive for >15 minutes, skipping token refresh');
            }
        }, REFRESH_INTERVAL);
        
        // Also attempt an initial refresh after 8 minutes
        setTimeout(() => {
            if (Date.now() - lastActivity < 15 * 60 * 1000) {
                attemptTokenRefresh();
            }
        }, REFRESH_INTERVAL);
    }
    
    // Start the refresh cycle
    startTokenRefresh();
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
    });
    
    // Expose refresh function globally if needed
    window.refreshAuthToken = attemptTokenRefresh;
})();