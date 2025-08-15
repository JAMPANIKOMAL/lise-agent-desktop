// RFB is the noVNC core library
import RFB from './core/rfb.js';

// --- DOM ELEMENTS ---
const statusDisplay = document.getElementById('status-display');
const connectionFormContainer = document.getElementById('connection-form-container');
const connectionForm = document.getElementById('connection-form');
const displayNameInput = document.getElementById('display_name_input');
const orchestratorIpInput = document.getElementById('orchestrator_ip_input');
const logOutput = document.getElementById('log-output');
const simulationView = document.getElementById('simulation-view');
const vncScreen = document.getElementById('vnc-screen');

// Check if all required DOM elements exist
const requiredElements = {
    statusDisplay,
    connectionFormContainer, 
    connectionForm,
    displayNameInput,
    orchestratorIpInput,
    logOutput,
    simulationView,
    vncScreen
};

for (const [name, element] of Object.entries(requiredElements)) {
    if (!element) {
        console.error(`Required DOM element not found: ${name}`);
    }
}

let rfb; // To hold the noVNC client instance

// --- Logging ---
function addLog(message, type = 'info') {
    if (!logOutput) {
        console.warn('logOutput element not found, logging to console:', message);
        return;
    }
    const timestamp = new Date().toLocaleTimeString();
    const color = type === 'error' ? 'text-red-400' : 'text-gray-300';
    logOutput.innerHTML += `<span class="${color}">[${timestamp}] ${message}\n</span>`;
    logOutput.scrollTop = logOutput.scrollHeight; // Auto-scroll
}

// --- WebSocket Connection ---
let socket;

function connectWebSocket(name, ip) {
    // Connect to the Orchestrator's WebSocket
    socket = new WebSocket(`ws://${ip}:8000/ws/${name}`);

    socket.onopen = () => {
        addLog(`Connected to Orchestrator at ${ip} as ${name}.`);
        if (statusDisplay) {
            statusDisplay.textContent = 'Status: Connected';
            statusDisplay.className = 'text-right px-3 py-1 rounded-md bg-green-800 border border-green-500';
        }
        if (connectionFormContainer) {
            connectionFormContainer.classList.add('hidden');
        }
    };

    socket.onmessage = async (event) => {
        try {
            const data = JSON.parse(event.data);
            addLog(`Received command: ${data.action || 'unknown'}`);

            if (data.action === "start_simulation") {
                addLog(`Starting simulation: ${data.scenario_id || 'unknown scenario'}`);
                if (simulationView) {
                    simulationView.classList.remove("hidden");
                }
                await startVmAndConnectVnc();
            }
        } catch (error) {
            const errorMessage = error?.message || error?.toString() || 'Unknown parsing error';
            addLog(`Error parsing WebSocket message: ${errorMessage}`, 'error');
        }
    };

    socket.onclose = () => {
        addLog("Disconnected from Orchestrator.");
        if (statusDisplay) {
            statusDisplay.textContent = 'Status: Disconnected';
            statusDisplay.className = 'text-right px-3 py-1 rounded-md bg-red-800 border border-red-500';
        }
        if (connectionFormContainer) {
            connectionFormContainer.classList.remove('hidden');
        }
        if (simulationView) {
            simulationView.classList.add('hidden');
        }
    };

    socket.onerror = (error) => {
        const errorMessage = error?.message || error?.type || 'Unknown WebSocket error';
        addLog(`WebSocket Error: ${errorMessage}`, 'error');
    };
}

// --- Simulation and VNC Logic ---
async function startVmAndConnectVnc() {
    const imageName = "ghcr.io/jampanikomal/lise-scenarios/poc-vm:1.0";
    const hostPort = 8080;
    const containerPort = 5900;

    try {
        addLog(`Pulling Docker image: ${imageName}...`);
        // Ask our own backend to run the command
        const pullRes = await fetch('http://127.0.0.1:8001/api/docker/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ imageName })
        });
        if (!pullRes.ok) throw new Error(await pullRes.text());
        addLog("Image pulled successfully.");

        addLog("Starting Docker container...");
        // Ask our own backend to run the command
        const runRes = await fetch('http://127.0.0.1:8001/api/docker/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ imageName, hostPort, containerPort })
        });
        if (!runRes.ok) throw new Error(await runRes.text());
        addLog("Container started. Connecting VNC client...");

        // Connect noVNC after a short delay
        setTimeout(() => {
            try {
                if (!vncScreen) {
                    addLog("VNC screen element not found", 'error');
                    return;
                }
                const url = `ws://127.0.0.1:${hostPort}`;
                rfb = new RFB(vncScreen, url);
                addLog(`noVNC connected to ${url}`);
                
                // Add RFB event listeners for better error handling
                rfb.addEventListener("connect", () => {
                    addLog("RFB connection established");
                });
                
                rfb.addEventListener("disconnect", (e) => {
                    addLog(`RFB disconnected: ${e.detail.clean ? 'Clean' : 'Unclean'} disconnect`, 
                           e.detail.clean ? 'info' : 'error');
                });
                
            } catch (error) {
                const errorMessage = error?.message || error?.toString() || 'Unknown RFB error';
                addLog(`Failed to create RFB connection: ${errorMessage}`, 'error');
            }
        }, 3000);

    } catch (error) {
        const errorMessage = error?.message || error?.toString() || 'Unknown error occurred';
        addLog(`Failed to start simulation: ${errorMessage}`, 'error');
    }
}

// --- Event Listeners ---
if (connectionForm && displayNameInput && orchestratorIpInput) {
    connectionForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const name = displayNameInput.value;
        const ip = orchestratorIpInput.value;
        if (name && ip) {
            connectWebSocket(name, ip);
        }
    });
} else {
    addLog("Connection form elements not found", 'error');
}

// --- Initial Log ---
addLog("Agent UI Initialized. Ready to connect.");
