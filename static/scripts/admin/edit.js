// Edit Functionality

// Global variables for edit state
let editingUser = null;
let savingUsers = new Set();
let editStartTime = null;
let justEnteredEditMode = false;

// Consistent field lists
const EDITABLE_FIELDS = [
    "email",
    "legal_name",
    "preferred_name",
    "pronouns",
    "dob",
    "discord",
    "events",
];

const TEXT_FIELDS = [
    "email",
    "legal_name",
    "preferred_name",
    "pronouns",
    "dob",
    "discord",
];

const FIELD_MAPPING = {
    legal_name: "legalName",
    preferred_name: "preferredName",
};

// Toast notification system
function showToast(message, type = "success") {
    const container = getOrCreateToastContainer();

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    const icon = type === "success" ? "✓" : "✗";
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add("show"), 10);

    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getOrCreateToastContainer() {
    let container = document.querySelector(".toast-container");
    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    return container;
}

// Edit functionality
function editUser(userEmail, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    // Prevent editing if user is currently saving
    if (savingUsers.has(userEmail)) {
        showToast("Please wait for current save to complete", "error");
        return;
    }

    if (editingUser === userEmail) return; // Already editing this user
    if (editingUser) cancelEdit();

    editingUser = userEmail;
    editStartTime = Date.now();
    justEnteredEditMode = true;

    const row = document.querySelector(`[data-user-id="${userEmail}"]`);
    row.classList.add("edit-mode");

    // Clear the flag after a longer delay to allow for initial focus/blur events
    setTimeout(() => {
        justEnteredEditMode = false;
    }, 3000);

    // Hide all edit icons in this row
    row.querySelectorAll(".edit-icon").forEach((icon) => {
        icon.style.display = "none";
    });

    // Show delete icon in ID field
    const deleteIcon = row.querySelector(".delete-icon");
    if (deleteIcon) {
        deleteIcon.style.display = "inline";
    }

    // Make all fields editable except ID
    EDITABLE_FIELDS.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (!cell) return;

        const currentValue = getCurrentFieldValue(row, field);

        if (field === "events") {
            createEventsEditor(cell, currentValue);
        } else {
            createTextEditor(cell, currentValue, field);
        }
    });
}

function getCurrentFieldValue(row, field) {
    // Check for stored user changes first
    const storedValue = row.getAttribute(`data-user-${field}`);
    if (storedValue !== null) {
        return storedValue;
    }

    // Fall back to original data
    const dataField = FIELD_MAPPING[field] || field;
    return row.dataset[dataField] || "";
}

function createTextEditor(cell, currentValue, field) {
    const originalContent = cell.innerHTML;
    const input = document.createElement("input");
    input.type = field === "dob" ? "date" : "text";
    input.className = "edit-input";
    input.value = currentValue === "N/A" ? "" : currentValue;
    input.dataset.originalContent = originalContent;

    cell.innerHTML = "";
    cell.appendChild(input);

    // Focus the input after a small delay to prevent immediate blur events
    setTimeout(() => {
        input.focus();
    }, 100);
}

function createEventsEditor(cell, currentValue) {
    const originalContent = cell.innerHTML;
    const container = document.createElement("div");
    container.dataset.originalContent = originalContent;

    const currentEvents = currentValue.split(",").filter((e) => e.trim());

    Object.keys(eventsData).forEach((eventKey) => {
        const label = document.createElement("label");
        label.style.display = "block";
        label.style.fontSize = "11px";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = eventKey;
        checkbox.checked = currentEvents.includes(eventKey);
        checkbox.style.marginRight = "4px";

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(eventsData[eventKey].name));
        container.appendChild(label);
    });

    cell.innerHTML = "";
    cell.appendChild(container);
}

