import { invoke } from "@tauri-apps/api/core";
import RFB from './core/rfb.js';

// --- DOM Elements ---
const statusDisplay = document.getElementById('status-display');
const connectionFormContainer = document.getElementById('connection-form-container');
const connectionForm = document.getElementById('connection-form');
const displayNameInput = document.getElementById('display_name_input');
const orchestratorIpInput = document.getElementById('orchestrator_ip_input');
const logOutput = document.getElementById('log-output');
const simulationView = document.getElementById('simulation-view');
const vncScreen = document.getElementById('vnc-screen');

let rfb; // To hold the noVNC client instance

// --- Logging ---
function log(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const color = type === 'error' ? 'text-red-400' : 'text-gray-300';
    logOutput.innerHTML += `<span class="${color}">[${timestamp}] ${message}\n</span>`;
    logOutput.scrollTop = logOutput.scrollHeight; // Auto-scroll
}

// --- WebSocket Connection ---
let socket;

function connectWebSocket(name, ip) {
    socket = new WebSocket(`ws://${ip}:8000/ws/${name}`);

    socket.onopen = () => {
        log(`Connected to Orchestrator at ${ip} as ${name}.`);
        statusDisplay.textContent = 'Status: Connected';
        statusDisplay.className = 'text-right px-3 py-1 rounded-md bg-green-800 border border-green-500';
        connectionFormContainer.classList.add('hidden');
    };

    socket.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        log(`Received command: ${data.action}`);

        if (data.action === "start_simulation") {
            log(`Starting simulation: ${data.scenario_id}`);
            connectionFormContainer.classList.add("hidden");
            simulationView.classList.remove("hidden");
            
            // Start the Docker container and connect noVNC
            await startVmAndConnectVnc();
        }
    };

    socket.onclose = () => {
        log("Disconnected from Orchestrator.");
        statusDisplay.textContent = 'Status: Disconnected';
        statusDisplay.className = 'text-right px-3 py-1 rounded-md bg-red-800 border border-red-500';
        connectionFormContainer.classList.remove('hidden');
        simulationView.classList.add('hidden'); // Hide VM on disconnect
    };

    socket.onerror = (error) => {
        log(`WebSocket Error: ${error.message}`, 'error');
    };
}

// --- Simulation and VNC Logic ---
async function startVmAndConnectVnc() {
    const imageName = "ghcr.io/jampanikomal/lise-scenarios/poc-vm:1.0";
    const hostPort = 8080; // The port on the student's machine
    const containerPort = 5900; // The port inside the container

    try {
        log(`Pulling Docker image: ${imageName}...`);
        // Note: The shell scope must be configured in tauri.conf.json
        await invoke("plugin:shell|execute", {
            program: "docker",
            args: ["pull", imageName],
        });

        log("Starting Docker container...");
        await invoke("plugin:shell|execute", {
            program: "docker",
            args: ["run", "-d", "-p", `${hostPort}:${containerPort}`, imageName],
        });

        log("Container started. Connecting VNC client...");

        // Connect noVNC after a short delay to give the container time to start
        setTimeout(() => {
            const url = `ws://127.0.0.1:${hostPort}`;
            rfb = new RFB(vncScreen, url);
            log(`noVNC connected to ${url}`);
        }, 3000); // 3-second delay

    } catch (error) {
        log(`Failed to start simulation: ${error}`, 'error');
    }
}

// --- Event Listeners ---
connectionForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = displayNameInput.value;
    const ip = orchestratorIpInput.value;
    if (name && ip) {
        connectWebSocket(name, ip);
    }
});

// --- Initial Log ---
log("Agent UI Initialized. Ready to connect.");
