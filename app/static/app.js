/**
 * FIFA 2026 CrowdFlow Assist - Frontend Orchestration
 * Performs WCAG-aware UI updates, handles inputs safely, and draws the interactive SVG stadium map.
 */

// Coordinates for rendering the stadium graph nodes in the 500x380 SVG viewbox
const NODE_COORDINATES = {
    // Upper Deck Sections
    "sec_301": { x: 300, y: 130, name: "Section 301 (Upper)", color: "#10b981" },
    "sec_304": { x: 200, y: 250, name: "Section 304 (Upper)", color: "#10b981" },
    // Mid Level Sections
    "sec_201": { x: 280, y: 150, name: "Section 201 (Mid)", color: "#10b981" },
    "sec_204": { x: 220, y: 230, name: "Section 204 (Mid)", color: "#10b981" },
    // Lower Level Sections
    "sec_101": { x: 280, y: 190, name: "Section 101 (Lower)", color: "#10b981" },
    "sec_104": { x: 220, y: 190, name: "Section 104 (Lower)", color: "#10b981" },
    
    // Concourse connector nodes
    "stairs_east": { x: 320, y: 140, name: "Stairs East", color: "#10b981", type: "STAIRS" },
    "stairs_west": { x: 180, y: 240, name: "Stairs West", color: "#10b981", type: "STAIRS" },
    "elevator_east": { x: 320, y: 240, name: "Elevator East", color: "#10b981", type: "ELEVATOR" },
    "elevator_west": { x: 180, y: 140, name: "Elevator West", color: "#10b981", type: "ELEVATOR" },
    "escalator_north": { x: 220, y: 110, name: "Escalator North", color: "#10b981", type: "ESCALATOR" },
    "walkway_concourse": { x: 250, y: 175, name: "Concourse Walkway", color: "#10b981" },
    
    // Core Gates
    "gate_a": { x: 370, y: 190, name: "Gate A (East)", color: "#10b981" },
    "gate_b": { x: 250, y: 80, name: "Gate B (North)", color: "#10b981" },
    "gate_c": { x: 130, y: 190, name: "Gate C (West)", color: "#10b981" },
    "gate_d": { x: 250, y: 300, name: "Gate D (South)", color: "#10b981" },
    
    // Transit Hubs
    "train_station": { x: 250, y: 350, name: "Train Station", color: "#6366f1" },
    "rideshare_hub": { x: 250, y: 30, name: "Rideshare Hub", color: "#6366f1" },
    "parking_lot_a": { x: 450, y: 190, name: "Parking A", color: "#6366f1" },
    "parking_lot_b": { x: 50, y: 190, name: "Parking B", color: "#6366f1" }
};

// Map Edges for drawing physical walkways
const GRAPH_EDGES = [
    { from: "sec_301", to: "stairs_east" },
    { from: "sec_301", to: "elevator_east" },
    { from: "sec_304", to: "stairs_west" },
    { from: "sec_304", to: "elevator_west" },
    { from: "sec_201", to: "stairs_east" },
    { from: "sec_201", to: "elevator_east" },
    { from: "sec_201", to: "escalator_north" },
    { from: "sec_204", to: "stairs_west" },
    { from: "sec_204", to: "elevator_west" },
    { from: "sec_204", to: "escalator_north" },
    { from: "sec_101", to: "gate_a" },
    { from: "sec_101", to: "gate_b" },
    { from: "sec_104", to: "gate_c" },
    { from: "sec_104", to: "gate_d" },
    { from: "stairs_east", to: "gate_a" },
    { from: "elevator_east", to: "gate_a" },
    { from: "stairs_west", to: "gate_c" },
    { from: "elevator_west", to: "gate_c" },
    { from: "escalator_north", to: "gate_b" },
    { from: "gate_a", to: "walkway_concourse" },
    { from: "gate_b", to: "walkway_concourse" },
    { from: "gate_c", to: "walkway_concourse" },
    { from: "gate_d", to: "walkway_concourse" },
    { from: "gate_a", to: "train_station" },
    { from: "gate_b", to: "rideshare_hub" },
    { from: "gate_a", to: "parking_lot_a" },
    { from: "gate_c", to: "parking_lot_b" },
    { from: "gate_d", to: "train_station" }
];

