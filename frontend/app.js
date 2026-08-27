const state = {
    currentPage: "live-feeds",
    cameras: [],
    alerts: [],
    history: [],
    historyTotal: 0,
    historyPage: 1,
    historyLimit: 20,
    historyFilters: {
        camera_id: "",
        rule_name: "",
        severity: "",
        status: ""
    },
    selectedEvent: null,
    ws: null
};

// API Endpoints
const API_BASE = "http://localhost:8000/api";
const WS_URL = "ws://localhost:8000/ws/events";

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initModals();
    
    // Fetch initial data
    fetchCameras();
    fetchActiveAlerts();
    
    // Connect WebSocket
    connectWebSocket();
    
    // Render initial page
    renderPage(state.currentPage);
});

/* ==========================================================================
   NAVIGATION & ROUTING
   ========================================================================== */
function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            
            // Update active class
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");
            
            // Navigate
            const page = item.getAttribute("data-page");
            state.currentPage = page;
            renderPage(page);
        });
    });
}

function renderPage(page) {
    const titleEl = document.getElementById("page-title");
    const contentEl = document.getElementById("page-content");
    
    switch (page) {
        case "live-feeds":
            titleEl.textContent = "Live CCTV Feeds";
            renderLiveFeeds(contentEl);
            break;
        case "alert-history":
            titleEl.textContent = "Alert History";
            renderAlertHistory(contentEl);
            break;
        case "system-settings":
            titleEl.textContent = "System Settings";
            renderPlaceholderPage(contentEl, "System Settings will be implemented in the next milestone.");
            break;
        case "demo-sandbox":
            titleEl.textContent = "Demo Sandbox";
            renderDemoSandbox(contentEl);
            break;
        case "executive-summary":
            titleEl.textContent = "Executive Summary";
            renderPlaceholderPage(contentEl, "Executive Summary analytics will be implemented in the next milestone.");
            break;
    }
}

function renderPlaceholderPage(container, message) {
    container.innerHTML = `<div class="empty-state">${message}</div>`;
}

/* ==========================================================================
   ALERT HISTORY PAGE
   ========================================================================== */
function renderAlertHistory(container) {
    const template = document.getElementById("alert-history-template");
    container.innerHTML = '';
    container.appendChild(template.content.cloneNode(true));
    
    // Bind Filter Controls
    document.getElementById("apply-filters-btn").addEventListener("click", () => {
        state.historyFilters.camera_id = document.getElementById("filter-camera").value;
        state.historyFilters.rule_name = document.getElementById("filter-rule").value;
        state.historyFilters.severity = document.getElementById("filter-severity").value;
        state.historyFilters.status = document.getElementById("filter-status").value;
        state.historyPage = 1;
        fetchHistory();
    });
    
    // Populate Camera Dropdown
    const camSelect = document.getElementById("filter-camera");
    state.cameras.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        camSelect.appendChild(opt);
    });
    
    // Set existing filter values
    document.getElementById("filter-camera").value = state.historyFilters.camera_id;
    // Map rule_name manually since the select is hardcoded by rule_name but API expects rule_id or we filter locally.
    // Wait, our backend /api/events filter supports rule_id, but the dropdown has rule_names.
    // We will find rule_id dynamically if needed or filter after fetching if the API doesn't support rule_name.
    // Let's rely on standard dropdown values.
    document.getElementById("filter-rule").value = state.historyFilters.rule_name;
    document.getElementById("filter-severity").value = state.historyFilters.severity;
    document.getElementById("filter-status").value = state.historyFilters.status;
    
    // Bind Pagination
    document.getElementById("page-prev").addEventListener("click", () => {
        if(state.historyPage > 1) {
            state.historyPage--;
            fetchHistory();
        }
    });
    
    document.getElementById("page-next").addEventListener("click", () => {
        if(state.history.length === state.historyLimit) {
            state.historyPage++;
            fetchHistory();
        }
    });

    fetchHistory();
}

