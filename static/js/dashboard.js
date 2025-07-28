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