// App State
let appState = {
    sensorData: {
        "gate_a": "LOW",
        "gate_b": "LOW",
        "elevator_east": "true",
        "elevator_west": "true"
    },
    currentPath: [],
    networkOnline: true
};

// UI Components
const routeForm = document.getElementById("route-form");
const startNodeSelect = document.getElementById("start-node");
const destNodeSelect = document.getElementById("dest-node");
const wheelchairToggle = document.getElementById("wheelchair-toggle");
const queryInput = document.getElementById("query-input");
const charCounter = document.getElementById("char-count");
const searchBtn = document.getElementById("search-btn");
const searchSpinner = document.getElementById("search-spinner");
const resultsPanel = document.getElementById("results-panel");
const resultsEmpty = document.getElementById("results-empty-state");
const resultsContent = document.getElementById("results-content-panel");
const langSelect = document.getElementById("lang-select");

// Metric fields
const metricTime = document.getElementById("metric-time");
const metricDistance = document.getElementById("metric-distance");
const metricSource = document.getElementById("metric-source");
const fallbackBadge = document.getElementById("fallback-badge");
const genaiNarrativeText = document.getElementById("genai-narrative");
const routeStepsList = document.getElementById("route-steps");

// Map Container
const mapContainer = document.getElementById("stadium-map-svg-container");

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
    // Generate initial SVG layout
    renderStadiumMap();
    
    // Character limit counter for textarea
    queryInput.addEventListener("input", (e) => {
        const count = e.target.value.length;
        charCounter.textContent = `${count} / 250`;
        // WCAG color warning near limit
        if (count >= 230) {
            charCounter.style.color = "var(--color-red)";
        } else {
            charCounter.style.color = "var(--text-muted)";
        }
    });

    // Handle Form submission
    routeForm.addEventListener("submit", (e) => {
        e.preventDefault();
        triggerRouting();
    });

    // Monitor operational changes to auto-recompute active routes
    document.querySelectorAll(".sensor-select, .sensor-select-status").forEach(select => {
        select.addEventListener("change", (e) => {
            const node = e.target.getAttribute("data-node");
            const val = e.target.value;
            submitSensorUpdate(node, val);
        });
    });

    // Language switcher auto recalculation
    langSelect.addEventListener("change", () => {
        if (appState.currentPath.length > 0) {
            triggerRouting();
        }
    });

    // Periodic network connectivity simulator check
    window.addEventListener("online", updateNetworkStatus);
    window.addEventListener("offline", updateNetworkStatus);
});

function updateNetworkStatus() {
    const statusDot = document.querySelector("#network-status .status-dot");
    const statusLabel = document.querySelector("#network-status .status-label");
    
    if (navigator.onLine) {
        appState.networkOnline = true;
        statusDot.className = "status-dot online";
        statusLabel.textContent = "Stadium Wi-Fi (Connected)";
    } else {
        appState.networkOnline = false;
        statusDot.className = "status-dot offline";
        statusLabel.textContent = "Low Bandwidth (Offline Fallback)";
    }
}

/**
 * Sends real-time sensor overrides to the FastAPI backend.
 */
