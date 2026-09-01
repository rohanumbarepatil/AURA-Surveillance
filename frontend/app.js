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

/* ==========================================================================
   PRODUCTION API CONFIGURATION
   ========================================================================== */

// Render Backend
const BACKEND_URL = "https://aura-surveillance.onrender.com";

// REST API
const API_BASE = "https://aura-surveillance.onrender.com/api";

// WebSocket
const WS_URL = "wss://aura-surveillance.onrender.com/ws/events";


/* ==========================================================================
   INITIAL LOAD
   ========================================================================== */

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

            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");

            const page = item.getAttribute("data-page");

            state.currentPage = page;
            renderPage(page);
        });
    });
}


function renderPage(page) {
    const titleEl = document.getElementById("page-title");
    const contentEl = document.getElementById("page-content");

    if (!titleEl || !contentEl) return;

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
            renderPlaceholderPage(
                contentEl,
                "System Settings will be implemented in the next milestone."
            );
            break;

        case "demo-sandbox":
            titleEl.textContent = "Demo Sandbox";
            renderDemoSandbox(contentEl);
            break;

        case "executive-summary":
            titleEl.textContent = "Executive Summary";
            renderPlaceholderPage(
                contentEl,
                "Executive Summary analytics will be implemented in the next milestone."
            );
            break;
    }
}


function renderPlaceholderPage(container, message) {
    container.innerHTML = `
        <div class="empty-state">
            ${message}
        </div>
    `;
}


/* ==========================================================================
   ALERT HISTORY PAGE
   ========================================================================== */

function renderAlertHistory(container) {

    const template = document.getElementById("alert-history-template");

    if (!template) {
        container.innerHTML = `
            <div class="empty-state">
                Alert history template not found.
            </div>
        `;
        return;
    }

    container.innerHTML = "";
    container.appendChild(template.content.cloneNode(true));

    const applyFiltersBtn = document.getElementById("apply-filters-btn");

    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener("click", () => {

            state.historyFilters.camera_id =
                document.getElementById("filter-camera")?.value || "";

            state.historyFilters.rule_name =
                document.getElementById("filter-rule")?.value || "";

            state.historyFilters.severity =
                document.getElementById("filter-severity")?.value || "";

            state.historyFilters.status =
                document.getElementById("filter-status")?.value || "";

            state.historyPage = 1;

            fetchHistory();
        });
    }


    /* Camera dropdown */

    const camSelect = document.getElementById("filter-camera");

    if (camSelect) {

        state.cameras.forEach(camera => {

            const opt = document.createElement("option");

            opt.value = camera.id;
            opt.textContent = camera.name;

            camSelect.appendChild(opt);
        });

        camSelect.value = state.historyFilters.camera_id;
    }


    const ruleSelect = document.getElementById("filter-rule");
    const severitySelect = document.getElementById("filter-severity");
    const statusSelect = document.getElementById("filter-status");

    if (ruleSelect) {
        ruleSelect.value = state.historyFilters.rule_name;
    }

    if (severitySelect) {
        severitySelect.value = state.historyFilters.severity;
    }

    if (statusSelect) {
        statusSelect.value = state.historyFilters.status;
    }


    /* Pagination */

    const prevBtn = document.getElementById("page-prev");
    const nextBtn = document.getElementById("page-next");

    if (prevBtn) {
        prevBtn.addEventListener("click", () => {

            if (state.historyPage > 1) {
                state.historyPage--;
                fetchHistory();
            }

        });
    }


    if (nextBtn) {
        nextBtn.addEventListener("click", () => {

            if (state.history.length === state.historyLimit) {
                state.historyPage++;
                fetchHistory();
            }

        });
    }


    fetchHistory();
}


