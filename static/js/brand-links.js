/**
 * Brand Links JavaScript
 * Automatically adds data-text attributes to links for the masking effect
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find all links that don't have data-text attribute
    const links = document.querySelectorAll('a:not([data-text]):not(.no-link-style):not(.btn):not(.button):not([class*="btn"])');

    links.forEach(function(link) {
        // Get the text content of the link
        const textContent = link.textContent.trim();

        // Only add data-text if the link has text content
        if (textContent) {
            link.setAttribute('data-text', textContent);
        }
    });

    // Note: CSS already handles ::after pseudo-element via attr(data-text)
    // No dynamic style creation needed - avoids CSP violations
});
