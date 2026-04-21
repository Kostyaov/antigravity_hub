import os
import json
import importlib.util
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Initialize Root App (Hot-Reload Triggered - EXCEPTION LOGGING)
app = FastAPI(title="Antigravity Hub Orchestrator")

# Ensure root directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount global static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates engine
templates = Jinja2Templates(directory="templates")

# Connections Manager for WebSockets (e.g. yt-dlp-front)
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
app.state.ws_manager = manager

class PluginManager:
    def __init__(self, app: FastAPI):
        self.app = app
        self.plugins = []
        self.scan_apps()

    def scan_apps(self):
        apps_dir = "apps"
        if not os.path.exists(apps_dir):
            os.makedirs(apps_dir)
            return

        for folder in os.listdir(apps_dir):
            folder_path = os.path.join(apps_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            
            manifest_path = os.path.join(folder_path, "manifest.json")
            if not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                
                # Check for backend
                if manifest.get("has_backend", False):
                    router_path = os.path.join(folder_path, manifest.get("backend_entry", "router.py"))
                    if os.path.exists(router_path):
                        spec = importlib.util.spec_from_file_location(f"{manifest['id']}_router", router_path)
                        plugin_module = importlib.util.module_from_spec(spec)
                        sys_module_name = f"apps.{folder}"
                        import sys
                        sys.modules[sys_module_name] = plugin_module
                        spec.loader.exec_module(plugin_module)
                        if hasattr(plugin_module, "router"):
                            app.include_router(plugin_module.router)
                            with open("plugin_loader.log", "a") as logf:
                                logf.write(f"[SUCCESS] Loaded backend for {manifest['name']} from {router_path}\n")
                        else:
                            with open("plugin_loader.log", "a") as logf:
                                logf.write(f"[ERROR] No 'router' object in {router_path}\n")
                    else:
                        with open("plugin_loader.log", "a") as logf:
                            logf.write(f"[ERROR] Router file not found: {router_path}\n")

                # Only add to list if we reached this point without error
                manifest["folder"] = folder_path
                manifest["folder_name"] = folder
                self.plugins.append(manifest)

            except Exception as e:
                with open("plugin_loader.log", "a") as logf:
                    logf.write(f"[CRITICAL ERROR] Failed to load {folder}: {str(e)}\n")
                    import traceback
                    logf.write(traceback.format_exc() + "\n")

        # Sort plugins by order if defined, else by name
        self.plugins.sort(key=lambda x: x.get("order", 99))
        print(f"Total plugins loaded: len({self.plugins})")

# Load Plugins
plugin_manager = PluginManager(app)
app.state.plugins = plugin_manager.plugins

# Since ui.html needs to be rendered natively inside the jinja template or requested
# We need an endpoint to fetch the dynamic HTML to inject if we do it via frontend, OR we pass raw content directly to Jinja2

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serves the main Antigravity Hub SPA with dynamically loaded tabs.
    """
    # Read the HTML content for each plugin so Jinja can inject it safely
    plugins_data = []
    for p in app.state.plugins:
        ui_path = os.path.join(p["folder"], p.get("html_entry", "ui.html"))
        ui_content = f"<div style='color:red;'>UI file {p.get('html_entry')} not found</div>"
        if os.path.exists(ui_path):
            with open(ui_path, "r", encoding="utf-8") as f:
                ui_content = f.read()
                
        # Optional: load custom JS entry
        js_content = ""
        js_entry = p.get("js_entry")
        if js_entry:
            js_path = os.path.join(p["folder"], js_entry)
            if os.path.exists(js_path):
                with open(js_path, "r", encoding="utf-8") as f:
                    js_content = f.read()

        plugins_data.append({
            **p,
            "html": ui_content,
            "js_script": js_content
        })

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "plugins": plugins_data
    })

@app.get("/debug/routes")
async def list_routes():
    """Returns all registered application routes."""
    url_list = [{"path": route.path, "name": route.name} for route in app.routes]
    return {
        "total_plugins_loaded": len(app.state.plugins),
        "plugins": [p["name"] for p in app.state.plugins],
        "routes": url_list
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
