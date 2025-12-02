// Admin panel JavaScript - sidebar navigation and page switching

// Initialize sidebar state from localStorage
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('toggleBtn');
const navItems = document.querySelectorAll('.nav-item');
const pages = document.querySelectorAll('.page-content');

// Load collapsed state from localStorage
const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
if (isCollapsed) {
    sidebar.classList.add('collapsed');
}

// Toggle sidebar
toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    const collapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebarCollapsed', collapsed);
});

// Page navigation
function navigateToPage(pageName) {
    // Update active nav item
    navItems.forEach(item => {
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Show active page
    pages.forEach(page => {
        if (page.id === `page-${pageName}`) {
            page.classList.add('active');
        } else {
            page.classList.remove('active');
        }
    });

    // Update URL without reload
    const url = pageName === 'home' ? '/admin' : `/admin/${pageName}`;
    window.history.pushState({ page: pageName }, '', url);

    // Load page content if needed
    loadPageContent(pageName);
}

// Handle nav item clicks
navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const pageName = item.dataset.page;
        navigateToPage(pageName);
    });
});

// Handle browser back/forward
window.addEventListener('popstate', (e) => {
    if (e.state?.page) {
        // Update UI without pushing new state
        navItems.forEach(item => {
            if (item.dataset.page === e.state.page) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        pages.forEach(page => {
            if (page.id === `page-${e.state.page}`) {
                page.classList.add('active');
            } else {
                page.classList.remove('active');
            }
        });

        loadPageContent(e.state.page);
    }
});

// Permission metadata (from static/permissions.json) - cached after first load
let permissionMetadata = { permissions: {}, categories: {} };
let permissionMetadataLoaded = false;

async function ensurePermissionMetadata() {
    if (permissionMetadataLoaded) return permissionMetadata;

    try {
        const response = await secureFetch('/static/permissions.json');
        const data = await response.json();
        permissionMetadata = {
            permissions: data.permissions || {},
            categories: data.categories || {}
        };
    } catch (error) {
        console.warn('Failed to load permission metadata', error);
        permissionMetadata = { permissions: {}, categories: {} };
    }

    permissionMetadataLoaded = true;
    return permissionMetadata;
}

// Load page content dynamically
async function loadPageContent(pageName) {
    const pageElement = document.getElementById(`page-${pageName}`);

    // Handle attendees page with DataTables
    if (pageName === 'attendees') {
        // Check if DataTables is already initialized
        if ($.fn.DataTable.isDataTable('#attendees-table')) {
            return; // Already initialized
        }

        // Initialize DataTables
        $('#attendees-table').DataTable({
            ajax: {
                url: '/admin/users/data',
                dataSrc: 'data'
            },
            columns: [
                {
                    data: 'email',
                    defaultContent: '',
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditable(td, 'email', rowData));
                    }
                },
                {
                    data: 'legal_name',
                    defaultContent: '',
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditable(td, 'legal_name', rowData));
                    }
                },
                {
                    data: 'preferred_name',
                    defaultContent: '',
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditable(td, 'preferred_name', rowData));
                    }
                },
                {
                    data: 'pronouns',
                    defaultContent: '',
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditable(td, 'pronouns', rowData));
                    }
                },
                {
                    data: 'dob',
                    defaultContent: '',
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditable(td, 'dob', rowData));
                    }
                },
                {
                    data: 'discord_id',
                    defaultContent: '',
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditable(td, 'discord_id', rowData));
                    }
                },
                {
                    data: 'events',
                    render: function(data, type, row) {
                        if (!data || data.length === 0) {
                            return '<span class="text-muted">No events</span>';
                        }
                        return data.map(eventId => {
                            return `<span class="event-tag event-${eventId}">${eventId}</span>`;
                        }).join(' ');
                    },
                    createdCell: function(td, cellData, rowData) {
                        td.classList.add('editable');
                        td.addEventListener('click', () => makeEditableEvents(td, rowData));
                    }
                }
            ],
            pageLength: 1000,
            lengthMenu: [[25, 50, 100, 500, 1000, -1], [25, 50, 100, 500, 1000, "All"]],
            order: [[0, 'asc']],
            scrollY: 'calc(100vh - 250px)',
            scrollCollapse: true,
            paging: true,
            responsive: false
        });
        return;
    }

    // Handle events page
    if (pageName === 'events') {
        if ($.fn.DataTable.isDataTable('#events-table')) {
            return; // Already initialized
        }
        loadEventsPage();
        return;
    }

    // Handle API keys page
    if (pageName === 'keys') {
        if ($.fn.DataTable.isDataTable('#keys-table')) {
            return; // Already initialized
        }
        await loadKeysPage();
        return;
    }

    // Handle admins page
    if (pageName === 'admins') {
        if ($.fn.DataTable.isDataTable('#admins-table')) {
            return; // Already initialized
        }
        loadAdminsPage();
        return;
    }

    // Handle apps page
    if (pageName === 'apps') {
        if ($.fn.DataTable.isDataTable('#apps-table')) {
            return; // Already initialized
        }
        loadAppsPage();
        return;
    }

    // Skip if already loaded (has content other than loading message)
    if (pageElement.querySelector('.loading') === null) {
        return;
    }

    // TODO: Implement actual content loading for other pages
    // For now, just show placeholder
    pageElement.innerHTML = `<h1>${pageName.charAt(0).toUpperCase() + pageName.slice(1)}</h1><p>Content for ${pageName} page.</p>`;
}