function renderHistoryTable() {

    if (state.currentPage !== "alert-history") return;

    const tbody = document.getElementById("history-tbody");
    const emptyState = document.getElementById("history-empty");
    const totalEl = document.getElementById("history-total");

    if (!tbody) return;

    tbody.innerHTML = "";


    if (state.history.length === 0) {

        if (emptyState) {
            emptyState.classList.remove("hidden");
        }

        const prevBtn = document.getElementById("page-prev");
        const nextBtn = document.getElementById("page-next");

        if (prevBtn) prevBtn.disabled = true;
        if (nextBtn) nextBtn.disabled = true;

        if (totalEl) {
            totalEl.textContent = "0";
        }

        return;
    }


    if (emptyState) {
        emptyState.classList.add("hidden");
    }

    if (totalEl) {
        totalEl.textContent =
            state.historyTotal || state.history.length;
    }


    state.history.forEach(event => {

        const tr = document.createElement("tr");

        const date = event.timestamp
            ? new Date(event.timestamp).toLocaleString()
            : "N/A";

        const shortEventId =
            event.event_id
                ? `${event.event_id.split("-")[0]}...`
                : "N/A";


        tr.innerHTML = `
            <td>${date}</td>

            <td>
                Camera ${event.camera_id ?? "N/A"}
            </td>

            <td>
                ${event.rule_name || "N/A"}
            </td>

            <td>
                <span class="severity-badge severity-${event.severity || "UNKNOWN"}">
                    ${event.severity || "UNKNOWN"}
                </span>
            </td>

            <td>
                ${event.zone || "N/A"}
            </td>

            <td>
                <span class="status-badge ${
                    event.status === "RESOLVED"
                        ? "connected"
                        : "disconnected"
                }">
                    ${event.status || "UNKNOWN"}
                </span>
            </td>

            <td class="event-id-cell">
                ${shortEventId}
            </td>

            <td class="actions">

                <button
                    class="btn secondary view-btn"
                    data-id="${event.event_id}">
                    View
                </button>

                ${
                    event.status !== "RESOLVED"
                        ? `
                            <button
                                class="btn primary ack-btn"
                                data-id="${event.event_id}">
                                Resolve
                            </button>
                        `
                        : ""
                }

            </td>
        `;

        tbody.appendChild(tr);
    });


    const pageInfo = document.getElementById("page-info");
    const prevBtn = document.getElementById("page-prev");
    const nextBtn = document.getElementById("page-next");


    if (pageInfo) {
        pageInfo.textContent =
            `Page ${state.historyPage}`;
    }

    if (prevBtn) {
        prevBtn.disabled =
            state.historyPage === 1;
    }

    if (nextBtn) {
        nextBtn.disabled =
            state.history.length < state.historyLimit;
    }


    /* View buttons */

    document
        .querySelectorAll("#history-tbody .view-btn")
        .forEach(btn => {

            btn.addEventListener("click", e => {

                const id =
                    e.currentTarget.getAttribute("data-id");

                openEventModal(id);
            });
        });


    /* Resolve buttons */

    document
        .querySelectorAll("#history-tbody .ack-btn")
        .forEach(btn => {

            btn.addEventListener("click", e => {

                const id =
                    e.currentTarget.getAttribute("data-id");

                resolveEvent(id);
            });
        });
}


/* ==========================================================================
   DEMO SANDBOX
   ========================================================================== */

let sandboxPollInterval = null;


function renderDemoSandbox(container) {

    const template =
        document.getElementById("demo-sandbox-template");

    if (!template) {
        container.innerHTML = `
            <div class="empty-state">
                Demo Sandbox template not found.
            </div>
        `;
        return;
    }


    container.innerHTML = "";

    container.appendChild(
        template.content.cloneNode(true)
    );


    if (sandboxPollInterval) {
        clearInterval(sandboxPollInterval);
        sandboxPollInterval = null;
    }


    const uploadBtn =
        document.getElementById("sandbox-upload-btn");

    const fileInput =
        document.getElementById("sandbox-file-input");

    const uploadBox =
        document.getElementById("sandbox-upload-box");

    const statusBox =
        document.getElementById("sandbox-status-box");

    const videoBox =
        document.getElementById("sandbox-video-box");


    if (!uploadBtn || !fileInput) return;


    uploadBtn.addEventListener("click", () => {
        fileInput.click();
    });


    fileInput.addEventListener("change", async e => {

        const file = e.target.files[0];

        if (!file) return;


        uploadBox?.classList.add("hidden");
        statusBox?.classList.remove("hidden");
        videoBox?.classList.add("hidden");


        const statusText =
            document.getElementById("sandbox-status-text");

        const progressBar =
            document.getElementById("sandbox-progress-bar");

        const framesEl =
            document.getElementById("sandbox-frames");

        const eventsEl =
            document.getElementById("sandbox-events");


        if (statusText) {
            statusText.textContent = "UPLOADING...";
        }

        if (progressBar) {
            progressBar.style.width = "0%";
        }

        if (framesEl) {
            framesEl.textContent = "Frames: 0/0";
        }

        if (eventsEl) {
            eventsEl.textContent = "Events Generated: 0";
        }


        const formData = new FormData();

        formData.append("file", file);


        try {

            const response = await fetch(
                `${API_BASE}/sandbox/upload`,
                {
                    method: "POST",
                    body: formData
                }
            );


            if (!response.ok) {

                const errorText =
                    await response.text().catch(() => "");

                throw new Error(
                    `Upload failed (${response.status}) ${errorText}`
                );
            }


            const data = await response.json();

            const jobId = data.job_id;

            if (!jobId) {
                throw new Error(
                    "Backend did not return job_id"
                );
            }


            pollSandboxJob(jobId);

        } catch (err) {

            console.error(
                "Sandbox upload error:",
                err
            );

            if (statusText) {

                statusText.textContent =
                    "ERROR: UPLOAD FAILED";

                statusText.style.color =
                    "var(--status-red)";
            }
        }

    });
}


