# LISE Agent (Desktop Application)

The LISE Agent is the student-facing component of the Local Incident Simulation Environment (LISE). It is a native desktop application that connects to a central LISE Orchestrator, receives simulation scenarios, and launches them locally on the student's machine.

This application uses a hybrid architecture: a Rust-based Tauri shell wraps a web-based user interface and manages a Python backend process.

---

## Project Structure

```
lise-agent-desktop/
├── agent/                      # Python backend
│   ├── main.py                # FastAPI server (rebuilt from LISE 1.0)
│   ├── requirements.txt       # Python dependencies
│   ├── static/               # Web UI assets
│   │   └── index.html        # Agent web interface
│   └── dist/                 # PyInstaller output
│       └── lise-agent.exe    # Standalone executable
├── src/                      # Tauri frontend
│   ├── index.html           # Desktop wrapper interface
│   ├── main.js              # Frontend logic
│   └── styles.css           # Styling
├── src-tauri/               # Tauri configuration
│   ├── main.rs              # Rust application entry
│   ├── tauri.conf.json      # Tauri settings
│   └── Cargo.toml           # Rust dependencies
├── others/                  # Backup of previous broken version
└── build/                   # Build artifacts
```

## Technology Stack

- **Application Framework:** Tauri (v2)
- **Frontend:** HTML, Tailwind CSS, Vanilla JavaScript
- **Backend:** Python 3.13.6 with FastAPI
- **Build Tools:** PyInstaller 6.15.0, Rust/Cargo 1.89.0
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

## Development Environment Setup

This project was completely rebuilt from a working LISE 1.0 foundation. Follow these exact steps for setup:

### Prerequisites

- **Rust:** Install Rust (1.89.0+)
- **Node.js:** Install Node.js with npm (11.4.2+)
- **Python:** Install Python (3.13.6+)
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

Configure Python environment and install dependencies:

```sh
cd agent
python -m venv venv
.\venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 4. Test Python Backend

Verify the backend works correctly:

```sh
# Test directly with Python
python main.py

# In another terminal, test the endpoint
Invoke-WebRequest -Uri "http://localhost:8000" -Method GET
```

### 5. Build Python Executable

Create standalone executable using PyInstaller:

```sh
cd ..  # Back to project root
pyinstaller --noconsole --onefile agent/main.py --distpath agent/dist --name lise-agent
```

### 6. Development Mode

Run the desktop application in development mode:

```sh
# Terminal 1: Start Python agent
cd agent/dist
./lise-agent.exe

# Terminal 2: Start Tauri development server
cd ../..  # Back to project root
npm run tauri dev
```

### 7. Production Build

Build the complete desktop application:

```sh
npm run tauri build
```

---

## Complete Rebuild Process

This section documents the complete rebuild process used to restore this project from a broken state using a working LISE 1.0 reference. **Use this process for lise-orchestrator-desktop**.

### Step 1: Backup and Cleanup

```sh
# Create backup of broken version
mkdir others
mv build others/backup-broken-version
mv main.spec others/
# Remove other broken artifacts as needed
```

### Step 2: Rebuild Python Backend

1. **Copy working code from LISE 1.0 reference**:
   - Copy `main.py` from working lise-project
   - Copy `static/index.html` from working lise-project
   - Copy `requirements.txt` or recreate with working dependencies

2. **Install dependencies**:
   ```sh
   cd agent
   pip install fastapi uvicorn pydantic requests
   pip freeze > requirements.txt
   ```

3. **Test backend**:
   ```sh
   python main.py
   # Verify http://localhost:8000 responds
   ```

### Step 3: Create PyInstaller Executable

```sh
cd ..  # Project root
pyinstaller --noconsole --onefile agent/main.py --distpath agent/dist --name lise-agent
```

### Step 4: Configure Tauri

1. **Update `src-tauri/tauri.conf.json`**:
   - Set proper application name and identifier
   - Configure window dimensions (800x600 minimum)
   - Add lise-agent.exe to bundle resources

2. **Update `src/index.html`**:
   - Implement connection retry logic (120 attempts over 60 seconds)
   - Add iframe for localhost:8000
   - Include error handling and manual fallback

3. **Simplify `src-tauri/main.rs`**:
   - Remove automatic agent launching to avoid threading issues
   - Keep basic Tauri setup only

### Step 5: Integration Testing

```sh
# Terminal 1: Start agent
cd agent/dist
./lise-agent.exe

# Terminal 2: Test Tauri
cd ../..
npm run tauri dev
```

### Step 6: Verification

```sh
# Check agent is running
netstat -an | Select-String "8000"

# Test HTTP response
Invoke-WebRequest -Uri "http://localhost:8000" -Method GET
```

---

## Important Notes

- **others/ folder**: Contains backup of the previous broken version for reference
- **Separate terminals**: Always run Python agent and Tauri in separate terminal sessions
- **PyInstaller compatibility**: The `resource_path()` function in main.py handles both development and compiled executable paths
- **Connection retry**: Frontend includes robust retry logic to handle agent startup timing
- **Thread safety**: Rust code avoids Send trait violations by not passing app parameters to background threads

---

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