// Initialize current page based on URL
const currentPath = window.location.pathname;
let initialPage = 'home';
if (currentPath.includes('/attendees')) initialPage = 'attendees';
else if (currentPath.includes('/events')) initialPage = 'events';
else if (currentPath.includes('/keys')) initialPage = 'keys';
else if (currentPath.includes('/admins')) initialPage = 'admins';
else if (currentPath.includes('/apps')) initialPage = 'apps';

navigateToPage(initialPage);

// Inline editing functionality
let editingCell = null;
let editingRow = null;

function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : 'success'}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function makeEditable(cell, field, rowData) {
    if (editingCell) return;

    editingCell = cell;
    editingRow = rowData;

    const currentValue = cell.textContent;
    const originalValue = currentValue;

    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentValue;
    input.className = 'cell-edit-input';

    cell.textContent = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    let saveTimeout;

    function save() {
        clearTimeout(saveTimeout);
        const newValue = input.value.trim();

        if (newValue === originalValue) {
            cancel();
            return;
        }

        // Optimistic update
        cell.textContent = newValue;
        cell.classList.add('editing');
        editingCell = null;
        editingRow = null;

        // Save to server
        saveTimeout = setTimeout(async () => {
            try {
                const response = await secureFetch('/admin/update-user', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: rowData.email,
                        field: field,
                        value: newValue
                    })
                });

                const data = await response.json();

                if (data.success) {
                    cell.classList.remove('editing');
                    showToast('Saved successfully');
                    rowData[field] = newValue;
                } else {
                    cell.textContent = originalValue;
                    cell.classList.remove('editing');
                    showToast('Failed to save: ' + (data.error || 'Unknown error'), true);
                }
            } catch (error) {
                cell.textContent = originalValue;
                cell.classList.remove('editing');
                showToast('Failed to save: ' + error.message, true);
            }
        }, 100);
    }

    function cancel() {
        clearTimeout(saveTimeout);
        cell.textContent = originalValue;
        editingCell = null;
        editingRow = null;
    }

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            save();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancel();
        }
    });
}

function makeEditableEvents(cell, rowData) {
    if (editingCell) return;

    editingCell = cell;
    editingRow = rowData;

    const currentEvents = rowData.events || [];
    const currentValue = currentEvents.join(', ');
    const originalEvents = [...currentEvents];

    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentValue;
    input.className = 'cell-edit-input';
    input.placeholder = 'e.g., counterspell, scrapyard';

    cell.textContent = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    let saveTimeout;

    function save() {
        clearTimeout(saveTimeout);
        const newValue = input.value.trim();
        const newEvents = newValue ? newValue.split(',').map(e => e.trim()).filter(e => e) : [];

        if (JSON.stringify(newEvents) === JSON.stringify(originalEvents)) {
            cancel();
            return;
        }

        // Optimistic update
        const html = newEvents.length === 0
            ? '<span class="text-muted">No events</span>'
            : newEvents.map(eventId => `<span class="event-tag event-${eventId}">${eventId}</span>`).join(' ');
        cell.innerHTML = html;
        cell.classList.add('editing');
        editingCell = null;
        editingRow = null;

        // Save to server
        saveTimeout = setTimeout(async () => {
            try {
                const response = await secureFetch('/admin/update-user', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: rowData.email,
                        field: 'events',
                        value: newEvents
                    })
                });

                const data = await response.json();

                if (data.success) {
                    cell.classList.remove('editing');
                    showToast('Saved successfully');
                    rowData.events = newEvents;
                } else {
                    const originalHtml = originalEvents.length === 0
                        ? '<span class="text-muted">No events</span>'
                        : originalEvents.map(eventId => `<span class="event-tag event-${eventId}">${eventId}</span>`).join(' ');
                    cell.innerHTML = originalHtml;
                    cell.classList.remove('editing');
                    showToast('Failed to save: ' + (data.error || 'Unknown error'), true);
                }
            } catch (error) {
                const originalHtml = originalEvents.length === 0
                    ? '<span class="text-muted">No events</span>'
                    : originalEvents.map(eventId => `<span class="event-tag event-${eventId}">${eventId}</span>`).join(' ');
                cell.innerHTML = originalHtml;
                cell.classList.remove('editing');
                showToast('Failed to save: ' + error.message, true);
            }
        }, 100);
    }

    function cancel() {
        clearTimeout(saveTimeout);
        const originalHtml = originalEvents.length === 0
            ? '<span class="text-muted">No events</span>'
            : originalEvents.map(eventId => `<span class="event-tag event-${eventId}">${eventId}</span>`).join(' ');
        cell.innerHTML = originalHtml;
        editingCell = null;
        editingRow = null;
    }

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            save();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancel();
        }
    });
}

