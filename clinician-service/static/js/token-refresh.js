// Token refresh functionality
const TOKEN_REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutes

function getAccessToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function setTokens(access, refresh) {
    localStorage.setItem('access_token', access);
    if (refresh) {
        localStorage.setItem('refresh_token', refresh);
    }
    // Set cookie for server-side rendering
    document.cookie = `access_token=${access}; path=/; max-age=900`;
}

function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        window.location.href = '/login/';
        return false;
    }

    try {
        const response = await fetch('/api/clinician/auth/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            setTokens(data.access);
            return true;
        } else {
            clearTokens();
            window.location.href = '/login/';
            return false;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

// Check if user is active and refresh if needed
async function refreshIfActive() {
    const accessToken = getAccessToken();
    if (!accessToken) {
        return false;
    }

    try {
        const response = await fetch('/api/clinician/auth/refresh-if-active/', {
            method: 'POST',
            credentials: 'include', // Include cookies
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (data.active) {
            if (data.needs_refresh && data.access) {
                setTokens(data.access);
            }
            return true;
        } else {
            clearTokens();
            window.location.href = '/login/';
            return false;
        }
    } catch (error) {
        console.error('Activity check failed:', error);
        return false;
    }
}

// Set up automatic token refresh
let refreshInterval;

function startTokenRefresh() {
    // Clear any existing interval
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // Set up new interval
    refreshInterval = setInterval(() => {
        refreshIfActive();
    }, TOKEN_REFRESH_INTERVAL);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const accessToken = getAccessToken();
    if (accessToken) {
        // Set cookie for server-side rendering
        document.cookie = `access_token=${accessToken}; path=/; max-age=900`;
        startTokenRefresh();
    }
});

// Export functions for use in other scripts
window.tokenUtils = {
    getAccessToken,
    getRefreshToken,
    setTokens,
    clearTokens,
    refreshAccessToken,
    refreshIfActive,
    startTokenRefresh
};