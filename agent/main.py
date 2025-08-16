# agent/main.py
# The main application for the LISE Agent.

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import requests
import socket
import subprocess
import os
import threading
import time
import sys
import re
from typing import List

# --- Helper Function for PyInstaller ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Pydantic Models ---
class ConnectionRequest(BaseModel):
    display_name: str
    orchestrator_ip: str

class ScenarioStartRequest(BaseModel):
    compose_file_content: str
    vnc_port: int
    web_port: int

class ScenarioStopRequest(BaseModel):
    compose_file_path: str

# Create the FastAPI application instance
app = FastAPI(
    title="LISE Agent API",
    description="The agent application that runs on student machines to manage simulation containers.",
    version="2.0.0"
)

# --- Mount Static Files ---
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")

# --- AGENT STATE ---
state = {
    "is_connected": False,
    "orchestrator_ip": None,
    "display_name": None,
    "current_scenario_file": None,
    "current_scenario_name": None,
    "status_message": "Disconnected",
    "log_thread": None,
    "websockify_process": None
}

# --- Helper Functions ---
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def strip_ansi_codes(s):
    """Removes ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', s)

def stream_logs(compose_file_path, agent_name, orchestrator_ip):
    print("LOG: Initiating log stream thread.")
    log_url = f"http://{orchestrator_ip}:8080/api/log"
    time.sleep(3)
    command = ["docker-compose", "-f", compose_file_path, "logs", "-f", "--no-log-prefix"]
    print(f"LOG: Executing log command: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(f"LOG: Log stream subprocess started with PID: {process.pid}")
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            try:
                log_entry = {"agent_name": agent_name, "log_line": line.strip()}
                requests.post(log_url, json=log_entry, timeout=2)
            except requests.exceptions.RequestException:
                print(f"WARN: Could not send log line to orchestrator at {log_url}")
        process.stdout.close()
        process.wait()
        print(f"LOG: Log stream for {agent_name} ended. Process exited with code {process.returncode}.")
    except FileNotFoundError:
        print("ERROR: 'docker-compose' command not found. Please ensure Docker is installed and in your PATH.")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during log streaming: {e}")


def start_websockify(vnc_port):
    """Starts the websockify process to proxy VNC traffic."""
    print("LOG: Attempting to start websockify.")
    # This is the corrected path for the noVNC client.
    novnc_path = resource_path(os.path.join("static", "novnc"))
    command = ["websockify", "--web", novnc_path, "8081", f"localhost:{vnc_port}"]
    print(f"LOG: Websockify command: {' '.join(command)}")
    print(f"LOG: noVNC web directory: {novnc_path} ---")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        state["websockify_process"] = process
        print(f"LOG: Websockify process started successfully with PID: {process.pid}")
        # Add a delay to check for immediate errors.
        time.sleep(1)
        if process.poll() is not None:
             print(f"ERROR: Websockify process exited prematurely with code {process.returncode}")
        else:
            print("LOG: Websockify process is running.")

    except FileNotFoundError:
        print("ERROR: 'websockify' command not found. Please ensure it's installed and in your PATH.")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while starting websockify: {e}")

def stop_websockify():
    """Stops the websockify process if it's running."""
    if state.get("websockify_process") and state["websockify_process"].poll() is None:
        print("LOG: Stopping websockify process.")
        state["websockify_process"].terminate()
        state["websockify_process"].wait()
        state["websockify_process"] = None
        print("LOG: Websockify process stopped.")
    else:
        print("LOG: Websockify process was not running.")

# --- API ENDPOINTS ---

@app.get("/", response_class=FileResponse, tags=["UI"])
async def read_index():
    return resource_path("static/index.html")

