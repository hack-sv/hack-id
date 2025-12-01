// CSRF Token Helper Functions for Admin Panel

// Get CSRF token safely with validation
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta || !meta.content) {
        console.error('CSRF token meta tag is missing or empty');
        return null;
    }
    return meta.content;
}

// Show session expired modal
function showSessionExpiredModal() {
    // Check if modal already exists
    let overlay = document.getElementById('session-expired-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
        return;
    }

    // Create modal overlay
    const modalHTML = `
        <div id="session-expired-overlay" class="session-expired-overlay">
            <div id="session-expired-modal" class="session-expired-modal">
                <h2>⚠️ Session Expired</h2>
                <p>
                    Your session has expired or the CSRF token is invalid.<br>
                    Please reload the page to continue.
                </p>
                <button onclick="window.location.reload()">Reload Page</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// Enhanced fetch wrapper with CSRF and 403 error handling
async function secureFetch(url, options = {}) {
    // Check if this is a request that needs CSRF token (non-GET requests)
    const method = options.method ? options.method.toUpperCase() : 'GET';
    const needsCSRF = method !== 'GET';

    if (needsCSRF) {
        const token = getCSRFToken();
        if (!token) {
            showSessionExpiredModal();
            throw new Error('CSRF token is missing');
        }

        // Add CSRF token to headers
        options.headers = options.headers || {};
        options.headers['X-CSRFToken'] = token;
    }

    try {
        const response = await fetch(url, options);

        // Handle 403 Forbidden (likely CSRF failure or permission issue)
        if (response.status === 403) {
            const contentType = response.headers.get('content-type');

            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();

                // Check if error message indicates session/CSRF issue
                const errorMsg = (data.error || '').toLowerCase();
                if (errorMsg.includes('csrf') ||
                    errorMsg.includes('session') ||
                    errorMsg.includes('expired') ||
                    errorMsg.includes('not authenticated')) {
                    showSessionExpiredModal();
                    throw new Error('Session expired');
                }

                // Return response for other 403 errors (permission denied, etc.)
                return response;
            } else {
                // Non-JSON 403 response, likely CSRF failure
                showSessionExpiredModal();
                throw new Error('Session expired or CSRF token invalid');
            }
        }

        return response;
    } catch (error) {
        // Re-throw session/CSRF errors (already handled with modal)
        if (error.message === 'Session expired' || error.message === 'CSRF token is missing') {
            throw error;
        }
        // Re-throw other errors (network, etc.)
        throw error;
    }
}