function renderHistoryTable() {
    if (state.currentPage !== 'alert-history') return;
    
    const tbody = document.getElementById("history-tbody");
    const emptyState = document.getElementById("history-empty");
    const totalEl = document.getElementById("history-total");
    
    tbody.innerHTML = '';
    
    if (state.history.length === 0) {
        emptyState.classList.remove("hidden");
        document.getElementById("page-prev").disabled = true;
        document.getElementById("page-next").disabled = true;
        totalEl.textContent = 0;
        return;
    }
    
    emptyState.classList.add("hidden");
    totalEl.textContent = state.historyTotal || state.history.length;
    
    state.history.forEach(event => {
        const tr = document.createElement("tr");
        
        const date = new Date(event.timestamp).toLocaleString();
        
        tr.innerHTML = `
            <td>${date}</td>
            <td>Camera ${event.camera_id}</td>
            <td>${event.rule_name || 'N/A'}</td>
            <td><span class="severity-badge severity-${event.severity}">${event.severity}</span></td>
            <td>${event.zone || 'N/A'}</td>
            <td><span class="status-badge ${event.status === 'RESOLVED' ? 'connected' : 'disconnected'}">${event.status}</span></td>
            <td class="event-id-cell">${event.event_id.split('-')[0]}...</td>
            <td class="actions">
                <button class="btn secondary view-btn" data-id="${event.event_id}">View</button>
                ${event.status !== 'RESOLVED' ? `<button class="btn primary ack-btn" data-id="${event.event_id}">Resolve</button>` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    // Pagination state
    document.getElementById("page-info").textContent = `Page ${state.historyPage}`;
    document.getElementById("page-prev").disabled = state.historyPage === 1;
    document.getElementById("page-next").disabled = state.history.length < state.historyLimit;
    
    // Attach action handlers
    document.querySelectorAll('#history-tbody .view-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            openEventModal(e.target.getAttribute('data-id'));
        });
    });
    
    document.querySelectorAll('#history-tbody .ack-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            resolveEvent(e.target.getAttribute('data-id'));
        });
    });
}

/* ==========================================================================
   DEMO SANDBOX PAGE
   ========================================================================== */
let sandboxPollInterval = null;

function renderDemoSandbox(container) {
    const template = document.getElementById("demo-sandbox-template");
    container.innerHTML = '';
    container.appendChild(template.content.cloneNode(true));
    
    // Clear any existing polling
    if (sandboxPollInterval) {
        clearInterval(sandboxPollInterval);
        sandboxPollInterval = null;
    }

    const uploadBtn = document.getElementById("sandbox-upload-btn");
    const fileInput = document.getElementById("sandbox-file-input");
    const uploadBox = document.getElementById("sandbox-upload-box");
    const statusBox = document.getElementById("sandbox-status-box");
    const videoBox = document.getElementById("sandbox-video-box");
    
    uploadBtn.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Hide upload box, show status box
        uploadBox.classList.add("hidden");
        statusBox.classList.remove("hidden");
        videoBox.classList.add("hidden");
        
        document.getElementById("sandbox-status-text").textContent = "UPLOADING...";
        document.getElementById("sandbox-progress-bar").style.width = "0%";
        document.getElementById("sandbox-frames").textContent = "Frames: 0/0";
        document.getElementById("sandbox-events").textContent = "Events Generated: 0";

        // Upload
        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(`${API_BASE}/sandbox/upload`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) throw new Error("Upload failed");

            const data = await response.json();
            const jobId = data.job_id;
            
            // Start polling
            pollSandboxJob(jobId);
        } catch (err) {
            console.error(err);
            document.getElementById("sandbox-status-text").textContent = "ERROR: UPLOAD FAILED";
            document.getElementById("sandbox-status-text").style.color = "var(--status-red)";
        }
    });
}

async function pollSandboxJob(jobId) {
    sandboxPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/sandbox/jobs/${jobId}?t=${Date.now()}`);
            if (!res.ok) return;

            const job = await res.json();
            
            // Update UI
            document.getElementById("sandbox-status-text").textContent = job.status.replace(/_/g, " ");
            document.getElementById("sandbox-progress-bar").style.width = `${job.progress}%`;
            document.getElementById("sandbox-frames").textContent = `Frames: ${job.processed_frames}/${job.total_frames}`;
            document.getElementById("sandbox-events").textContent = `Events Generated: ${job.events_generated}`;

            if (job.status === "AI_PLAYBACK_ACTIVE" || job.status === "COMPLETED") {
                clearInterval(sandboxPollInterval);
                sandboxPollInterval = null;
                
                // Show Video
                const videoBox = document.getElementById("sandbox-video-box");
                const videoPlayer = document.getElementById("sandbox-video-player");
                
                videoBox.classList.remove("hidden");
                // Prepend API_BASE correctly (removing /api from output_video if needed or handle it)
                // job.output_video is "/api/sandbox/video/..."
                // So full URL is just domain + job.output_video
                videoPlayer.src = `http://localhost:8000${job.output_video}`;
                videoPlayer.play();
                
                // Refresh history/stats so the user sees the new events
                fetchHistory();
            } else if (job.status === "FAILED") {
                clearInterval(sandboxPollInterval);
                sandboxPollInterval = null;
                document.getElementById("sandbox-status-text").style.color = "var(--status-red)";
                document.getElementById("sandbox-status-text").textContent = `ERROR: ${job.error || "Processing Failed"}`;
            }

        } catch (err) {
            console.error("Polling error", err);
        }
    }, 2000);
}

