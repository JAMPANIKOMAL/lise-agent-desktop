import asyncio
import websockets
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess

# --- FastAPI Setup ---
app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- WebSocket Endpoint for Orchestrator ---
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    print(f"Agent {client_id} connected to its own backend.")
    try:
        while True:
            # This is just to keep the connection alive for orchestrator messages
            # In a real app, you'd handle messages from the orchestrator here
            message = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {message}", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Agent {client_id} disconnected.")

# --- Models for API Requests ---
class DockerPullRequest(BaseModel):
    imageName: str

class DockerRunRequest(BaseModel):
    imageName: str
    hostPort: int
    containerPort: int

# --- API Endpoints for Docker Commands ---
@app.post("/api/docker/pull")
async def pull_docker_image(request: DockerPullRequest):
    try:
        print(f"Pulling image: {request.imageName}")
        subprocess.run(["docker", "pull", request.imageName], check=True, capture_output=True, text=True)
        return {"status": "success", "message": f"Image {request.imageName} pulled successfully."}
    except subprocess.CalledProcessError as e:
        print(f"Error pulling image: {e.stderr}")
        return {"status": "error", "message": e.stderr}

@app.post("/api/docker/run")
async def run_docker_container(request: DockerRunRequest):
    try:
        print(f"Running image: {request.imageName} on port {request.hostPort}")
        port_mapping = f"{request.hostPort}:{request.containerPort}"
        subprocess.run(
            ["docker", "run", "-d", "-p", port_mapping, request.imageName],
            check=True, capture_output=True, text=True
        )
        return {"status": "success", "message": "Container started successfully."}
    except subprocess.CalledProcessError as e:
        print(f"Error running container: {e.stderr}")
        return {"status": "error", "message": e.stderr}


# --- Serve Static Files (The Frontend) ---
import os
# --- Serve Static Files (The Frontend) ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    # Use port 8001 for the agent to avoid conflicts with the orchestrator
    uvicorn.run(app, host="0.0.0.0", port=8001, log_config=None)