function saveUser(userEmail) {
    // Check if enough time has passed since edit started (100ms minimum)
    if (editStartTime && Date.now() - editStartTime < 100) {
        setTimeout(
            () => saveUser(userEmail),
            100 - (Date.now() - editStartTime)
        );
        return;
    }

    // Prevent multiple saves
    if (savingUsers.has(userEmail)) {
        return;
    }

    const row = document.querySelector(`[data-user-id="${userEmail}"]`);
    if (!row) return;

    // Store original data for potential revert
    const originalData = {};

    EDITABLE_FIELDS.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (cell) {
            const input = cell.querySelector(".edit-input");
            const container = cell.querySelector("div[data-original-content]");

            if (input && input.dataset.originalContent) {
                originalData[field] = input.dataset.originalContent;
            } else if (container && container.dataset.originalContent) {
                originalData[field] = container.dataset.originalContent;
            }
        }
    });

    // Collect form data
    const formData = new FormData();
    formData.append("email", userEmail);

    // Get user ID from the row
    const userIdCell = row.querySelector('[data-field="id"]');
    const userId = userIdCell ? userIdCell.textContent.trim() : null;
    if (userId) {
        formData.append("user_id", userId);
    }

    // Collect text field values
    const textFields = TEXT_FIELDS;

    textFields.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        const input = cell?.querySelector(".edit-input");
        if (input) {
            formData.append(field, input.value);
        }
    });

    // Collect events
    const eventsCell = row.querySelector(`[data-field="events"]`);
    if (eventsCell) {
        const checkboxes = eventsCell.querySelectorAll(
            'input[type="checkbox"]:checked'
        );
        const selectedEvents = Array.from(checkboxes).map((cb) => cb.value);
        formData.append("events", JSON.stringify(selectedEvents));
    }

    // Exit edit mode immediately and update display with new values optimistically
    exitEditModeWithNewValues(userEmail, formData);

    // Mark as saving
    savingUsers.add(userEmail);
    row.classList.add("saving-mode");

    // Send update
    fetch("/admin/update-user", {
        method: "POST",
        body: formData,
    })
        .then((response) => response.json())
        .then((data) => {
            savingUsers.delete(userEmail);
            row.classList.remove("saving-mode");

            if (data.success) {
                showToast("User updated successfully", "success");
                // Store the user's changes in the row data attributes for future reference
                storeUserChanges(row, formData);
            } else {
                showToast("Error: " + data.error, "error");
                // Revert changes to original display
                revertRowChanges(row, originalData);
            }
        })
        .catch((error) => {
            savingUsers.delete(userEmail);
            row.classList.remove("saving-mode");
            showToast("Error: " + error.message, "error");
            // Revert changes to original display
            revertRowChanges(row, originalData);
        });
}

function cancelEdit() {
    if (!editingUser) return;

    const row = document.querySelector(`[data-user-id="${editingUser}"]`);
    row.classList.remove("edit-mode");

    // Restore original content
    const fields = EDITABLE_FIELDS.filter((f) => f !== "email"); // All except email

    fields.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (!cell) return;

        const input = cell.querySelector(".edit-input");
        const container = cell.querySelector("div[data-original-content]");

        if (input && input.dataset.originalContent) {
            cell.innerHTML = input.dataset.originalContent;
        } else if (container && container.dataset.originalContent) {
            cell.innerHTML = container.dataset.originalContent;
        }
    });

    // Restore edit icons and hide delete icon
    row.querySelectorAll(".edit-icon").forEach((icon) => {
        icon.style.display = "";
    });
    const deleteIcon = row.querySelector(".delete-icon");
    if (deleteIcon) {
        deleteIcon.style.display = "none";
    }

    editingUser = null;
}

// Helper function to exit edit mode without saving
function exitEditMode(userEmail) {
    const row = document.querySelector(`[data-user-id="${userEmail}"]`);
    if (!row) return;

    row.classList.remove("edit-mode");

    // Restore original content
    const fields = EDITABLE_FIELDS;

    fields.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (!cell) return;

        const input = cell.querySelector(".edit-input");
        const container = cell.querySelector("div[data-original-content]");

        if (input && input.dataset.originalContent) {
            cell.innerHTML = input.dataset.originalContent;
        } else if (container && container.dataset.originalContent) {
            cell.innerHTML = container.dataset.originalContent;
        }
    });

    // Restore edit icons and hide delete icon
    row.querySelectorAll(".edit-icon").forEach((icon) => {
        icon.style.display = "";
    });
    const deleteIcon = row.querySelector(".delete-icon");
    if (deleteIcon) {
        deleteIcon.style.display = "none";
    }

    editingUser = null;
}

// Helper function to exit edit mode and display new values
function exitEditModeWithNewValues(userEmail, formData) {
    const row = document.querySelector(`[data-user-id="${userEmail}"]`);
    if (!row) return;

    row.classList.remove("edit-mode");

    // Store the user's changes first
    storeUserChanges(row, formData);

    // Update display with new values instead of reverting to original
    const fields = EDITABLE_FIELDS;

    fields.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (!cell) return;

        // Use stored user changes if available, otherwise use form data
        const storedValue = row.getAttribute(`data-user-${field}`);
        const newValue =
            storedValue !== null ? storedValue : formData.get(field);

        if (field === "events") {
            // Handle events field specially
            if (newValue) {
                const selectedEvents = JSON.parse(newValue);
                updateEventsDisplay(cell, selectedEvents);
            }
        } else {
            // Handle text fields
            if (newValue !== null) {
                updateTextFieldDisplay(cell, newValue);
            }
        }
    });

    // Restore edit icons and hide delete icon
    row.querySelectorAll(".edit-icon").forEach((icon) => {
        icon.style.display = "";
    });
    const deleteIcon = row.querySelector(".delete-icon");
    if (deleteIcon) {
        deleteIcon.style.display = "none";
    }

    editingUser = null;
}