async function pollSandboxJob(jobId) {

    if (sandboxPollInterval) {
        clearInterval(sandboxPollInterval);
    }


    sandboxPollInterval = setInterval(async () => {

        try {

            const res = await fetch(
                `${API_BASE}/sandbox/jobs/${jobId}?t=${Date.now()}`
            );


            if (!res.ok) return;


            const job = await res.json();


            const statusText =
                document.getElementById(
                    "sandbox-status-text"
                );

            const progressBar =
                document.getElementById(
                    "sandbox-progress-bar"
                );

            const framesEl =
                document.getElementById(
                    "sandbox-frames"
                );

            const eventsEl =
                document.getElementById(
                    "sandbox-events"
                );


            if (statusText) {
                statusText.textContent =
                    (job.status || "")
                        .replace(/_/g, " ");
            }


            if (progressBar) {
                progressBar.style.width =
                    `${job.progress || 0}%`;
            }


            if (framesEl) {

                framesEl.textContent =
                    `Frames: ${
                        job.processed_frames || 0
                    }/${
                        job.total_frames || 0
                    }`;
            }


            if (eventsEl) {

                eventsEl.textContent =
                    `Events Generated: ${
                        job.events_generated || 0
                    }`;
            }


            if (
                job.status === "AI_PLAYBACK_ACTIVE" ||
                job.status === "COMPLETED"
            ) {

                clearInterval(
                    sandboxPollInterval
                );

                sandboxPollInterval = null;


                const videoBox =
                    document.getElementById(
                        "sandbox-video-box"
                    );

                const videoPlayer =
                    document.getElementById(
                        "sandbox-video-player"
                    );


                if (videoBox) {
                    videoBox.classList.remove("hidden");
                }


                if (videoPlayer && job.output_video) {

                    let videoUrl;

                    if (
                        job.output_video.startsWith("http://") ||
                        job.output_video.startsWith("https://")
                    ) {
                        videoUrl =
                            job.output_video;
                    } else {
                        videoUrl =
                            `${BACKEND_URL}${job.output_video}`;
                    }


                    videoPlayer.src = videoUrl;

                    videoPlayer.load();

                    videoPlayer.play().catch(() => {});
                }


                fetchHistory();
                fetchActiveAlerts();

            }


            else if (job.status === "FAILED") {

                clearInterval(
                    sandboxPollInterval
                );

                sandboxPollInterval = null;


                if (statusText) {

                    statusText.style.color =
                        "var(--status-red)";

                    statusText.textContent =
                        `ERROR: ${
                            job.error ||
                            "Processing Failed"
                        }`;
                }
            }


        } catch (err) {

            console.error(
                "Polling error:",
                err
            );
        }

    }, 2000);
}


/* ==========================================================================
   LIVE FEEDS
   ========================================================================== */

function renderLiveFeeds(container) {

    const actionsRow =
        document.createElement("div");

    actionsRow.className =
        "page-actions";


    const addCameraBtn =
        document.createElement("button");

    addCameraBtn.className =
        "btn primary";

    addCameraBtn.textContent =
        "+ Add Camera";

    addCameraBtn.onclick =
        openAddCameraModal;


    actionsRow.appendChild(
        addCameraBtn
    );


    const grid =
        document.createElement("div");

    grid.className =
        "camera-grid";

    grid.id =
        "camera-grid";


    container.innerHTML = "";

    container.appendChild(
        actionsRow
    );

    container.appendChild(
        grid
    );


    renderCameraGrid();
}