/* ==========================================================================
   LIVE FEEDS PAGE
   ========================================================================== */
function renderLiveFeeds(container) {
    // Actions Row
    const actionsRow = document.createElement('div');
    actionsRow.className = 'page-actions';
    
    const addCameraBtn = document.createElement('button');
    addCameraBtn.className = 'btn primary';
    addCameraBtn.textContent = '+ Add Camera';
    addCameraBtn.onclick = openAddCameraModal;
    
    actionsRow.appendChild(addCameraBtn);
    
    // Grid
    const grid = document.createElement('div');
    grid.className = 'camera-grid';
    grid.id = 'camera-grid';
    
    container.innerHTML = '';
    container.appendChild(actionsRow);
    container.appendChild(grid);
    
    // Render Cameras
    renderCameraGrid();
}

function renderCameraGrid() {
    const grid = document.getElementById('camera-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    if (state.cameras.length === 0) {
        grid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1">No cameras configured. Click "+ Add Camera" to begin.</div>';
        return;
    }
    
    state.cameras.forEach(camera => {
        const card = document.createElement('div');
        card.className = 'camera-card';
        
        const isConnected = camera.status === "CONNECTED" || camera.status === "ACTIVE";
        const badgeClass = isConnected ? "connected" : "disconnected";
        const badgeText = isConnected ? "CONNECTED" : "DISCONNECTED";
        
        card.innerHTML = `
            <div class="camera-preview">
                <span class="placeholder">NO SIGNAL</span>
            </div>
            <div class="camera-info">
                <div class="camera-details">
                    <h4>${camera.name}</h4>
                    <p>${camera.source}</p>
                </div>
                <div class="status-badge ${badgeClass}">${badgeText}</div>
            </div>
        `;
        grid.appendChild(card);
    });
}

/* ==========================================================================
   LIVE ALERTS PANEL
   ========================================================================== */
function renderLiveAlerts() {
    const listEl = document.getElementById("alert-list");
    const countEl = document.getElementById("active-alert-count");
    
    if (!listEl || !countEl) return;
    
    countEl.textContent = state.alerts.length;
    listEl.innerHTML = '';
    
    if (state.alerts.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No active alerts.</div>';
        return;
    }
    
    // Sort newest first
    const sortedAlerts = [...state.alerts].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    sortedAlerts.forEach(alert => {
        const card = document.createElement('div');
        card.className = `alert-card severity-${alert.severity}`;
        
        const date = new Date(alert.timestamp).toLocaleTimeString();
        
        card.innerHTML = `
            <div class="alert-card-header">
                <span class="alert-rule">${alert.rule_name || 'Rule Alert'}</span>
                <span class="alert-time">${date}</span>
            </div>
            <div class="alert-meta">
                Camera ID: ${alert.camera_id} ${alert.zone ? `| Zone: ${alert.zone}` : ''}
            </div>
            <div class="alert-details">
                ${alert.details || 'No details provided.'}
            </div>
            <div class="alert-actions">
                <button class="btn secondary view-btn" data-id="${alert.event_id}">View Image</button>
                <button class="btn primary ack-btn" data-id="${alert.event_id}">Acknowledge</button>
            </div>
        `;
        
        listEl.appendChild(card);
    });
    
    // Attach listeners
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const id = e.target.getAttribute('data-id');
            openEventModal(id);
        });
    });
    
    document.querySelectorAll('.ack-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const id = e.target.getAttribute('data-id');
            resolveEvent(id);
        });
    });
}

/* ==========================================================================
   MODALS
   ========================================================================== */
function initModals() {
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('event-modal').classList.add('hidden');
            document.getElementById('add-camera-modal').classList.add('hidden');
        });
    });
    
    // Add Camera Form Submit
    document.getElementById('submit-camera-btn').addEventListener('click', () => {
        const name = document.getElementById('camera-name').value;
        const source = document.getElementById('camera-source').value;
        if(name && source) {
            addCamera(name, source);
        }
    });
    
    // Acknowledge from Modal
    document.getElementById('modal-acknowledge-btn').addEventListener('click', () => {
        if(state.selectedEvent) {
            resolveEvent(state.selectedEvent.event_id);
            document.getElementById('event-modal').classList.add('hidden');
        }
    });
}