// Helper function to update text field display with new value
function updateTextFieldDisplay(cell, newValue) {
    // Create the display content with edit icon
    const displayValue = newValue === "" ? "N/A" : newValue;
    const userEmail = cell.closest("[data-user-id]").dataset.userId;

    // For now, use simple formatting for all fields to ensure it works
    cell.innerHTML = `${displayValue} <img src="/static/icons/pencil.svg" alt="Edit" class="edit-icon" style="cursor: pointer;" onclick="editUser('${userEmail}')">`;
}

// Helper function to update events display with new values
function updateEventsDisplay(cell, selectedEvents) {
    const userEmail = cell.closest("[data-user-id]").dataset.userId;

    let eventsContent;
    if (selectedEvents.length === 0) {
        eventsContent = "No events";
    } else {
        eventsContent = selectedEvents.join(" ");
    }

    cell.innerHTML = `${eventsContent} <img src="/static/icons/pencil.svg" alt="Edit" class="edit-icon" style="cursor: pointer;" onclick="editUser('${userEmail}')">`;
}

// Helper function to update display with new values after successful save
function updateDisplayWithNewValues(row, formData) {
    const fields = EDITABLE_FIELDS;

    fields.forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (!cell) return;

        if (field === "events") {
            // Handle events field specially
            const eventsData = formData.get("events");
            if (eventsData) {
                const selectedEvents = JSON.parse(eventsData);
                updateEventsDisplay(cell, selectedEvents);
            }
        } else {
            // Handle text fields
            const newValue = formData.get(field);
            if (newValue !== null) {
                updateTextFieldDisplay(cell, newValue);
            }
        }
    });
}

// Helper function to store user changes in row data attributes
function storeUserChanges(row, formData) {
    const fields = EDITABLE_FIELDS;

    fields.forEach((field) => {
        const newValue = formData.get(field);
        if (newValue !== null) {
            // Store the user's change in a data attribute
            row.setAttribute(`data-user-${field}`, newValue);
        }
    });
}

// Helper function to update row data after successful save
function updateRowData(row, formData) {
    // Update data attributes with new values
    for (const [key, value] of formData.entries()) {
        if (key === "email") continue;

        // Convert snake_case to camelCase for dataset
        const dataKey = key.replace(/_([a-z])/g, (_, letter) =>
            letter.toUpperCase()
        );
        row.dataset[dataKey] = value;
    }
}

// Helper function to revert changes if save fails
function revertRowChanges(row, originalData) {
    Object.keys(originalData).forEach((field) => {
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (cell && originalData[field]) {
            cell.innerHTML = originalData[field];
        }
    });

    // Restore edit icons
    row.querySelectorAll(".edit-icon").forEach((icon) => {
        icon.style.display = "";
    });
}

// Delete user function
function deleteUser(userEmail, userId) {
    // Show confirmation dialog
    if (
        confirm(
            `Are you sure you want to delete user ${userEmail}? This action cannot be undone.`
        )
    ) {
        // Send delete request
        fetch("/admin/delete-user", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                email: userEmail,
                user_id: userId,
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    // Remove the row from the table
                    const row = document.querySelector(
                        `[data-user-id="${userEmail}"]`
                    );
                    if (row) {
                        row.remove();
                    }

                    // Show success message
                    alert("User deleted successfully");

                    // Update user count
                    updateUserCount();
                } else {
                    alert(
                        "Error deleting user: " +
                            (data.error || "Unknown error")
                    );
                }
            })
            .catch((error) => {
                console.error("Error:", error);
                alert("Error deleting user: " + error.message);
            });
    }
}

// Helper function to update user count
function updateUserCount() {
    const userRows = document.querySelectorAll(".user-row");
    const countElement = document.querySelector(".user-count");
    if (countElement) {
        countElement.textContent = userRows.length;
    }
}

// Make functions and variables globally accessible
window.editUser = editUser;
window.saveUser = saveUser;
window.cancelEdit = cancelEdit;
window.deleteUser = deleteUser;

// Make variables accessible via getters/setters
Object.defineProperty(window, "editingUser", {
    get: () => editingUser,
    set: (value) => {
        editingUser = value;
    },
});

Object.defineProperty(window, "savingUsers", {
    get: () => savingUsers,
    set: (value) => {
        savingUsers = value;
    },
});

Object.defineProperty(window, "justEnteredEditMode", {
    get: () => justEnteredEditMode,
    set: (value) => {
        justEnteredEditMode = value;
    },
});