async function submitSensorUpdate(nodeId, value) {
    const payload = { node_id: nodeId };
    
    if (value === "true" || value === "false") {
        payload.elevator_operational = (value === "true");
        payload.crowd_density = "LOW"; // Keep low if operational
        appState.sensorData[nodeId] = value;
    } else {
        payload.crowd_density = value;
        appState.sensorData[nodeId] = value;
    }

    try {
        const response = await fetch("/api/sensor/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error("Sensor upload failed");
        
        showToast(`Sensor configured for ${NODE_COORDINATES[nodeId]?.name || nodeId}`);
        
        // Dynamic rerouting trigger if a path is actively displayed
        if (appState.currentPath.length > 0) {
            triggerRouting(true); // silent re-calculation
        } else {
            renderStadiumMap(); // just redraw node colors
        }
    } catch (err) {
        console.error(err);
        showToast("Error updating sensor feed.", true);
    }
}

/**
 * Triggers routing calculations by contacting the FastAPI Gateway.
 */
async function triggerRouting(isSilent = false) {
    if (!isSilent) {
        searchSpinner.classList.remove("hidden");
        searchBtn.disabled = true;
    }

    // Input sanitization guard
    const queryStr = queryInput.value.trim() || `Route to ${destNodeSelect.value}`;
    const requestData = {
        query: queryStr,
        language: langSelect.value,
        wheelchair_accessible: wheelchairToggle.checked,
        current_section: startNodeSelect.value,
        destination: destNodeSelect.value
    };

    try {
        const response = await fetch("/api/route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Server routing error");
        }

        const result = await response.json();
        
        if (result.route_found) {
            appState.currentPath = result.path_taken;
            renderRouteResults(result);
        } else {
            appState.currentPath = [];
            showRouteError(result.genai_narrative);
        }
    } catch (error) {
        console.error("Routing error:", error);
        // Offline / failure state degradation fallback
        appState.currentPath = [];
        showRouteError(error.message || "Network lost. Please verify connectivity or request stewards assistance.");
    } finally {
        if (!isSilent) {
            searchSpinner.classList.add("hidden");
            searchBtn.disabled = false;
        }
    }
}

/**
 * Displays route data in results card and updates the map overlay.
 */