function openAddCameraModal() {
    document.getElementById('add-camera-modal').classList.remove('hidden');
}

function openEventModal(eventId) {
    // Find event in either alerts or history
    let event = state.alerts.find(a => a.event_id === eventId);
    if (!event) event = state.history.find(a => a.event_id === eventId);
    
    if (!event) {
        // Fallback: Fetch from API if not locally cached
        fetch(`${API_BASE}/events/${eventId}`)
            .then(res => res.json())
            .then(data => {
                state.selectedEvent = data;
                populateModal(data);
            })
            .catch(err => console.error("Event not found", err));
        return;
    }
    
    state.selectedEvent = event;
    populateModal(event);
}

function populateModal(event) {
    document.getElementById('modal-severity').textContent = event.severity;
    document.getElementById('modal-severity').className = `severity-badge severity-${event.severity}`;
    
    const statusEl = document.getElementById('modal-status');
    statusEl.textContent = event.status;
    statusEl.className = `status-badge ${event.status === 'RESOLVED' ? 'connected' : 'disconnected'}`;
    
    document.getElementById('modal-rule-name').textContent = event.rule_name || "Rule Alert";
    document.getElementById('modal-timestamp').textContent = new Date(event.timestamp).toLocaleString();
    document.getElementById('modal-camera').textContent = `Camera ${event.camera_id} ${event.zone ? `| ${event.zone}` : ''}`;
    document.getElementById('modal-event-id').textContent = event.event_id;
    document.getElementById('modal-details-text').textContent = event.details || "No details provided.";
    
    const resolvedTimeEl = document.getElementById('modal-resolved-time');
    if (event.status === 'RESOLVED' && event.resolved_at) {
        resolvedTimeEl.textContent = `Resolved at: ${new Date(event.resolved_at).toLocaleString()}`;
        resolvedTimeEl.classList.remove('hidden');
    } else {
        resolvedTimeEl.classList.add('hidden');
    }
    
    const imgEl = document.getElementById('modal-image');
    const noImgEl = document.getElementById('modal-no-image');
    
    if (event.snapshot_path) {
        let cleanPath = event.snapshot_path;
        if(cleanPath.startsWith("storage/snapshots/")) {
            cleanPath = cleanPath.replace("storage/snapshots/", "");
        }
        
        imgEl.src = `${API_BASE}/snapshots/${cleanPath}`;
        imgEl.classList.remove('hidden');
        noImgEl.classList.add('hidden');
    } else {
        imgEl.classList.add('hidden');
        noImgEl.classList.remove('hidden');
    }
    
    const ackBtn = document.getElementById('modal-acknowledge-btn');
    if (event.status === 'RESOLVED') {
        ackBtn.classList.add('hidden');
    } else {
        ackBtn.classList.remove('hidden');
        ackBtn.disabled = false;
        ackBtn.textContent = "Resolve Event";
    }
    
    document.getElementById('modal-feedback').textContent = "";
    document.getElementById('event-modal').classList.remove('hidden');
}

/* ==========================================================================
   API CALLS
   ========================================================================== */
async function fetchCameras() {
    try {
        const response = await fetch(`${API_BASE}/cameras`);
        const data = await response.json();
        state.cameras = data;
        if(state.currentPage === 'live-feeds') {
            renderCameraGrid();
        }
    } catch (e) {
        console.error("Failed to fetch cameras", e);
    }
}