function renderCameraGrid() {

    const grid =
        document.getElementById(
            "camera-grid"
        );

    if (!grid) return;


    grid.innerHTML = "";


    if (state.cameras.length === 0) {

        grid.innerHTML = `
            <div
                class="empty-state"
                style="grid-column:1/-1">
                No cameras configured.
                Click "+ Add Camera" to begin.
            </div>
        `;

        return;
    }


    state.cameras.forEach(camera => {

        const card =
            document.createElement("div");

        card.className =
            "camera-card";


        const isConnected =
            camera.status === "CONNECTED" ||
            camera.status === "ACTIVE";


        const badgeClass =
            isConnected
                ? "connected"
                : "disconnected";


        const badgeText =
            isConnected
                ? "CONNECTED"
                : "DISCONNECTED";


        card.innerHTML = `
            <div class="camera-preview">
                <span class="placeholder">
                    NO SIGNAL
                </span>
            </div>

            <div class="camera-info">

                <div class="camera-details">

                    <h4>
                        ${camera.name || "Unnamed Camera"}
                    </h4>

                    <p>
                        ${camera.source || "N/A"}
                    </p>

                </div>

                <div class="status-badge ${badgeClass}">
                    ${badgeText}
                </div>

            </div>
        `;


        grid.appendChild(card);
    });
}


/* ==========================================================================
   LIVE ALERTS
   ========================================================================== */

function renderLiveAlerts() {

    const listEl =
        document.getElementById(
            "alert-list"
        );

    const countEl =
        document.getElementById(
            "active-alert-count"
        );


    if (!listEl || !countEl) return;


    countEl.textContent =
        state.alerts.length;


    listEl.innerHTML = "";


    if (state.alerts.length === 0) {

        listEl.innerHTML = `
            <div class="empty-state">
                No active alerts.
            </div>
        `;

        return;
    }


    const sortedAlerts =
        [...state.alerts].sort(
            (a, b) =>
                new Date(b.timestamp) -
                new Date(a.timestamp)
        );


    sortedAlerts.forEach(alert => {

        const card =
            document.createElement("div");

        card.className =
            `alert-card severity-${alert.severity}`;


        const date =
            alert.timestamp
                ? new Date(
                    alert.timestamp
                ).toLocaleTimeString()
                : "N/A";


        card.innerHTML = `

            <div class="alert-card-header">

                <span class="alert-rule">
                    ${alert.rule_name || "Rule Alert"}
                </span>

                <span class="alert-time">
                    ${date}
                </span>

            </div>


            <div class="alert-meta">

                Camera ID:
                ${alert.camera_id ?? "N/A"}

                ${
                    alert.zone
                        ? `| Zone: ${alert.zone}`
                        : ""
                }

            </div>


            <div class="alert-details">

                ${
                    alert.details ||
                    "No details provided."
                }

            </div>


            <div class="alert-actions">

                <button
                    class="btn secondary view-btn"
                    data-id="${alert.event_id}">
                    View Image
                </button>

                <button
                    class="btn primary ack-btn"
                    data-id="${alert.event_id}">
                    Acknowledge
                </button>

            </div>
        `;


        listEl.appendChild(card);
    });


    document
        .querySelectorAll(".view-btn")
        .forEach(btn => {

            btn.addEventListener(
                "click",
                e => {

                    const id =
                        e.currentTarget
                            .getAttribute("data-id");

                    openEventModal(id);
                }
            );
        });


    document
        .querySelectorAll(".ack-btn")
        .forEach(btn => {

            btn.addEventListener(
                "click",
                e => {

                    const id =
                        e.currentTarget
                            .getAttribute("data-id");

                    resolveEvent(id);
                }
            );
        });
}


/* ==========================================================================
   MODALS
   ========================================================================== */

function initModals() {

    document
        .querySelectorAll(".close-modal")
        .forEach(btn => {

            btn.addEventListener(
                "click",
                () => {

                    document
                        .getElementById(
                            "event-modal"
                        )
                        ?.classList.add("hidden");

                    document
                        .getElementById(
                            "add-camera-modal"
                        )
                        ?.classList.add("hidden");
                }
            );
        });


    const submitBtn =
        document.getElementById(
            "submit-camera-btn"
        );


    if (submitBtn) {

        submitBtn.addEventListener(
            "click",
            () => {

                const name =
                    document.getElementById(
                        "camera-name"
                    )?.value.trim();

                const source =
                    document.getElementById(
                        "camera-source"
                    )?.value.trim();


                if (name && source) {
                    addCamera(
                        name,
                        source
                    );
                }
            }
        );
    }


    const acknowledgeBtn =
        document.getElementById(
            "modal-acknowledge-btn"
        );


    if (acknowledgeBtn) {

        acknowledgeBtn.addEventListener(
            "click",
            () => {

                if (state.selectedEvent) {

                    resolveEvent(
                        state.selectedEvent.event_id
                    );

                    document
                        .getElementById(
                            "event-modal"
                        )
                        ?.classList.add("hidden");
                }
            }
        );
    }
}


