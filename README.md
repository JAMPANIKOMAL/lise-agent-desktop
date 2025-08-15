# LISE Agent (Desktop Application)

The LISE Agent is the student-facing component of the Local Incident Simulation Environment (LISE). It is a native desktop application that connects to a central LISE Orchestrator, receives simulation scenarios, and launches them locally on the student's machine.

This application uses a hybrid architecture: a Rust-based Tauri shell wraps a web-based user interface and manages a Python backend process.

---

## Technology Stack

- **Application Framework:** Tauri (v2)
- **Frontend:** HTML, Tailwind CSS, Vanilla JavaScript
- **Backend:** Python with FastAPI
- **Virtualization:** Docker
- **Desktop Installer:** MSI installer via Tauri

---

## Features

- Secure connection to LISE Orchestrator via WebSockets
- Real-time commands to start and stop simulations
- Executes scenarios packaged as Docker containers
- Displays virtual machine desktops using a web-based VNC client
- Real-time event log for status updates and debugging

---

## Setup and Development

Follow these steps to set up a local development environment.

### Prerequisites

- **Rust:** Install Rust
- **Node.js:** Install Node.js (LTS)
- **Python:** Install Python (3.8+)
- **Docker:** Install Docker Desktop

### 1. Clone the Repository

```sh
git clone <your-repository-url>
cd lise-agent-desktop
```

### 2. Install Frontend Dependencies

```sh
npm install
```

### 3. Set Up Python Environment

Create a virtual environment and install required Python packages.

```sh
cd agent
python -m venv venv
.\venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 4. Build the Python Backend Executable

Compile the Python backend into a standalone `.exe` file using PyInstaller.

```sh
cd ..
pyinstaller --noconsole --onefile agent/main.py
```

### 5. Position the Backend Executable

After building, copy `main.exe` from the `dist` folder and paste it into the `src-tauri` folder.

### 6. Run the Application

Start the application in development mode:

```sh
npm run tauri dev
```

---

## Building for Production

To create a shareable MSI installer:

```sh
npm run tauri build
```

The installer will be located in `src-tauri/target/release/bundle/msi/`.