// API Keys Page
async function loadKeysPage() {
    await ensurePermissionMetadata();

    const pageElement = document.getElementById('page-keys');
    pageElement.innerHTML = `
        <div class="page-header">
            <h1>API Keys</h1>
            <button class="btn-primary" id="add-key-btn">Create API Key</button>
        </div>
        <table id="keys-table" class="display table-full-width">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Created By</th>
                    <th>Permissions</th>
                    <th>Rate Limit</th>
                    <th>Last Used</th>
                    <th>Actions</th>
                </tr>
            </thead>
        </table>
    `;

    document.getElementById('add-key-btn').addEventListener('click', () => openApiKeyModal());

    const table = $('#keys-table').DataTable({
        ajax: {
            url: '/admin/api_keys',
            dataSrc: 'keys'
        },
        columns: [
            {
                data: 'name',
                render: function(data) {
                    return data || '<span class="muted">Untitled</span>';
                }
            },
            { data: 'created_by', defaultContent: '' },
            {
                data: 'permissions',
                render: function(data) {
                    return renderPermissionBadges(data);
                }
            },
            {
                data: 'rate_limit_rpm',
                render: function(data) {
                    if (data === 0) return '<span class="muted">Unlimited</span>';
                    if (typeof data === 'number') return `${data} / min`;
                    return '<span class="muted">n/a</span>';
                }
            },
            {
                data: 'last_used_at',
                render: function(data) {
                    if (!data) return '<span class="muted">Never</span>';
                    const date = new Date(data);
                    return isNaN(date.getTime()) ? data : date.toLocaleString();
                }
            },
            {
                data: 'id',
                render: function(data) {
                    return `
                        <button class="btn-secondary btn-view-logs" data-key-id="${data}">Logs</button>
                        <button class="btn-secondary btn-edit-key" data-key-id="${data}">Edit</button>
                        <button class="btn-danger btn-delete-key" data-key-id="${data}">Delete</button>
                    `;
                }
            }
        ],
        pageLength: 25,
        order: [[4, 'desc']]
    });

    $('#keys-table').on('click', '.btn-edit-key', function() {
        const rowData = table.row($(this).closest('tr')).data();
        openApiKeyModal(rowData);
    });

    $('#keys-table').on('click', '.btn-delete-key', function() {
        const rowData = table.row($(this).closest('tr')).data();
        deleteApiKey(rowData);
    });

    $('#keys-table').on('click', '.btn-view-logs', function() {
        const rowData = table.row($(this).closest('tr')).data();
        viewApiKeyLogs(rowData);
    });
}

function renderPermissionBadges(permissions) {
    if (!permissions || permissions.length === 0) {
        return '<span class="muted">None</span>';
    }

    return permissions.map(perm => {
        const def = permissionMetadata.permissions[perm];
        const category = def ? permissionMetadata.categories[def.category] : null;
        const color = category?.color || '#007bff';
        const displayName = def?.name || perm;
        return `<span class="permission-pill" style="border: 1px solid ${color}; color: ${color};">${displayName}</span>`;
    }).join(' ');
}

async function openApiKeyModal(keyData = null) {
    await ensurePermissionMetadata();

    const title = document.getElementById('api-key-modal-title');
    const idInput = document.getElementById('api-key-id');
    const nameInput = document.getElementById('api-key-name');
    const rateInput = document.getElementById('api-key-rate-limit');

    title.textContent = keyData ? 'Edit API Key' : 'Add API Key';
    idInput.value = keyData?.id || '';
    nameInput.value = keyData?.name || '';
    rateInput.value = typeof keyData?.rate_limit_rpm === 'number' ? keyData.rate_limit_rpm : 60;

    renderPermissionChecklist(keyData?.permissions || []);
    openModal('api-key-modal');
}

function renderPermissionChecklist(selectedPermissions) {
    const container = document.getElementById('api-key-permissions');
    const selectedSet = new Set(selectedPermissions || []);
    const grouped = {};

    Object.entries(permissionMetadata.permissions).forEach(([key, def]) => {
        const category = def.category || 'Other';
        if (!grouped[category]) grouped[category] = [];
        grouped[category].push({ key, def });
    });

    const categories = Object.keys(grouped).sort();
    if (categories.length === 0) {
        container.innerHTML = '<p class="muted">No permissions defined.</p>';
        return;
    }

    container.innerHTML = categories.map(cat => {
        const color = permissionMetadata.categories[cat]?.color || '#00ccff';
        const tiles = grouped[cat].map(item => {
            const checked = selectedSet.has(item.key) ? 'checked' : '';
            return `
                <div class="permission-tile">
                    <label>
                        <input type="checkbox" class="api-key-permission" value="${item.key}" ${checked}>
                        <div>
                            <strong>${item.def.name || item.key}</strong>
                            <span class="permission-pill" style="border: 1px solid ${color}; color: ${color}; background: #f6fbff;">${cat}</span>
                            <small>${item.def.description || ''}</small>
                        </div>
                    </label>
                </div>
            `;
        }).join('');

        return `
            <div class="permission-group">
                <h3>${cat}</h3>
                <div class="permission-grid">${tiles}</div>
            </div>
        `;
    }).join('');
}

function getSelectedApiPermissions() {
    return Array.from(document.querySelectorAll('.api-key-permission:checked')).map(cb => cb.value);
}

