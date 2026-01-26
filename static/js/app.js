/**
 * Moonlight Dashboard - Main Application JavaScript
 * Workstation Manager for Apollo/Moonlight Streaming
 */

/* ============================================
   State
   ============================================ */
let discoveredWorkstations = [];
let selectedForImport = new Set();
let iconPickerResolve = null;

/* ============================================
   Color Utilities
   ============================================ */

/**
 * Parse a color string (hex or rgb) to RGB values
 * @param {string} color - Color in hex (#rgb, #rrggbb) or rgb(r, g, b) format
 * @returns {{r: number, g: number, b: number}|null} RGB values (0-255) or null if invalid
 */
function parseColor(color) {
    // Handle hex colors
    if (color.startsWith('#')) {
        let hex = color.slice(1);
        // Expand shorthand (#rgb -> #rrggbb)
        if (hex.length === 3) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }
        if (hex.length === 6) {
            return {
                r: parseInt(hex.slice(0, 2), 16),
                g: parseInt(hex.slice(2, 4), 16),
                b: parseInt(hex.slice(4, 6), 16)
            };
        }
    }
    // Handle rgb() colors
    const rgbMatch = color.match(/rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i);
    if (rgbMatch) {
        return {
            r: parseInt(rgbMatch[1], 10),
            g: parseInt(rgbMatch[2], 10),
            b: parseInt(rgbMatch[3], 10)
        };
    }
    return null;
}

/**
 * Calculate the relative luminance of a color (WCAG formula)
 * @param {{r: number, g: number, b: number}} rgb - RGB values (0-255)
 * @returns {number} Relative luminance (0-1)
 */