@app.post("/api/connect", tags=["Connection Management"])
async def connect_to_orchestrator(conn_request: ConnectionRequest):
    print(f"LOG: Received connect request from UI. Display name: {conn_request.display_name}")
    state["display_name"] = conn_request.display_name
    state["orchestrator_ip"] = conn_request.orchestrator_ip
    orchestrator_url = f"http://{state['orchestrator_ip']}:8080/api/agents/register"
    agent_payload = {"display_name": state["display_name"], "ip_address": get_local_ip()}
    try:
        print(f"LOG: Sending registration to orchestrator at {orchestrator_url}")
        response = requests.post(orchestrator_url, json=agent_payload, timeout=5)
        response.raise_for_status()
        state["is_connected"] = True
        state["status_message"] = f"Connected to {state['orchestrator_ip']}"
        print(f"LOG: Successfully registered with orchestrator.")
        return {"status": "success", "message": state["status_message"]}
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to register with orchestrator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scenario/start", tags=["Simulation Control"])
async def start_scenario(request: ScenarioStartRequest, background_tasks: BackgroundTasks):
    print("LOG: Received scenario start request.")
    temp_compose_file = "temp-compose.yaml"
    with open(temp_compose_file, "w") as f:
        f.write(request.compose_file_content)
    print(f"LOG: Docker Compose file written to {temp_compose_file}")

    if state.get("current_scenario_file"):
        os.remove(temp_compose_file)
        print("ERROR: A scenario is already running.")
        raise HTTPException(status_code=400, detail="A scenario is already running.")

    command = ["docker-compose", "-f", temp_compose_file, "up", "-d"]
    try:
        print(f"LOG: Starting Docker Compose: {' '.join(command)}")
        # Adding a shell=True flag to make subprocess work correctly
        process_result = subprocess.run(command, check=True, capture_output=True, text=True, shell=True)
        print(f"LOG: Docker Compose started successfully. STDOUT: {process_result.stdout}, STDERR: {process_result.stderr}")
        
        state["current_scenario_file"] = temp_compose_file
        state["current_scenario_name"] = "vm-scenario"
        state["status_message"] = f"Running scenario: {state['current_scenario_name']}"

        start_websockify(request.vnc_port)

        log_thread = threading.Thread(
            target=stream_logs,
            args=(state["current_scenario_file"], state["display_name"], state["orchestrator_ip"]),
            daemon=True
        )
        state["log_thread"] = log_thread
        log_thread.start()

        print(f"LOG: Scenario '{state['current_scenario_name']}' started successfully.")
        return {"status": "success", "message": "Scenario started."}
    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_compose_file):
            os.remove(temp_compose_file)
        print(f"ERROR: Docker Compose failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Docker Compose failed: {e.stderr}")
    except FileNotFoundError:
        if os.path.exists(temp_compose_file):
            os.remove(temp_compose_file)
        print("ERROR: 'docker-compose' command not found.")
        raise HTTPException(status_code=500, detail="docker-compose or websockify command not found.")

@app.post("/api/scenario/stop", tags=["Simulation Control"])
async def stop_scenario():
    print("LOG: Received scenario stop request.")
    if not state.get("current_scenario_file"):
        print("ERROR: No scenario is currently running.")
        raise HTTPException(status_code=400, detail="No scenario is currently running.")

    compose_file = state["current_scenario_file"]
    command = ["docker-compose", "-f", compose_file, "down"]
    try:
        print(f"LOG: Stopping Docker Compose: {' '.join(command)}")
        subprocess.run(command, check=True, capture_output=True, text=True)

        stop_websockify()

        state["current_scenario_file"] = None
        state["current_scenario_name"] = None
        state["status_message"] = "Idle"
        if state.get("log_thread") and state["log_thread"].is_alive():
             state["log_thread"] = None

        os.remove(compose_file)
        print("LOG: Temporary Docker Compose file removed.")

        print("LOG: Scenario stopped successfully.")
        return {"status": "success", "message": "Scenario stopped."}
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Docker Compose 'down' failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Docker Compose 'down' failed: {e.stderr}")
    except FileNotFoundError:
        print("ERROR: 'docker-compose' command not found.")
        raise HTTPException(status_code=500, detail="docker-compose command not found.")

@app.get("/api/status", tags=["Status"])
def get_status():
    print("LOG: Received status request.")
    return {
        "status": state["status_message"],
        "is_connected": state["is_connected"],
        "display_name": state["display_name"],
        "orchestrator_ip": state["orchestrator_ip"],
        "current_scenario": state["current_scenario_name"]
    }

@app.websocket("/ws/log-stream")
async def websocket_endpoint(websocket: WebSocket):
    print("LOG: WebSocket connection request received.")
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("LOG: UI Client disconnected from logs.")

if __name__ == "__main__":
    print("--- Starting LISE Agent Server ---")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)