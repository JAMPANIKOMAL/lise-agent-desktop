// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|_app| {
      // For now, don't start the agent automatically since it's already running
      println!("🚀 LISE Agent Desktop starting...");
      println!("� Expecting Python agent on http://localhost:8000");
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
