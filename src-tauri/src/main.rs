// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::process::Command; // Use Rust's standard library for commands

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      // Get the path to the sidecar executable
      let sidecar_path = app.path()
          .resource_dir()
          .expect("failed to get resource directory")
          .join("main.exe");

      // Launch the backend executable
      Command::new(sidecar_path)
          .spawn()
          .expect("Failed to spawn sidecar");

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}