async function saveApiKey() {
    const id = document.getElementById('api-key-id').value;
    const name = document.getElementById('api-key-name').value.trim();
    const rateLimit = parseInt(document.getElementById('api-key-rate-limit').value, 10);
    const permissions = getSelectedApiPermissions();

    if (!name) {
        showToast('Name is required', true);
        return;
    }

    if (isNaN(rateLimit) || rateLimit < 0) {
        showToast('Rate limit must be 0 or a positive number', true);
        return;
    }

    const method = id ? 'PATCH' : 'POST';
    const url = id ? `/admin/api_keys/${id}` : '/admin/api_keys';

    try {
        const response = await secureFetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                permissions,
                rate_limit_rpm: rateLimit
            })
        });

        const data = await response.json();
        if (!data.success) {
            showToast(data.error || 'Failed to save API key', true);
            return;
        }

        closeModal('api-key-modal');
        showToast(id ? 'API key updated' : 'API key created');

        if (!id && data.key) {
            document.getElementById('created-api-key').value = data.key;
            openModal('api-key-created-modal');
        }

        if ($.fn.DataTable.isDataTable('#keys-table')) {
            $('#keys-table').DataTable().ajax.reload();
        }
    } catch (error) {
        showToast(error.message || 'Failed to save API key', true);
    }
}

async function deleteApiKey(keyData) {
    if (!keyData?.id) return;
    if (!confirm(`Delete API key "${keyData.name || 'Untitled'}"?`)) return;

    try {
        const response = await secureFetch(`/admin/api_keys/${keyData.id}`, {
            method: 'DELETE',
        });

        const data = await response.json();
        if (data.success) {
            showToast('API key deleted');
            if ($.fn.DataTable.isDataTable('#keys-table')) {
                $('#keys-table').DataTable().ajax.reload();
            }
        } else {
            showToast(data.error || 'Failed to delete key', true);
        }
    } catch (error) {
        showToast(error.message || 'Failed to delete key', true);
    }
}

async function viewApiKeyLogs(keyData) {
    if (!keyData?.id) return;

    try {
        const response = await secureFetch(`/admin/api_keys/${keyData.id}/logs?limit=15`);
        const data = await response.json();

        if (!data.success) {
            showToast(data.error || 'Failed to load logs', true);
            return;
        }

        const logsContainer = document.getElementById('api-key-logs');
        const title = document.getElementById('api-key-logs-title');

        title.textContent = `Usage for ${data.key_name || keyData.name || 'API Key'}`;

        if (!data.logs || data.logs.length === 0) {
            logsContainer.innerHTML = '<p class="muted">No recent usage.</p>';
            openModal('api-key-logs-modal');
            return;
        }

        const logItems = data.logs.map(log => {
            const timestamp = log.timestamp || '';
            const date = new Date(timestamp);
            const formatted = isNaN(date.getTime()) ? timestamp : date.toLocaleString();
            const metadata = log.metadata && Object.keys(log.metadata).length > 0
                ? `<div class="meta">Metadata: ${JSON.stringify(log.metadata)}</div>`
                : '';
            return `<div class="log-row"><div><strong>${log.action || 'request'}</strong></div><div class="meta">${formatted}</div>${metadata}</div>`;
        }).join('');

        logsContainer.innerHTML = logItems;
        openModal('api-key-logs-modal');
    } catch (error) {
        showToast(error.message || 'Failed to load logs', true);
    }
}

// Admins Page
function loadAdminsPage() {
    const pageElement = document.getElementById('page-admins');
    pageElement.innerHTML = `
        <div class="page-header">
            <h1>Admins</h1>
            <button class="btn-primary" id="add-admin-btn">Add Admin</button>
        </div>
        <table id="admins-table" class="display table-full-width">
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Added By</th>
                    <th>Added At</th>
                    <th>Status</th>
                    <th>Permissions</th>
                    <th>Actions</th>
                </tr>
            </thead>
        </table>
    `;

    // Add event listener for Add Admin button
    document.getElementById('add-admin-btn').addEventListener('click', showAddAdminModal);

    // Initialize DataTable
    const table = $('#admins-table').DataTable({
        ajax: {
            url: '/admin/users/data',
            dataSrc: function(json) {
                // Filter for admins only
                return json.data.filter(user => user.is_admin);
            }
        },
        columns: [
            { data: 'email' },
            { data: 'added_by', defaultContent: 'system' },
            { data: 'added_at', defaultContent: 'N/A' },
            {
                data: 'is_active',
                render: function(data) {
                    return data ? '<span class="status-active">Active</span>' : '<span class="status-inactive">Inactive</span>';
                },
                defaultContent: '<span class="status-active">Active</span>'
            },
            {
                data: 'email',
                render: function(data) {
                    return `<button class="btn-secondary btn-manage-permissions" data-email="${data}">Manage</button>`;
                }
            },
            {
                data: 'email',
                render: function(data, type, row) {
                    if (row.added_by === 'system') {
                        return '<span class="text-muted">System Admin</span>';
                    }
                    return `<button class="btn-danger btn-remove-admin" data-email="${data}">Remove</button>`;
                }
            }
        ],
        pageLength: 25,
        order: [[2, 'desc']]
    });

    // Event delegation for dynamically created buttons
    $('#admins-table').on('click', '.btn-manage-permissions', function() {
        const email = $(this).data('email');
        showPermissionsModal(email);
    });

    $('#admins-table').on('click', '.btn-remove-admin', function() {
        const email = $(this).data('email');
        removeAdmin(email);
    });
}