function openAddCameraModal() {

    document
        .getElementById(
            "add-camera-modal"
        )
        ?.classList.remove("hidden");
}


function openEventModal(eventId) {

    let event =
        state.alerts.find(
            a => a.event_id === eventId
        );


    if (!event) {

        event =
            state.history.find(
                a => a.event_id === eventId
            );
    }


    if (!event) {

        fetch(
            `${API_BASE}/events/${eventId}`
        )
            .then(res => {

                if (!res.ok) {
                    throw new Error(
                        `HTTP ${res.status}`
                    );
                }

                return res.json();
            })
            .then(data => {

                state.selectedEvent =
                    data;

                populateModal(data);
            })
            .catch(err =>
                console.error(
                    "Event not found:",
                    err
                )
            );

        return;
    }


    state.selectedEvent =
        event;

    populateModal(event);
}


function populateModal(event) {

    const severityEl =
        document.getElementById(
            "modal-severity"
        );


    if (severityEl) {

        severityEl.textContent =
            event.severity || "UNKNOWN";

        severityEl.className =
            `severity-badge severity-${
                event.severity || "UNKNOWN"
            }`;
    }


    const statusEl =
        document.getElementById(
            "modal-status"
        );


    if (statusEl) {

        statusEl.textContent =
            event.status || "UNKNOWN";

        statusEl.className =
            `status-badge ${
                event.status === "RESOLVED"
                    ? "connected"
                    : "disconnected"
            }`;
    }


    const ruleName =
        document.getElementById(
            "modal-rule-name"
        );

    if (ruleName) {
        ruleName.textContent =
            event.rule_name ||
            "Rule Alert";
    }


    const timestamp =
        document.getElementById(
            "modal-timestamp"
        );

    if (timestamp) {

        timestamp.textContent =
            event.timestamp
                ? new Date(
                    event.timestamp
                ).toLocaleString()
                : "N/A";
    }


    const cameraEl =
        document.getElementById(
            "modal-camera"
        );

    if (cameraEl) {

        cameraEl.textContent =
            `Camera ${
                event.camera_id ?? "N/A"
            } ${
                event.zone
                    ? `| ${event.zone}`
                    : ""
            }`;
    }


    const eventIdEl =
        document.getElementById(
            "modal-event-id"
        );

    if (eventIdEl) {
        eventIdEl.textContent =
            event.event_id || "N/A";
    }


    const detailsEl =
        document.getElementById(
            "modal-details-text"
        );

    if (detailsEl) {

        detailsEl.textContent =
            event.details ||
            "No details provided.";
    }


    const resolvedTimeEl =
        document.getElementById(
            "modal-resolved-time"
        );


    if (resolvedTimeEl) {

        if (
            event.status === "RESOLVED" &&
            event.resolved_at
        ) {

            resolvedTimeEl.textContent =
                `Resolved at: ${
                    new Date(
                        event.resolved_at
                    ).toLocaleString()
                }`;

            resolvedTimeEl.classList.remove(
                "hidden"
            );

        } else {

            resolvedTimeEl.classList.add(
                "hidden"
            );
        }
    }


    /* Snapshot */

    const imgEl =
        document.getElementById(
            "modal-image"
        );

    const noImgEl =
        document.getElementById(
            "modal-no-image"
        );


    if (
        imgEl &&
        noImgEl &&
        event.snapshot_path
    ) {

        let cleanPath =
            event.snapshot_path;


        cleanPath =
            cleanPath.replace(
                /^\/+/,
                ""
            );


        cleanPath =
            cleanPath.replace(
                /^storage\/snapshots\//,
                ""
            );


        imgEl.src =
            `${API_BASE}/snapshots/${cleanPath}`;


        imgEl.classList.remove(
            "hidden"
        );

        noImgEl.classList.add(
            "hidden"
        );

    } else {

        imgEl?.classList.add(
            "hidden"
        );

        noImgEl?.classList.remove(
            "hidden"
        );
    }


    const ackBtn =
        document.getElementById(
            "modal-acknowledge-btn"
        );


    if (ackBtn) {

        if (event.status === "RESOLVED") {

            ackBtn.classList.add(
                "hidden"
            );

        } else {

            ackBtn.classList.remove(
                "hidden"
            );

            ackBtn.disabled = false;

            ackBtn.textContent =
                "Resolve Event";
        }
    }


    const feedback =
        document.getElementById(
            "modal-feedback"
        );

    if (feedback) {
        feedback.textContent = "";
    }


    document
        .getElementById("event-modal")
        ?.classList.remove("hidden");
}


