use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tauri::RunEvent;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

#[tauri::command]
fn backend_url() -> &'static str {
    "http://127.0.0.1:18765"
}

fn wait_for_backend(address: &str, timeout: Duration) -> std::io::Result<()> {
    let deadline = Instant::now() + timeout;

    loop {
        if TcpStream::connect(address).is_ok() {
            return Ok(());
        }

        if Instant::now() >= deadline {
            return Err(std::io::Error::new(
                std::io::ErrorKind::TimedOut,
                format!("backend did not start on {address}"),
            ));
        }

        thread::sleep(Duration::from_millis(500));
    }
}

fn backend_is_running(address: &str) -> bool {
    TcpStream::connect(address).is_ok()
}

pub fn run() {
    let backend_child: Arc<Mutex<Option<CommandChild>>> = Arc::new(Mutex::new(None));
    let setup_child = Arc::clone(&backend_child);

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![backend_url])
        .setup(move |app| {
            if backend_is_running("127.0.0.1:18765") {
                return Ok(());
            }

            let sidecar = app
                .shell()
                .sidecar("supplierintel-backend")?
                .env("SUPPLIERINTEL_DESKTOP", "1")
                .env("SUPPLIERINTEL_DESKTOP_HOST", "127.0.0.1")
                .env("SUPPLIERINTEL_DESKTOP_PORT", "18765");

            let (mut rx, child) = sidecar.spawn()?;
            *setup_child.lock().expect("backend child mutex poisoned") = Some(child);

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[supplierintel-backend] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[supplierintel-backend] {}", String::from_utf8_lossy(&line));
                        }
                        _ => {}
                    }
                }
            });

            wait_for_backend("127.0.0.1:18765", Duration::from_secs(60))?;

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build SupplierIntel desktop app");

    app.run(move |_app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            if let Some(child) = backend_child
                .lock()
                .expect("backend child mutex poisoned")
                .take()
            {
                let _ = child.kill();
            }
        }
    });
}
