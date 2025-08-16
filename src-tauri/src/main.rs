// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

fn start_python_agent() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 Starting Python agent...");
    
    // Get the current executable directory
    let mut agent_path = std::env::current_exe()?;
    agent_path.pop(); // Remove the executable name
    
    // In development mode, the agent is in the agent/dist directory relative to project root
    // In production, it should be bundled with the app
    if cfg!(debug_assertions) {
        // Development mode: go up to project root, then to agent/dist
        agent_path.pop(); // Remove target
        agent_path.pop(); // Remove debug
        agent_path.pop(); // Remove target
        agent_path.push("agent");
        agent_path.push("dist");
        agent_path.push("lise-agent.exe");
    } else {
        // Production mode: agent should be in the same directory or resources
        agent_path.push("lise-agent.exe");
    }
    
    println!("Looking for agent at: {:?}", agent_path);
    
    if !agent_path.exists() {
        return Err(format!("Python agent not found at: {:?}", agent_path).into());
    }
    
    // Start the Python agent as a background process
    let mut child = Command::new(&agent_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    
    println!("✓ Python agent started with PID: {}", child.id());
    
    // Wait a moment for the agent to start
    thread::sleep(Duration::from_secs(2));
    
    // Check if the process is still running
    match child.try_wait() {
        Ok(Some(status)) => {
            return Err(format!("Python agent exited early with status: {}", status).into());
        }
        Ok(None) => {
            println!("✓ Python agent is running");
        }
        Err(e) => {
            return Err(format!("Failed to check agent status: {}", e).into());
        }
    }
    
    Ok(())
}

fn main() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|_app| {
      println!("🚀 LISE Agent Desktop starting...");
      
      // Start the Python agent
      match start_python_agent() {
          Ok(()) => {
              println!("✓ Python agent started successfully");
              println!("🌐 Agent available at http://localhost:8000");
          }
          Err(e) => {
              eprintln!("❌ Failed to start Python agent: {}", e);
              eprintln!("Please ensure the Python agent is built and available.");
          }
      }
      
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