function renderRouteResults(data) {
    resultsEmpty.classList.add("hidden");
    resultsContent.classList.remove("hidden");

    // Populate Metrics safely
    metricTime.textContent = `${data.total_time_minutes}m`;
    metricDistance.textContent = `${data.total_distance_meters}m`;
    metricSource.textContent = data.fallback_used ? "Offline" : "GenAI";

    // Set Fallback badge status
    if (data.is_cached) {
        fallbackBadge.textContent = "Cached Response";
        fallbackBadge.className = "badge active";
    } else if (data.fallback_used) {
        fallbackBadge.textContent = "Fallback Active";
        fallbackBadge.className = "badge warning";
    } else {
        fallbackBadge.textContent = "Live AI Stream";
        fallbackBadge.className = "badge active";
    }

    // XSS Mitigation: inject AI narrative text safely using textContent
    genaiNarrativeText.textContent = data.genai_narrative;

    // Compile step list timeline
    routeStepsList.innerHTML = "";
    data.steps.forEach(step => {
        const li = document.createElement("li");
        li.className = `timeline-step ${step.congested ? 'congested' : ''}`;
        
        const header = document.createElement("div");
        header.className = "step-header";
        header.innerHTML = `<span>Step ${step.step_number}</span><span>~${Math.ceil(step.estimated_seconds / 60)} min</span>`;
        
        const desc = document.createElement("div");
        desc.className = `step-desc ${step.congested ? 'congested-alert' : ''}`;
        desc.textContent = step.instruction; // Safe text insertion
        
        li.appendChild(header);
        li.appendChild(desc);
        routeStepsList.appendChild(li);
    });

    // Re-render map highlighting computed path
    renderStadiumMap(data.path_taken);
    
    // Smooth scroll down to result card for mobile accessibility
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showRouteError(errMsg) {
    resultsEmpty.classList.remove("hidden");
    resultsContent.classList.add("hidden");
    resultsEmpty.innerHTML = `<p style="color: var(--color-red); font-weight: 500;">⚠️ ${escapeHTML(errMsg)}</p>`;
    renderStadiumMap();
}

/**
 * Draws the SVG graphical view of MetLife Stadium dynamically.
 */
function renderStadiumMap(highlightedPath = []) {
    let svgHtml = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 380" class="map-svg" role="img" aria-label="Interactive Stadium Map">
            <rect width="100%" height="100%" class="map-bg" />
            <!-- MetLife Concourse Ring -->
            <ellipse cx="250" cy="190" rx="140" ry="110" class="map-concourse-ring" />
            <ellipse cx="250" cy="190" rx="140" ry="110" class="map-concourse-inner" />
            
            <!-- Edge connections (Background walkways) -->
            <g id="map-edges">
    `;

    // Draw all default background walkway connections
    GRAPH_EDGES.forEach(edge => {
        const fromNode = NODE_COORDINATES[edge.from];
        const toNode = NODE_COORDINATES[edge.to];
        if (fromNode && toNode) {
            svgHtml += `<line x1="${fromNode.x}" y1="${fromNode.y}" x2="${toNode.x}" y2="${toNode.y}" class="map-path-link" />`;
        }
    });

    svgHtml += `</g>`;

    // Draw active wayfinding highlight route line
    if (highlightedPath.length > 1) {
        svgHtml += `<g id="map-active-route">`;
        for (let i = 0; i < highlightedPath.length - 1; i++) {
            const current = NODE_COORDINATES[highlightedPath[i]];
            const next = NODE_COORDINATES[highlightedPath[i+1]];
            if (current && next) {
                svgHtml += `<line x1="${current.x}" y1="${current.y}" x2="${next.x}" y2="${next.y}" class="map-path-highlight" />`;
            }
        }
        svgHtml += `</g>`;
    }

    // Draw graph nodes (interactive circles)
    svgHtml += `<g id="map-nodes">`;
    Object.keys(NODE_COORDINATES).forEach(key => {
        const node = NODE_COORDINATES[key];
        let fill = "var(--color-green)";
        
        // Apply operational modifiers to colours
        if (appState.sensorData[key] === "MEDIUM") fill = "var(--color-orange)";
        if (appState.sensorData[key] === "HIGH") fill = "var(--color-red)";
        if (appState.sensorData[key] === "false") fill = "var(--color-broken)";
        if (key.includes("train") || key.includes("rideshare") || key.includes("parking")) {
            fill = "#6366f1"; // Accent transit blue
        }

        const isHighlighted = highlightedPath.includes(key);
        const radius = isHighlighted ? 9 : 6;
        const borderStroke = isHighlighted ? "#ffffff" : "rgba(255,255,255,0.4)";
        const strokeWidth = isHighlighted ? 2.5 : 1;

        svgHtml += `
            <g class="map-node-group">
                <circle cx="${node.x}" cy="${node.y}" r="${radius}" fill="${fill}" 
                        stroke="${borderStroke}" stroke-width="${strokeWidth}" class="map-node" data-key="${key}">
                    <title>${node.name} (${appState.sensorData[key] || 'Clear'})</title>
                </circle>
                <text x="${node.x}" y="${node.y - 10}" class="map-node-label">${escapeHTML(node.name.split(" ")[0])}</text>
            </g>
        `;
    });
    svgHtml += `</g></svg>`;

    mapContainer.innerHTML = svgHtml;

    // Attach click events on nodes to set start/destination selection automatically
    document.querySelectorAll(".map-node").forEach(circle => {
        circle.addEventListener("click", (e) => {
            const key = e.target.getAttribute("data-key");
            const node = NODE_COORDINATES[key];
            if (!node) return;

            // If it's a section, set start selection
            if (key.startsWith("sec_")) {
                startNodeSelect.value = key;
                showToast(`Start set to ${node.name}`);
            } else {
                // Otherwise set destination
                destNodeSelect.value = key;
                showToast(`Destination set to ${node.name}`);
            }
        });
    });
}

/**
 * Toast feedback popup for stadium operations updates.
 */
function showToast(message, isError = false) {
    const toast = document.getElementById("sensor-toast");
    toast.textContent = message;
    toast.style.color = isError ? "var(--color-red)" : "var(--color-green)";
    
    // Clear toast automatically
    setTimeout(() => {
        if (toast.textContent === message) {
            toast.textContent = "";
        }
    }, 3000);
}

// Basic HTML escaping helper for display safety
function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