/* ==========================================================================
   API CALLS
   ========================================================================== */

async function fetchCameras() {

    try {

        const response =
            await fetch(
                `${API_BASE}/cameras`
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        state.cameras =
            Array.isArray(data)
                ? data
                : [];


        if (
            state.currentPage ===
            "live-feeds"
        ) {

            renderCameraGrid();
        }


    } catch (e) {

        console.error(
            "Failed to fetch cameras:",
            e
        );
    }
}


async function addCamera(name, source) {

    try {

        const response =
            await fetch(
                `${API_BASE}/cameras/`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        name,
                        source,
                        source_type: "VIDEO"
                    })
                }
            );


        if (!response.ok) {

            const errorText =
                await response.text()
                    .catch(() => "");

            throw new Error(
                `HTTP ${response.status}: ${errorText}`
            );
        }


        document
            .getElementById(
                "add-camera-modal"
            )
            ?.classList.add("hidden");


        const nameInput =
            document.getElementById(
                "camera-name"
            );

        const sourceInput =
            document.getElementById(
                "camera-source"
            );


        if (nameInput) {
            nameInput.value = "";
        }

        if (sourceInput) {
            sourceInput.value = "";
        }


        await fetchCameras();


    } catch (e) {

        console.error(
            "Failed to add camera:",
            e
        );

        alert(
            "Failed to add camera. Please check the backend."
        );
    }
}