async function addCamera(name, source) {
    try {
        const response = await fetch(`${API_BASE}/cameras/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, source, source_type: "VIDEO" })
        });
        if(response.ok) {
            document.getElementById('add-camera-modal').classList.add('hidden');
            document.getElementById('camera-name').value = '';
            document.getElementById('camera-source').value = '';
            fetchCameras();
        }
    } catch (e) {
        console.error("Failed to add camera", e);
    }
}

async function fetchActiveAlerts() {
    try {
        const response = await fetch(`${API_BASE}/events/active`);
        const data = await response.json();
        state.alerts = data;
        renderLiveAlerts();
    } catch (e) {
        console.error("Failed to fetch active alerts", e);
    }
}

async function fetchHistory() {
    try {
        const offset = (state.historyPage - 1) * state.historyLimit;
        let url = `${API_BASE}/events?limit=${state.historyLimit}&offset=${offset}`;
        
        if (state.historyFilters.camera_id) url += `&camera_id=${state.historyFilters.camera_id}`;
        if (state.historyFilters.severity) url += `&severity=${state.historyFilters.severity}`;
        if (state.historyFilters.status) url += `&status=${state.historyFilters.status}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        // Local filtering for rule_name if the API doesn't support rule_name natively
        let filteredData = data;
        if (state.historyFilters.rule_name) {
            filteredData = data.filter(e => e.rule_name === state.historyFilters.rule_name);
        }
        
        state.history = filteredData;
        
        // Fetch stats to get approximate total (since API /events doesn't return count directly)
        const statsRes = await fetch(`${API_BASE}/events/stats`);
        if (statsRes.ok) {
            const stats = await statsRes.json();
            state.historyTotal = stats.total_events;
        }
        
        renderHistoryTable();
    } catch (e) {
        console.error("Failed to fetch history", e);
    }
}

async function resolveEvent(eventId) {
    const btn = document.getElementById('modal-acknowledge-btn');
    if (btn) btn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/events/${eventId}/resolve`, {
            method: 'PATCH'
        });
        
        if(response.ok) {
            const resolvedData = await response.json();
            
            // Remove from active alerts local state
            state.alerts = state.alerts.filter(a => a.event_id !== eventId);
            
            // Update history local state if present
            const histIdx = state.history.findIndex(h => h.event_id === eventId);
            if (histIdx >= 0) {
                state.history[histIdx] = resolvedData;
            }
            
            // Update currently selected event
            if (state.selectedEvent && state.selectedEvent.event_id === eventId) {
                state.selectedEvent = resolvedData;
                populateModal(resolvedData); // Update modal UI if open
                
                const feedback = document.getElementById('modal-feedback');
                feedback.textContent = "Event successfully resolved.";
                feedback.style.color = "var(--status-green)";
                setTimeout(() => { if(feedback) feedback.textContent = ""; }, 3000);
            }
            
            renderLiveAlerts();
            renderHistoryTable();
        } else {
            const feedback = document.getElementById('modal-feedback');
            if (feedback) {
                feedback.textContent = "Failed to resolve event.";
                feedback.style.color = "var(--status-red)";
                if (btn) btn.disabled = false;
            }
        }
    } catch (e) {
        console.error("Failed to resolve event", e);
        const feedback = document.getElementById('modal-feedback');
        if (feedback) {
            feedback.textContent = "Error communicating with server.";
            feedback.style.color = "var(--status-red)";
            if (btn) btn.disabled = false;
        }
    }
}

/* ==========================================================================
   WEBSOCKET
   ========================================================================== */
function connectWebSocket() {
    state.ws = new WebSocket(WS_URL);
    
    state.ws.onopen = () => {
        console.log("WebSocket Connected");
    };
    
    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error("Error parsing WS message", e);
        }
    };
    
    state.ws.onclose = () => {
        console.log("WebSocket Disconnected. Reconnecting in 3s...");
        setTimeout(connectWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    console.log("WS Event Received:", data.status, data.event_id);
    
    if (data.status === "ALERT_SENT" || data.status === "MONITORING") {
        const existingIndex = state.alerts.findIndex(a => a.event_id === data.event_id);
        
        if (existingIndex >= 0) {
            state.alerts[existingIndex] = data; // Escalation / update details
        } else {
            state.alerts.unshift(data); // New alert, push to top
        }
        
        // Update history if active
        const histIdx = state.history.findIndex(h => h.event_id === data.event_id);
        if (histIdx >= 0) {
            state.history[histIdx] = data;
            renderHistoryTable();
        } else if (state.currentPage === 'alert-history' && state.historyPage === 1) {
            // New event on page 1
            if (!state.historyFilters.status || state.historyFilters.status === "ACTIVE") {
                state.history.unshift(data);
                if (state.history.length > state.historyLimit) state.history.pop();
                renderHistoryTable();
            }
        }
    } 
    else if (data.status === "RESOLVED") {
        // Remove from active list
        state.alerts = state.alerts.filter(a => a.event_id !== data.event_id);
        
        // Update history if active
        const histIdx = state.history.findIndex(h => h.event_id === data.event_id);
        if (histIdx >= 0) {
            state.history[histIdx] = data;
            renderHistoryTable();
        }
    }
    
    // Re-render live alerts panel
    renderLiveAlerts();
}