// Apps Page
function loadAppsPage() {
    const pageElement = document.getElementById('page-apps');
    pageElement.innerHTML = `
        <div class="page-header">
            <h1>OAuth 2.0 Apps</h1>
            <button class="btn-primary" id="add-app-btn">Add App</button>
        </div>
        <table id="apps-table" class="display table-full-width">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Icon</th>
                    <th>Client ID</th>
                    <th>Redirect URIs</th>
                    <th>Scopes</th>
                    <th>Created By</th>
                    <th>Allow Anyone</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
        </table>
    `;

    // Add event listener for Add App button
    document.getElementById('add-app-btn').addEventListener('click', showAddAppModal);

    // Initialize DataTable
    $('#apps-table').DataTable({
        ajax: {
            url: '/admin/apps/data',
            dataSrc: 'data'
        },
        columns: [
            { data: 'name' },
            {
                data: 'icon',
                render: function(data) {
                    return data || '';
                }
            },
            {
                data: 'client_id',
                render: function(data) {
                    if (!data) return '<span class="text-muted">Legacy</span>';
                    return `<code class="code-small">${data.substring(0, 20)}...</code>`;
                }
            },
            {
                data: 'redirect_uris',
                render: function(data) {
                    if (!data) return '<span class="text-muted">N/A</span>';
                    try {
                        const uris = JSON.parse(data);
                        if (uris.length === 0) return '<span class="text-muted">None</span>';
                        if (uris.length === 1) return uris[0];
                        return `${uris[0]} <span class="text-muted">(+${uris.length - 1} more)</span>`;
                    } catch {
                        return data;
                    }
                }
            },
            {
                data: 'allowed_scopes',
                render: function(data) {
                    if (!data) return '<span class="text-muted">N/A</span>';
                    try {
                        const scopes = JSON.parse(data);
                        return scopes.join(', ');
                    } catch {
                        return data;
                    }
                }
            },
            { data: 'created_by' },
            {
                data: 'allow_anyone',
                render: function(data) {
                    return data ? '<span class="text-cyan">Yes</span>' : '<span class="text-muted">No</span>';
                }
            },
            {
                data: 'is_active',
                render: function(data) {
                    return data ? '<span class="status-active">Active</span>' : '<span class="status-inactive">Inactive</span>';
                }
            },
            {
                data: 'id',
                render: function(data) {
                    return `
                        <button class="btn-secondary btn-edit-app" data-app-id="${data}">Edit</button>
                        <button class="btn-danger btn-delete-app" data-app-id="${data}">Delete</button>
                    `;
                }
            }
        ],
        pageLength: 25,
        order: [[0, 'asc']]
    });

    // Event delegation for dynamically created buttons
    $('#apps-table').on('click', '.btn-edit-app', function() {
        const appId = $(this).data('app-id');
        editApp(appId);
    });

    $('#apps-table').on('click', '.btn-delete-app', function() {
        const appId = $(this).data('app-id');
        deleteApp(appId);
    });
}

// Events Page
function loadEventsPage() {
    const pageElement = document.getElementById('page-events');
    pageElement.innerHTML = `
        <div class="page-header">
            <h1>Events</h1>
        </div>
        <table id="events-table" class="display table-full-width">
            <thead>
                <tr>
                    <th>Event ID</th>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Attendees</th>
                    <th>Color</th>
                    <th>Discord Role ID</th>
                    <th>Legacy</th>
                </tr>
            </thead>
        </table>
    `;

    // Initialize DataTable
    $('#events-table').DataTable({
        ajax: {
            url: '/admin/events/data',
            dataSrc: 'data'
        },
        columns: [
            { data: 'id' },
            { data: 'name' },
            { data: 'description' },
            {
                data: 'user_count',
                render: function(data) {
                    return `<strong>${data}</strong>`;
                }
            },
            {
                data: 'color',
                render: function(data) {
                    return `<span class="color-swatch" style="background-color: #${data};"></span> <code>#${data}</code>`;
                }
            },
            {
                data: 'discord_role_id',
                render: function(data) {
                    return data ? `<code>${data}</code>` : '';
                }
            },
            {
                data: 'legacy',
                render: function(data) {
                    return data ? '<span class="text-warning">Yes</span>' : '<span class="text-muted">No</span>';
                }
            }
        ],
        pageLength: 25,
        order: [[3, 'desc']] // Sort by attendees descending
    });
}

// Modal helper functions - make them globally accessible
window.openModal = function(modalId) {
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById(modalId);
    overlay.classList.add('show');
    modal.classList.add('show');
}

window.closeModal = function(modalId) {
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById(modalId);
    overlay.classList.remove('show');
    modal.classList.remove('show');
}

// Close modal when clicking outside or on close buttons
$(document).ready(function() {
    // Click outside to close
    $('#modal-overlay').on('click', function(e) {
        if (e.target.id === 'modal-overlay') {
            // Find which modal is open and close it
            $('.modal[style*="display: block"]').each(function() {
                closeModal(this.id);
            });
        }
    });

    // Close button (×) click handler
    $(document).on('click', '.modal-close', function() {
        const modalId = $(this).data('modal');
        if (modalId) {
            closeModal(modalId);
        }
    });

    // Cancel button click handler
    $(document).on('click', '.modal-cancel', function() {
        const modalId = $(this).data('modal');
        if (modalId) {
            closeModal(modalId);
        }
    });
});