function getLuminance(rgb) {
    const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Determine if a color is light (needs dark text) or dark (needs light text)
 * @param {string} color - Color in hex or rgb format
 * @returns {boolean} True if the color is light
 */
function isLightColor(color) {
    const rgb = parseColor(color);
    if (!rgb) return false;
    // Threshold of 0.179 is based on WCAG contrast guidelines
    return getLuminance(rgb) > 0.179;
}

/**
 * Set the accent text color CSS variable based on accent color luminance
 */
function updateAccentTextColor() {
    const accentColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--accent-color').trim();

    const textColor = isLightColor(accentColor) ? '#000000' : '#ffffff';
    document.documentElement.style.setProperty('--accent-text-color', textColor);
}

/* ============================================
   Icon Picker
   ============================================ */

// Curated list of relevant Bootstrap Icons for workstation groups
const AVAILABLE_ICONS = [
    // Devices
    'bi-pc-display-horizontal', 'bi-pc-display', 'bi-laptop', 'bi-display',
    'bi-gpu-card', 'bi-cpu', 'bi-motherboard', 'bi-device-hdd', 'bi-device-ssd',
    'bi-server', 'bi-hdd-rack', 'bi-hdd-network', 'bi-router',
    // Categories
    'bi-folder', 'bi-folder2', 'bi-folder2-open', 'bi-collection',
    'bi-grid', 'bi-grid-3x3', 'bi-layers', 'bi-stack',
    // Gaming
    'bi-controller', 'bi-joystick', 'bi-headset-vr', 'bi-dice-5',
    // Creative
    'bi-brush', 'bi-palette', 'bi-easel', 'bi-camera-reels', 'bi-film',
    'bi-music-note-beamed', 'bi-vinyl', 'bi-image',
    // Development
    'bi-code-square', 'bi-code-slash', 'bi-terminal', 'bi-bug', 'bi-git',
    'bi-braces', 'bi-filetype-py', 'bi-filetype-js',
    // Office / Work
    'bi-building', 'bi-buildings', 'bi-briefcase', 'bi-clipboard-data',
    'bi-graph-up', 'bi-kanban', 'bi-calendar-event',
    // Location
    'bi-house', 'bi-house-door', 'bi-geo-alt', 'bi-pin-map', 'bi-globe',
    // Cloud / Network
    'bi-cloud', 'bi-cloud-upload', 'bi-cloud-download', 'bi-database',
    'bi-hdd-stack', 'bi-box-seam', 'bi-archive',
    // Education
    'bi-mortarboard', 'bi-book', 'bi-journal-code', 'bi-lightbulb',
    // Tools
    'bi-tools', 'bi-wrench', 'bi-gear', 'bi-sliders', 'bi-hammer',
    // People
    'bi-person', 'bi-people', 'bi-person-workspace',
    // Misc
    'bi-star', 'bi-heart', 'bi-lightning', 'bi-fire', 'bi-snow',
    'bi-cup-hot', 'bi-rocket-takeoff', 'bi-shield-check', 'bi-key',
    'bi-lock', 'bi-eye', 'bi-bullseye', 'bi-award', 'bi-trophy'
];

/**
 * Show the icon picker modal and return the selected icon
 * @param {string} currentIcon - Currently selected icon class
 * @returns {Promise<string|null>} Selected icon class or null if cancelled
 */
function showIconPicker(currentIcon = 'bi-folder') {
    return new Promise((resolve) => {
        iconPickerResolve = resolve;

        const grid = document.getElementById('iconPickerGrid');
        const searchInput = document.getElementById('iconSearchInput');

        // Render icons
        renderIconGrid(AVAILABLE_ICONS, currentIcon);

        // Setup search
        searchInput.value = '';
        searchInput.oninput = () => {
            const query = searchInput.value.toLowerCase();
            const filtered = AVAILABLE_ICONS.filter(icon =>
                icon.toLowerCase().includes(query)
            );
            renderIconGrid(filtered, currentIcon);
        };

        const modalEl = document.getElementById('iconPickerModal');
        const modal = new bootstrap.Modal(modalEl);

        // Handle cancel
        const handleHidden = () => {
            modalEl.removeEventListener('hidden.bs.modal', handleHidden);
            if (iconPickerResolve) {
                iconPickerResolve(null);
                iconPickerResolve = null;
            }
        };
        modalEl.addEventListener('hidden.bs.modal', handleHidden);

        modal.show();
        searchInput.focus();
    });
}

/**
 * Render the icon grid
 * @param {string[]} icons - Array of icon classes to display
 * @param {string} selected - Currently selected icon
 */
function renderIconGrid(icons, selected) {
    const grid = document.getElementById('iconPickerGrid');
    grid.innerHTML = icons.map(icon => `
        <div class="icon-picker-item ${icon === selected ? 'selected' : ''}"
             data-icon="${icon}"
             onclick="selectIcon('${icon}')"
             title="${icon.replace('bi-', '')}">
            <i class="bi ${icon}"></i>
        </div>
    `).join('');
}

/**
 * Handle icon selection
 * @param {string} icon - Selected icon class
 */
function selectIcon(icon) {
    if (iconPickerResolve) {
        iconPickerResolve(icon);
        iconPickerResolve = null;
    }
    bootstrap.Modal.getInstance(document.getElementById('iconPickerModal')).hide();
}

/* ============================================
   Toast Notifications
   ============================================ */

/**
 * Show a toast notification
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {string} type - Toast type: 'error', 'success', or 'info'
 * @param {number} duration - Auto-hide duration in ms (default: 4000)
 */
function showToast(title, message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    const id = 'toast-' + Date.now();

    const iconMap = {
        error: 'bi-exclamation-circle',
        success: 'bi-check-circle',
        info: 'bi-info-circle'
    };

    const html = `
        <div id="${id}" class="toast toast-${type}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="bi ${iconMap[type] || iconMap.info} me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);

    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: duration });
    toast.show();

    // Remove from DOM after hidden
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

/* ============================================
   Confirmation Dialog
   ============================================ */

/**
 * Show a confirmation dialog
 * @param {string} message - The message to display
 * @param {object} options - Optional settings
 * @param {string} options.title - Dialog title (default: "Confirm")
 * @param {string} options.confirmText - Confirm button text (default: "Confirm")
 * @param {string} options.confirmClass - Confirm button class (default: "btn-danger")
 * @param {string} options.icon - Bootstrap icon class (default: "bi-question-circle")
 * @returns {Promise<boolean>} Resolves to true if confirmed, false otherwise
 */
function showConfirm(message, options = {}) {
    return new Promise((resolve) => {
        const {
            title = 'Confirm',
            confirmText = 'Confirm',
            confirmClass = 'btn-danger',
            icon = 'bi-question-circle'
        } = options;

        const modalEl = document.getElementById('confirmModal');
        const titleEl = document.getElementById('confirmTitle');
        const messageEl = document.getElementById('confirmMessage');
        const okBtn = document.getElementById('confirmOk');

        // Set content
        titleEl.innerHTML = `<i class="bi ${icon} me-2"></i>${title}`;
        messageEl.textContent = message;
        okBtn.innerHTML = `<i class="bi bi-check-lg me-1"></i>${confirmText}`;
        okBtn.className = `btn ${confirmClass} btn-sm`;

        const modal = new bootstrap.Modal(modalEl);

        // Handle confirm
        const handleConfirm = () => {
            cleanup();
            modal.hide();
            resolve(true);
        };

        // Handle cancel/dismiss
        const handleCancel = () => {
            cleanup();
            resolve(false);
        };

        // Cleanup listeners
        const cleanup = () => {
            okBtn.removeEventListener('click', handleConfirm);
            modalEl.removeEventListener('hidden.bs.modal', handleCancel);
        };

        okBtn.addEventListener('click', handleConfirm);
        modalEl.addEventListener('hidden.bs.modal', handleCancel);

        modal.show();
    });
}

/* ============================================
   API Helpers
   ============================================ */

/**
 * Make a JSON POST request
 * @param {string} url - API endpoint
 * @param {object} data - Request body
 * @returns {Promise<object>} Response data
 */
async function postJSON(url, data) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

/**
 * Make a JSON PUT request
 * @param {string} url - API endpoint
 * @param {object} data - Request body
 * @returns {Promise<object>} Response data
 */
async function putJSON(url, data) {
    const res = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

/* ============================================
   Moonlight Streaming
   ============================================ */

/**
 * Launch a Moonlight stream with proper URL encoding
 * @param {string} ip - Host IP address
 * @param {string} app - Application name to stream
 * @param {number} [port] - Optional Apollo port (for multi-instance setups)
 */
function launchMoonlight(ip, app, port) {
    showToast('Launching', `Connecting to ${app}...`, 'info', 3000);
    let url;
    if (port) {
        url = `moonlight://connect/${ip}?port=${port}&app=${encodeURIComponent(app)}`;
    } else {
        url = `moonlight://connect/${ip}?app=${encodeURIComponent(app)}`;
    }
    window.location.href = url;
}