async function fetchActiveAlerts() {

    try {

        const response =
            await fetch(
                `${API_BASE}/events/active`
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        state.alerts =
            Array.isArray(data)
                ? data
                : [];


        renderLiveAlerts();


    } catch (e) {

        console.error(
            "Failed to fetch active alerts:",
            e
        );
    }
}


async function fetchHistory() {

    try {

        const offset =
            (state.historyPage - 1) *
            state.historyLimit;


        let url =
            `${API_BASE}/events` +
            `?limit=${state.historyLimit}` +
            `&offset=${offset}`;


        if (
            state.historyFilters.camera_id
        ) {

            url +=
                `&camera_id=${
                    encodeURIComponent(
                        state.historyFilters.camera_id
                    )
                }`;
        }


        if (
            state.historyFilters.severity
        ) {

            url +=
                `&severity=${
                    encodeURIComponent(
                        state.historyFilters.severity
                    )
                }`;
        }


        if (
            state.historyFilters.status
        ) {

            url +=
                `&status=${
                    encodeURIComponent(
                        state.historyFilters.status
                    )
                }`;
        }


        const response =
            await fetch(url);


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        let filteredData =
            Array.isArray(data)
                ? data
                : [];


        /* Local rule_name filtering */

        if (
            state.historyFilters.rule_name
        ) {

            filteredData =
                filteredData.filter(
                    e =>
                        e.rule_name ===
                        state.historyFilters.rule_name
                );
        }


        state.history =
            filteredData;


        /* Stats */

        try {

            const statsRes =
                await fetch(
                    `${API_BASE}/events/stats`
                );


            if (statsRes.ok) {

                const stats =
                    await statsRes.json();


                state.historyTotal =
                    stats.total_events || 0;
            }

        } catch (statsError) {

            console.warn(
                "Stats request failed:",
                statsError
            );
        }


        renderHistoryTable();


    } catch (e) {

        console.error(
            "Failed to fetch history:",
            e
        );
    }
}


async function resolveEvent(eventId) {

    const btn =
        document.getElementById(
            "modal-acknowledge-btn"
        );


    if (btn) {
        btn.disabled = true;
    }


    try {

        const response =
            await fetch(
                `${API_BASE}/events/${eventId}/resolve`,
                {
                    method: "PATCH"
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const resolvedData =
            await response.json();


        /* Remove from active alerts */

        state.alerts =
            state.alerts.filter(
                a =>
                    a.event_id !==
                    eventId
            );


        /* Update history */

        const histIdx =
            state.history.findIndex(
                h =>
                    h.event_id ===
                    eventId
            );


        if (histIdx >= 0) {

            state.history[histIdx] =
                resolvedData;
        }


        /* Update selected event */

        if (
            state.selectedEvent &&
            state.selectedEvent.event_id ===
                eventId
        ) {

            state.selectedEvent =
                resolvedData;


            populateModal(
                resolvedData
            );


            const feedback =
                document.getElementById(
                    "modal-feedback"
                );


            if (feedback) {

                feedback.textContent =
                    "Event successfully resolved.";

                feedback.style.color =
                    "var(--status-green)";


                setTimeout(() => {

                    feedback.textContent =
                        "";

                }, 3000);
            }
        }


        renderLiveAlerts();
        renderHistoryTable();


    } catch (e) {

        console.error(
            "Failed to resolve event:",
            e
        );


        const feedback =
            document.getElementById(
                "modal-feedback"
            );


        if (feedback) {

            feedback.textContent =
                "Error communicating with server.";

            feedback.style.color =
                "var(--status-red)";
        }


        if (btn) {
            btn.disabled = false;
        }
    }
}


/* ==========================================================================
   WEBSOCKET
   ========================================================================== */

function connectWebSocket() {

    try {

        if (
            state.ws &&
            (
                state.ws.readyState ===
                    WebSocket.OPEN ||
                state.ws.readyState ===
                    WebSocket.CONNECTING
            )
        ) {

            return;
        }


        console.log(
            "Connecting WebSocket:",
            WS_URL
        );


        state.ws =
            new WebSocket(WS_URL);


        state.ws.onopen = () => {

            console.log(
                "WebSocket Connected to Render"
            );
        };


        state.ws.onmessage = event => {

            try {

                const data =
                    JSON.parse(
                        event.data
                    );


                handleWebSocketMessage(
                    data
                );

            } catch (e) {

                console.error(
                    "Error parsing WS message:",
                    e
                );
            }
        };


        state.ws.onerror = error => {

            console.error(
                "WebSocket error:",
                error
            );
        };


        state.ws.onclose = () => {

            console.log(
                "WebSocket disconnected. Reconnecting in 5s..."
            );


            state.ws = null;


            setTimeout(() => {

                connectWebSocket();

            }, 5000);
        };


    } catch (error) {

        console.error(
            "WebSocket connection failed:",
            error
        );
    }
}


/* ==========================================================================
   WEBSOCKET MESSAGE HANDLER
   ========================================================================== */

function handleWebSocketMessage(data) {

    console.log(
        "WS Event Received:",
        data.status,
        data.event_id
    );


    if (
        data.status === "ALERT_SENT" ||
        data.status === "MONITORING"
    ) {

        const existingIndex =
            state.alerts.findIndex(
                a =>
                    a.event_id ===
                    data.event_id
            );


        if (existingIndex >= 0) {

            state.alerts[
                existingIndex
            ] = data;

        } else {

            state.alerts.unshift(data);
        }


        /* Update history */

        const histIdx =
            state.history.findIndex(
                h =>
                    h.event_id ===
                    data.event_id
            );


        if (histIdx >= 0) {

            state.history[
                histIdx
            ] = data;

            renderHistoryTable();

        } else if (
            state.currentPage ===
                "alert-history" &&
            state.historyPage === 1
        ) {

            if (
                !state.historyFilters.status ||
                state.historyFilters.status ===
                    "ACTIVE"
            ) {

                state.history.unshift(
                    data
                );


                if (
                    state.history.length >
                    state.historyLimit
                ) {

                    state.history.pop();
                }


                renderHistoryTable();
            }
        }

    }

    else if (
        data.status === "RESOLVED"
    ) {

        state.alerts =
            state.alerts.filter(
                a =>
                    a.event_id !==
                    data.event_id
            );


        const histIdx =
            state.history.findIndex(
                h =>
                    h.event_id ===
                    data.event_id
            );


        if (histIdx >= 0) {

            state.history[
                histIdx
            ] = data;

            renderHistoryTable();
        }
    }


    renderLiveAlerts();
}