// Modal and action functions
function showAddAdminModal() {
    document.getElementById('new-admin-email').value = '';
    openModal('add-admin-modal');
}

// Event listener for Add Admin confirmation
$(document).ready(function() {
    $('#confirm-add-admin-btn').on('click', function() {
        const email = document.getElementById('new-admin-email').value.trim();
        if (!email) {
            showToast('Please enter an email', true);
            return;
        }

        secureFetch('/admin/admins/data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('Admin added successfully');
                closeModal('add-admin-modal');
                if ($.fn.DataTable.isDataTable('#admins-table')) {
                    $('#admins-table').DataTable().ajax.reload();
                }
            } else {
                showToast(data.error || 'Failed to add admin', true);
            }
        });
    });

    // Event listener for Save Permissions
    $('#save-permissions-btn').on('click', savePermissions);

    // Event listener for Save App
    $('#save-app-btn').on('click', saveApp);

    // Event listener for Save API Key
    $('#save-api-key-btn').on('click', saveApiKey);

    // Copy newly created API key
    $('#copy-api-key-btn').on('click', function() {
        const input = document.getElementById('created-api-key');
        input.select();
        input.setSelectionRange(0, 99999);
        navigator.clipboard?.writeText(input.value).then(() => {
            showToast('Copied to clipboard');
        }).catch(() => {
            showToast('Copied', false);
        });
    });
});

function removeAdmin(email) {
    if (!confirm(`Remove admin privileges from ${email}?`)) return;

    secureFetch(`/admin/admins/data/${encodeURIComponent(email)}`, {
        method: 'DELETE',
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Admin removed successfully');
            $('#admins-table').DataTable().ajax.reload();
        } else {
            showToast(data.error || 'Failed to remove admin', true);
        }
    });
}

function showPermissionsModal(email) {
    // Fetch current permissions
    secureFetch(`/admin/admins/${encodeURIComponent(email)}/permissions`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                showToast(data.error || 'Failed to load permissions', true);
                return;
            }

            const permissions = data.permissions || [];
            const content = document.getElementById('permissions-content');

            // Store email for later use
            content.dataset.adminEmail = email;

            // Build permissions UI
            let html = `<h3 class="mb-15">Permissions for ${email}</h3>`;

            // Universal permission - only write
            html += `<div class="permission-group">
                <h3>Universal</h3>
                <div class="permission-item">
                    <label class="permission-label">*</label>
                    <div class="permission-access">
                        <label><input type="checkbox" class="access-write" data-type="*" data-value="*"> Write</label>
                    </div>
                </div>
            </div>`;

            // Events section
            html += `<div class="permission-group">
                <h3>Events</h3>
                <div class="permission-item">
                    <label class="permission-label">All Events</label>
                    <div class="permission-access">
                        <label><input type="checkbox" class="access-read" data-type="event" data-value="*"> Read</label>
                        <label><input type="checkbox" class="access-write" data-type="event" data-value="*"> Write</label>
                    </div>
                </div>
                <div class="permission-item">
                    <label class="permission-label">Counterspell</label>
                    <div class="permission-access">
                        <label><input type="checkbox" class="access-read" data-type="event" data-value="counterspell"> Read</label>
                        <label><input type="checkbox" class="access-write" data-type="event" data-value="counterspell"> Write</label>
                    </div>
                </div>
                <div class="permission-item">
                    <label class="permission-label">Scrapyard</label>
                    <div class="permission-access">
                        <label><input type="checkbox" class="access-read" data-type="event" data-value="scrapyard"> Read</label>
                        <label><input type="checkbox" class="access-write" data-type="event" data-value="scrapyard"> Write</label>
                    </div>
                </div>
                <div class="permission-item">
                    <label class="permission-label">hack.sv 2025</label>
                    <div class="permission-access">
                        <label><input type="checkbox" class="access-read" data-type="event" data-value="hacksv_2025"> Read</label>
                        <label><input type="checkbox" class="access-write" data-type="event" data-value="hacksv_2025"> Write</label>
                    </div>
                </div>
            </div>`;

            // Pages section
            html += `<div class="permission-group">
                <h3>Pages</h3>`;

            const pages = ['attendees', 'events', 'keys', 'admins', 'apps'];
            pages.forEach(page => {
                html += `<div class="permission-item">
                    <label class="permission-label">${page.charAt(0).toUpperCase() + page.slice(1)}</label>
                    <div class="permission-access">
                        <label><input type="checkbox" class="access-read" data-type="page" data-value="${page}"> Read</label>
                        <label><input type="checkbox" class="access-write" data-type="page" data-value="${page}"> Write</label>
                    </div>
                </div>`;
            });

            html += `</div>`;

            // Apps section - fetch apps dynamically
            html += `<div class="permission-group">
                <h3>Apps</h3>
                <div id="apps-permissions-loading">Loading apps...</div>
            </div>`;

            content.innerHTML = html;

            // Fetch apps and add to permissions
            secureFetch('/admin/apps/data')
                .then(r => r.json())
                .then(appsData => {
                    const appsContainer = content.querySelector('#apps-permissions-loading').parentElement;
                    let appsHtml = '<h3>Apps</h3>';

                    if (appsData.data && appsData.data.length > 0) {
                        appsData.data.forEach(app => {
                            appsHtml += `<div class="permission-item">
                                <label class="permission-label">${app.name}</label>
                                <div class="permission-access">
                                    <label><input type="checkbox" class="access-read" data-type="app" data-value="${app.id}"> Read</label>
                                    <label><input type="checkbox" class="access-write" data-type="app" data-value="${app.id}"> Write</label>
                                </div>
                            </div>`;
                        });
                    } else {
                        appsHtml += '<p class="muted">No apps available</p>';
                    }

                    appsContainer.innerHTML = appsHtml;

                    // Re-check existing permissions after apps are loaded
                    permissions.forEach(perm => {
                        const checkbox = content.querySelector(`input[data-type="${perm.permission_type}"][data-value="${perm.permission_value}"].access-${perm.access_level}`);
                        if (checkbox) {
                            checkbox.checked = true;
                        }
                    });
                });

            // Check existing permissions for events and pages (before apps are loaded)
            permissions.forEach(perm => {
                if (perm.permission_type !== 'app') {
                    const checkbox = content.querySelector(`input[data-type="${perm.permission_type}"][data-value="${perm.permission_value}"].access-${perm.access_level}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                }
            });

            openModal('permissions-modal');
        });
}
function savePermissions() {
    const content = document.getElementById('permissions-content');
    const email = content.dataset.adminEmail;

    // Collect all checked permissions
    const permissions = [];
    content.querySelectorAll('.access-read:checked, .access-write:checked').forEach(checkbox => {
        permissions.push({
            permission_type: checkbox.dataset.type,
            permission_value: checkbox.dataset.value,
            access_level: checkbox.classList.contains('access-read') ? 'read' : 'write'
        });
    });

    // Send to server
    secureFetch(`/admin/admins/${encodeURIComponent(email)}/permissions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ permissions })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Permissions updated successfully');
            closeModal('permissions-modal');
        } else {
            showToast(data.error || 'Failed to update permissions', true);
        }
    });
}