/* ============================================
   Workstation CRUD
   ============================================ */

/**
 * Delete a workstation
 * @param {string} id - Workstation ID
 */
async function deleteWorkstation(id) {
    const confirmed = await showConfirm('Are you sure you want to delete this workstation?', {
        title: 'Delete Workstation',
        confirmText: 'Delete',
        icon: 'bi-trash'
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/workstations/${id}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            showToast('Deleted', 'Workstation removed successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Error', 'Failed to delete workstation', 'error');
        }
    } catch (e) {
        showToast('Error', 'Failed to delete workstation: ' + e.message, 'error');
    }
}

/**
 * Probe a workstation and update its info
 * @param {string} ip - Workstation IP
 * @param {string} id - Workstation ID
 */
async function probeWorkstation(ip, id) {
    showToast('Probing', `Checking ${ip}...`, 'info', 2000);

    try {
        const res = await fetch(`/api/probe/${ip}`);
        const data = await res.json();

        if (data.apollo_online) {
            const updateData = {};
            if (data.apollo_instances) updateData.apollo_instances = data.apollo_instances;
            if (data.hostname) updateData.hostname = data.hostname;
            if (data.gpu) updateData.gpu = data.gpu;
            if (data.ram) updateData.ram = data.ram;
            if (data.os) updateData.os = data.os;
            if (data.cpu) updateData.cpu = data.cpu;

            await putJSON(`/api/workstations/${id}`, updateData);
            showToast('Updated', 'Workstation info refreshed', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Offline', `Apollo not responding on ${ip}`, 'error');
        }
    } catch (e) {
        showToast('Error', 'Probe failed: ' + e.message, 'error');
    }
}

/* ============================================
   Status & Connectivity
   ============================================ */

/**
 * Refresh online/offline status for all workstations
 */
async function refreshStatus() {
    document.querySelectorAll('.status-indicator').forEach(async el => {
        const ip = el.dataset.ip;
        try {
            const res = await fetch(`/api/ping/${ip}`);
            const data = await res.json();
            el.innerHTML = data.online
                ? '<i class="bi bi-circle-fill status-online"></i>'
                : '<i class="bi bi-circle-fill status-offline"></i>';
        } catch {
            el.innerHTML = '<i class="bi bi-circle-fill status-offline"></i>';
        }
    });
}

/**
 * Test if the Moonlight protocol handler is installed
 */
function testProtocolHandler() {
    const resultSpan = document.getElementById('testResult');
    resultSpan.innerHTML = '<span class="text-info">Opening Moonlight...</span>';

    // Try to open a test URL - use localhost with a dummy app
    // The handler expects: moonlight://connect/{ip}?app={appname}
    window.location.href = 'moonlight://connect/127.0.0.1?app=Desktop';

    // After a moment, ask if it worked
    setTimeout(() => {
        resultSpan.innerHTML = '<span class="text-warning">Did Moonlight open?</span>';
    }, 1500);
}

/* ============================================
   Network Discovery
   ============================================ */

/**
 * Start network discovery scan
 */
async function startDiscovery() {
    const subnetInput = document.getElementById('scanSubnet').value.trim();
    const startInput = document.getElementById('scanStart').value.trim();
    const endInput = document.getElementById('scanEnd').value.trim();

    // Validate inputs
    if (!subnetInput) {
        showToast('Missing Field', 'Please enter a subnet (e.g., 192.168.1)', 'error');
        return;
    }

    if (!startInput || !endInput) {
        showToast('Missing Field', 'Please enter start and end IP addresses', 'error');
        return;
    }

    const start = parseInt(startInput);
    const end = parseInt(endInput);

    if (isNaN(start) || isNaN(end)) {
        showToast('Invalid Input', 'Start and end IPs must be numbers', 'error');
        return;
    }

    if (start < 1 || start > 254 || end < 1 || end > 254) {
        showToast('Invalid Range', 'IP addresses must be between 1 and 254', 'error');
        return;
    }

    if (start > end) {
        showToast('Invalid Range', 'Start IP must be less than or equal to end IP', 'error');
        return;
    }

    const status = document.getElementById('discoveryStatus');
    const results = document.getElementById('discoveryResults');

    // Reset state
    status.classList.remove('d-none');
    status.innerHTML = `<i class="bi bi-hourglass-split pulse me-2"></i>Scanning ${end - start + 1} IPs for Apollo servers...`;
    results.innerHTML = '';
    discoveredWorkstations = [];
    selectedForImport.clear();
    updateImportButton();

    try {
        const data = await postJSON('/api/discover', { subnet: subnetInput, start, end });
        discoveredWorkstations = data.discovered;

        status.classList.add('d-none');

        if (data.count === 0) {
            results.innerHTML = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle me-2"></i>No Apollo servers found on the network.</div>';
            return;
        }

        results.innerHTML = `<div class="alert alert-success mb-3"><i class="bi bi-check-circle me-2"></i>Found ${data.count} Apollo server(s)</div>`;

        data.discovered.forEach((ws, idx) => {
            results.innerHTML += createDiscoveryItemHTML(ws, idx);
        });

    } catch (e) {
        status.classList.add('d-none');
        showToast('Scan Failed', e.message, 'error');
    }
}

/**
 * Create HTML for a discovery result item
 * @param {object} ws - Workstation data
 * @param {number} idx - Index
 * @returns {string} HTML string
 */
function createDiscoveryItemHTML(ws, idx) {
    const specsHtml = [ws.gpu, ws.ram, ws.cpu]
        .filter(Boolean)
        .map(s => `<span class="badge specs-badge me-1">${s}</span>`)
        .join('') || '<span class="text-muted">Specs unknown</span>';

    // Handle both new apollo_instances format and legacy apps format
    let appsHtml = '';
    if (ws.apollo_instances && ws.apollo_instances.length) {
        // New format: show instance count and all apps
        const instanceCount = ws.apollo_instances.length;
        if (instanceCount > 1) {
            appsHtml = `<span class="badge bg-info me-1">${instanceCount} displays</span>`;
        }
        // Collect all apps from all instances
        const allApps = ws.apollo_instances.flatMap(inst => inst.apps);
        appsHtml += allApps.map(a => `<span class="badge app-badge me-1">${a}</span>`).join('');
    } else if (ws.apps && ws.apps.length) {
        // Legacy format
        appsHtml = ws.apps.map(a => `<span class="badge app-badge me-1">${a}</span>`).join('');
    }

    return `
        <div class="discovery-item" data-idx="${idx}" onclick="toggleSelect(${idx})">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong><i class="bi bi-pc-display me-2"></i>${ws.hostname}</strong>
                    <span class="text-muted ms-2">${ws.ip}</span>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="chk${idx}" onchange="toggleSelect(${idx})">
                </div>
            </div>
            <div class="mt-2">${specsHtml}</div>
            ${appsHtml ? `<div class="mt-2">${appsHtml}</div>` : ''}
        </div>
    `;
}

/**
 * Toggle selection of a discovered workstation
 * @param {number} idx - Index of workstation
 */
function toggleSelect(idx) {
    if (selectedForImport.has(idx)) {
        selectedForImport.delete(idx);
    } else {
        selectedForImport.add(idx);
    }

    document.querySelectorAll('.discovery-item').forEach((el, i) => {
        el.classList.toggle('selected', selectedForImport.has(i));
        const chk = document.getElementById('chk' + i);
        if (chk) chk.checked = selectedForImport.has(i);
    });

    updateImportButton();
}

/**
 * Update the import button state
 */
function updateImportButton() {
    document.getElementById('selectedCount').textContent = selectedForImport.size;
    document.getElementById('importBtn').disabled = selectedForImport.size === 0;
}

/**
 * Import selected discovered workstations
 */
async function importSelected() {
    const toImport = Array.from(selectedForImport).map(idx => discoveredWorkstations[idx]);

    try {
        const data = await postJSON('/api/import-discovered', { workstations: toImport });

        if (data.success) {
            let message = `Imported ${data.imported} workstation(s)`;
            if (data.skipped > 0) {
                message += `. ${data.skipped} skipped (already exist)`;
            }
            showToast('Import Complete', message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast('Import Failed', 'Could not import workstations', 'error');
        }
    } catch (e) {
        showToast('Error', 'Import failed: ' + e.message, 'error');
    }
}

/* ============================================
   Edit Workstation
   ============================================ */

/**
 * Open the edit modal for a workstation
 * @param {HTMLElement} cardEl - The card element
 */
function openEditModal(cardEl) {
    const ws = JSON.parse(cardEl.dataset.ws);

    document.getElementById('editWsId').value = ws.id;
    document.getElementById('editName').value = ws.name || '';
    document.getElementById('editIp').value = ws.ip || '';
    document.getElementById('editGpu').value = ws.gpu || '';
    document.getElementById('editCpu').value = ws.cpu || '';

    // Set select values
    const ramSelect = document.getElementById('editRam');
    ramSelect.value = ws.ram || '';

    const osSelect = document.getElementById('editOs');
    osSelect.value = ws.os || '';

    const groupSelect = document.getElementById('editGroup');
    groupSelect.value = ws.group || '';

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
}

/**
 * Save workstation changes
 */
async function saveWorkstation() {
    const id = document.getElementById('editWsId').value;
    const data = {
        name: document.getElementById('editName').value.trim(),
        gpu: document.getElementById('editGpu').value.trim() || null,
        ram: document.getElementById('editRam').value || null,
        os: document.getElementById('editOs').value || null,
        cpu: document.getElementById('editCpu').value.trim() || null,
        group: document.getElementById('editGroup').value || null
    };

    try {
        const res = await putJSON(`/api/workstations/${id}`, data);

        if (res.success) {
            showToast('Saved', 'Workstation updated successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Error', 'Failed to save changes', 'error');
        }
    } catch (e) {
        showToast('Error', 'Failed to save: ' + e.message, 'error');
    }
}

/**
 * Show the new group input field
 */
function showNewGroupInput() {
    document.getElementById('newGroupInput').classList.remove('d-none');
    document.getElementById('newGroupName').focus();
}

/**
 * Hide the new group input field
 */
function hideNewGroupInput() {
    document.getElementById('newGroupInput').classList.add('d-none');
    document.getElementById('newGroupName').value = '';
    document.getElementById('newGroupIcon').value = 'bi-folder';
    // Reset icon preview
    const preview = document.getElementById('newGroupIconPreview');
    preview.className = 'bi bi-folder';
}

/**
 * Open icon picker for new group
 */
async function pickNewGroupIcon() {
    const currentIcon = document.getElementById('newGroupIcon').value;
    const icon = await showIconPicker(currentIcon);
    if (icon) {
        document.getElementById('newGroupIcon').value = icon;
        document.getElementById('newGroupIconPreview').className = `bi ${icon}`;
    }
}

/**
 * Edit an existing group's icon
 * @param {string} groupName - Name of the group to edit
 */
async function editGroupIcon(groupName) {
    // Get current icon from the header
    const header = document.querySelector(`[data-group="${groupName}"]`);
    const iconEl = header?.querySelector('.group-icon');
    const currentIcon = iconEl?.className.match(/bi-[\w-]+/)?.[0] || 'bi-folder';

    const icon = await showIconPicker(currentIcon);
    if (icon) {
        try {
            await putJSON(`/api/groups/${encodeURIComponent(groupName)}`, { icon: icon });
            showToast('Updated', `Icon updated for "${groupName}"`, 'success');
            setTimeout(() => location.reload(), 800);
        } catch (e) {
            showToast('Error', 'Failed to update icon', 'error');
        }
    }
}

/**
 * Add a new group to the select dropdown and save its icon
 */
async function addNewGroup() {
    const input = document.getElementById('newGroupName');
    const iconSelect = document.getElementById('newGroupIcon');
    const groupName = input.value.trim();
    const iconClass = iconSelect.value;

    if (!groupName) {
        showToast('Error', 'Please enter a group name', 'error');
        return;
    }

    const select = document.getElementById('editGroup');

    // Check if group already exists
    for (const opt of select.options) {
        if (opt.value.toLowerCase() === groupName.toLowerCase()) {
            select.value = opt.value;
            hideNewGroupInput();
            return;
        }
    }

    // Save the group icon to the API
    try {
        await putJSON(`/api/groups/${encodeURIComponent(groupName)}`, { icon: iconClass });
    } catch (e) {
        console.warn('Could not save group icon:', e);
    }

    // Add new option and select it
    const option = document.createElement('option');
    option.value = groupName;
    option.textContent = groupName;
    select.add(option);
    select.value = groupName;

    hideNewGroupInput();
}

/* ============================================
   Initialization
   ============================================ */

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateAccentTextColor();
    refreshStatus();
});
