// Dashboard JavaScript functionality

// Reveal/Hide functionality
document.querySelectorAll(".reveal-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
        const target = this.getAttribute("data-target");
        const section = this.closest(".dashboard-section");
        const values = section.querySelectorAll(".info-value[data-full]");

        if (this.textContent.trim() === "Reveal") {
            // Show full data
            values.forEach((value) => {
                value.textContent = value.getAttribute("data-full");
            });
            this.textContent = "Hide";
        } else {
            // Show censored data
            values.forEach((value) => {
                const type = value.getAttribute("data-type");
                const full = value.getAttribute("data-full");
                value.textContent = censorData(full, type);
            });
            this.textContent = "Reveal";
        }
    });
});

// Delete data functionality
const deleteCheckbox = document.getElementById("delete-confirm");
const deleteBtn = document.getElementById("delete-btn");

if (deleteCheckbox && deleteBtn) {
    // Function to update button state
    function updateDeleteButtonState() {
        if (deleteCheckbox.checked) {
            deleteBtn.disabled = false;
            deleteBtn.style.opacity = "1";
            deleteBtn.style.cursor = "pointer";
        } else {
            deleteBtn.disabled = true;
            deleteBtn.style.opacity = "0.5";
            deleteBtn.style.cursor = "not-allowed";
        }
    }

    // Initialize button state
    updateDeleteButtonState();

    // Update button state when checkbox changes
    deleteCheckbox.addEventListener("change", updateDeleteButtonState);

    deleteBtn.addEventListener("click", function (e) {
        // If button is disabled, prevent any action
        if (this.disabled) {
            e.preventDefault();
            return;
        }

        if (
            confirm(
                "Are you absolutely sure? This action cannot be undone and will permanently delete all your data."
            )
        ) {
            // Create a form and submit to the direct deletion endpoint
            const form = document.createElement("form");
            form.method = "POST";
            form.action = "/delete-dashboard";

            // Add CSRF token if available
            const csrfToken = document.querySelector('meta[name="csrf-token"]');
            if (csrfToken) {
                const csrfInput = document.createElement("input");
                csrfInput.type = "hidden";
                csrfInput.name = "csrf_token";
                csrfInput.value = csrfToken.getAttribute("content");
                form.appendChild(csrfInput);
            }

            document.body.appendChild(form);
            form.submit();
        }
    });
}

// Discord unlink functionality
const unlinkBtn = document.querySelector(".unlink-btn");
if (unlinkBtn) {
    unlinkBtn.addEventListener("click", async function () {
        if (
            confirm(
                "Are you sure you want to unlink your Discord account?\n\n" +
                    "This will:\n" +
                    "• Remove your access to event-specific Discord channels\n" +
                    "• Remove your event roles\n" +
                    "• You can re-link anytime using /verify in Discord"
            )
        ) {
            try {
                // Show loading state
                const originalText = this.textContent;
                this.textContent = "Unlinking...";
                this.disabled = true;

                const response = await fetch("/dashboard/discord/unlink", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken(),
                    },
                    body: JSON.stringify({
                        user_email: getCurrentUserEmail(),
                    }),
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    // Update UI to show unlinked state
                    const discordSection = this.closest(".dashboard-section");
                    const discordInfo =
                        discordSection.querySelector(".discord-info");

                    discordInfo.innerHTML = `
                        <span class="not-connected">Not connected</span>
                        <a href="https://discord.com/invite/32BsffvEf4" target="_blank" class="join-discord-btn">Join Discord</a>
                    `;

                    // Show success message
                    showNotification(
                        "✅ Discord account unlinked successfully!",
                        "success"
                    );
                } else {
                    // Show error message
                    const errorMsg =
                        result.error || "Failed to unlink Discord account";
                    showNotification(`❌ ${errorMsg}`, "error");

                    // Restore button state
                    this.textContent = originalText;
                    this.disabled = false;
                }
            } catch (error) {
                console.error("Error unlinking Discord account:", error);
                showNotification(
                    "❌ An error occurred while unlinking your Discord account",
                    "error"
                );

                // Restore button state
                this.textContent = originalText;
                this.disabled = false;
            }
        }
    });
}

// Helper function to get CSRF token
function getCSRFToken() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    return csrfToken ? csrfToken.getAttribute("content") : "";
}

// Helper function to get current user email (from dashboard data)
function getCurrentUserEmail() {
    // Try to extract from profile section
    const emailElement = document.querySelector(
        '.info-value[data-type="email"]'
    );
    if (emailElement) {
        return (
            emailElement.getAttribute("data-full") || emailElement.textContent
        );
    }
    return null;
}

// Helper function to show notifications
function showNotification(message, type = "info") {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${
            type === "success"
                ? "#d4edda"
                : type === "error"
                ? "#f8d7da"
                : "#d1ecf1"
        };
        color: ${
            type === "success"
                ? "#155724"
                : type === "error"
                ? "#721c24"
                : "#0c5460"
        };
        border: 1px solid ${
            type === "success"
                ? "#c3e6cb"
                : type === "error"
                ? "#f5c6cb"
                : "#bee5eb"
        };
        border-radius: 8px;
        padding: 12px 20px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        max-width: 400px;
        word-wrap: break-word;
    `;

    // Add to page
    document.body.appendChild(notification);

    // Remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Censoring function
function censorData(data, type) {
    if (!data) return "";

    switch (type) {
        case "email":
            const emailParts = data.split("@");
            return emailParts[0].charAt(0) + "***@" + emailParts[1];
        case "name":
            // Don't censor names that are 3 characters or less
            if (data.length <= 3) {
                return data;
            }
            return data.substring(0, 3) + "***";
        case "phone":
            return data.replace(
                /(\+\d+\s*\(\d+\)\s*)\d{3}-\d{4}/,
                "$1***-****"
            );
        case "address":
            const addressParts = data.split(", ");
            const city = addressParts[addressParts.length - 2];
            const state = addressParts[addressParts.length - 1];
            return "*** ********* ****** " + city + ", " + state;
        case "emergency":
            const parts = data.split(", ");
            const name = parts[0].substring(0, 3) + "***";
            const email = parts[1].split("@");
            const censoredEmail = email[0].charAt(0) + "***@" + email[1];
            const phone = parts[2].replace(
                /(\+\d+\s*\(\d+\)\s*)\d{3}-\d{4}/,
                "$1***-****"
            );
            return name + ", " + censoredEmail + ", " + phone;
        case "date":
            // Handle different date formats
            // Format: "April 03, 2008" -> "**/**/20**"
            if (data.includes(",")) {
                return "**/**/20**";
            }
            // Format: "03/15/1995" -> "**/**/20**"
            if (data.includes("/")) {
                return data.replace(/\d{2}\/\d{2}\/(\d{4})/, "**/**/20**");
            }
            // Format: "2010-01-21" -> "**/**/20**"
            if (data.includes("-")) {
                return data.replace(/\d{4}-\d{2}-\d{2}/, "**/**/20**");
            }
            // Fallback for any other format
            return "**/**/20**";
        default:
            return data;
    }
}