function showAddAppModal() {
    document.getElementById('app-modal-title').textContent = 'Add OAuth 2.0 App';
    document.getElementById('app-id').value = '';
    document.getElementById('app-name').value = '';
    document.getElementById('app-icon').value = '';
    document.getElementById('app-redirect-uris').value = '';
    document.getElementById('app-allow-anyone').checked = false;
    document.getElementById('app-skip-consent').checked = false;

    // Hide credentials section for new apps
    const credentials = document.getElementById('app-credentials');
    credentials.classList.add('hidden');

    // Load scopes
    loadAppScopes([]);

    openModal('app-modal');
}

function editApp(appId) {
    // Fetch app details
    secureFetch(`/admin/apps/data`)
        .then(r => {
            if (r.status === 403) {
                showToast('You don\'t have permission to edit apps', true);
                throw new Error('Permission denied');
            }
            return r.json();
        })
        .then(data => {
            const app = data.data.find(a => a.id === appId);
            if (!app) {
                showToast('App not found', true);
                return;
            }

            document.getElementById('app-modal-title').textContent = 'Edit OAuth 2.0 App';
            document.getElementById('app-id').value = app.id;
            document.getElementById('app-name').value = app.name;
            document.getElementById('app-icon').value = app.icon || '';

            // Handle redirect URIs
            if (app.redirect_uris) {
                try {
                    const uris = JSON.parse(app.redirect_uris);
                    document.getElementById('app-redirect-uris').value = uris.join('\n');
                } catch {
                    document.getElementById('app-redirect-uris').value = '';
                }
            } else {
                document.getElementById('app-redirect-uris').value = '';
            }

            document.getElementById('app-allow-anyone').checked = app.allow_anyone;
            document.getElementById('app-skip-consent').checked = app.skip_consent_screen || false;

            // Show credentials if they exist
            const credentials = document.getElementById('app-credentials');
            if (app.client_id) {
                credentials.classList.remove('hidden');
                document.getElementById('app-client-id').value = app.client_id;
                document.getElementById('app-client-secret').value = app.client_secret || '';
                document.getElementById('app-client-secret').type = 'password';
            } else {
                credentials.classList.add('hidden');
            }

            // Load scopes
            const scopes = app.allowed_scopes ? JSON.parse(app.allowed_scopes) : [];
            loadAppScopes(scopes);

            openModal('app-modal');
        })
        .catch(error => {
            // Session expired and permission denied errors already shown
            if (error.message !== 'Session expired' &&
                error.message !== 'CSRF token is missing' &&
                error.message !== 'Permission denied') {
                showToast('Failed to load app details: ' + error.message, true);
            }
        });
}

function saveApp() {
    const appId = document.getElementById('app-id').value;
    const name = document.getElementById('app-name').value.trim();
    const icon = document.getElementById('app-icon').value.trim();
    const redirectUrisText = document.getElementById('app-redirect-uris').value.trim();
    const allowAnyone = document.getElementById('app-allow-anyone').checked;
    const skipConsent = document.getElementById('app-skip-consent').checked;

    if (!name) {
        showToast('Name is required', true);
        return;
    }

    // Parse redirect URIs
    const redirectUris = redirectUrisText.split('\n').map(uri => uri.trim()).filter(uri => uri.length > 0);
    if (redirectUris.length === 0) {
        showToast('At least one redirect URI is required', true);
        return;
    }

    // Get selected scopes
    const selectedScopes = [];
    document.querySelectorAll('#app-scopes input[type="checkbox"]:checked').forEach(cb => {
        selectedScopes.push(cb.value);
    });

    if (selectedScopes.length === 0) {
        showToast('At least one scope is required', true);
        return;
    }

    const method = appId ? 'PUT' : 'POST';
    const url = appId ? `/admin/apps/${appId}` : '/admin/apps';

    secureFetch(url, {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name,
            icon,
            redirect_uris: redirectUris,
            allowed_scopes: selectedScopes,
            allow_anyone: allowAnyone,
            skip_consent_screen: skipConsent
        })
    })
    .then(r => {
        if (r.status === 403) {
            showToast('You don\'t have permission to ' + (appId ? 'edit' : 'create') + ' apps', true);
            throw new Error('Permission denied');
        }
        return r.json();
    })
    .then(data => {
        if (data.success) {
            showToast(appId ? 'App updated successfully' : 'App created successfully');
            closeModal('app-modal');
            if ($.fn.DataTable.isDataTable('#apps-table')) {
                $('#apps-table').DataTable().ajax.reload();
            }
        } else {
            showToast(data.error || 'Failed to save app', true);
        }
    })
    .catch(error => {
        // Session expired and permission denied errors already shown
        if (error.message !== 'Session expired' &&
            error.message !== 'CSRF token is missing' &&
            error.message !== 'Permission denied') {
            showToast('Failed to save app: ' + error.message, true);
        }
    });
}

function deleteApp(appId) {
    if (!confirm('Delete this app?')) return;

    secureFetch(`/admin/apps/${appId}`, {
        method: 'DELETE',
    })
    .then(r => {
        if (r.status === 403) {
            showToast('You don\'t have permission to delete apps', true);
            throw new Error('Permission denied');
        }
        return r.json();
    })
    .then(data => {
        if (data.success) {
            showToast('App deleted successfully');
            $('#apps-table').DataTable().ajax.reload();
        } else {
            showToast(data.error || 'Failed to delete app', true);
        }
    })
    .catch(error => {
        // Session expired and permission denied errors already shown
        if (error.message !== 'Session expired' &&
            error.message !== 'CSRF token is missing' &&
            error.message !== 'Permission denied') {
            showToast('Failed to delete app: ' + error.message, true);
        }
    });
}

// Load available scopes from static/scopes.json
function loadAppScopes(selectedScopes = []) {
    secureFetch('/static/scopes.json')
        .then(r => r.json())
        .then(data => {
            const scopesContainer = document.getElementById('app-scopes');
            scopesContainer.innerHTML = '';

            data.scopes.forEach(scope => {
                const isChecked = selectedScopes.includes(scope.name);
                const isRequired = scope.required;

                const scopeDiv = document.createElement('div');
                scopeDiv.className = 'permission-item';
                scopeDiv.innerHTML = `
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox"
                               value="${scope.name}"
                               ${isChecked ? 'checked' : ''}
                               ${isRequired ? 'disabled checked' : ''}
                               style="margin-right: 10px;">
                        <div>
                            <strong>${scope.name}</strong>
                            <div style="font-size: 0.85em; color: #888;">${scope.description}</div>
                        </div>
                    </label>
                `;
                scopesContainer.appendChild(scopeDiv);
            });
        })
        .catch(err => {
            console.error('Failed to load scopes:', err);
            document.getElementById('app-scopes').innerHTML = '<p class="error">Failed to load scopes</p>';
        });
}

// Copy text to clipboard
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const text = element.value;

    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', true);
    });
}

// Toggle secret visibility
function toggleSecretVisibility(event) {
    const secretInput = document.getElementById('app-client-secret');
    const button = event ? event.target : null;

    if (secretInput.type === 'password') {
        secretInput.type = 'text';
        if (button) button.textContent = 'Hide';
    } else {
        secretInput.type = 'password';
        if (button) button.textContent = 'Show';
    }
}

// Regenerate client secret
function regenerateSecret() {
    const appId = document.getElementById('app-id').value;

    if (!appId) {
        showToast('Cannot regenerate secret for new app', true);
        return;
    }

    if (!confirm('Regenerate client secret? This will invalidate the current secret and break existing integrations until they update to the new secret.')) {
        return;
    }

    secureFetch(`/admin/apps/${appId}/regenerate-secret`, {
        method: 'POST',
    })
    .then(r => {
        if (r.status === 403) {
            showToast('You don\'t have permission to regenerate secrets', true);
            throw new Error('Permission denied');
        }
        return r.json();
    })
    .then(data => {
        if (data.success) {
            document.getElementById('app-client-secret').value = data.client_secret;
            document.getElementById('app-client-secret').type = 'text';
            showToast('Client secret regenerated successfully');
        } else {
            showToast(data.error || 'Failed to regenerate secret', true);
        }
    })
    .catch(error => {
        // Session expired and permission denied errors already shown
        if (error.message !== 'Session expired' &&
            error.message !== 'CSRF token is missing' &&
            error.message !== 'Permission denied') {
            showToast('Failed to regenerate secret: ' + error.message, true);
        }
    });
}
