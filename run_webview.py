import base64
import socket
import threading
import time
from pathlib import Path

import webview

from app import app

HOST = "127.0.0.1"
PORT = 5000
TIMEOUT = 15


class AppApi:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def save_file(self, payload):
        if self.window is None:
            raise RuntimeError("Window is not ready")

        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")

        filename = payload.get("filename") or "download"
        data = payload.get("data")
        if not data:
            return {"status": "error", "message": "No data provided"}

        mime_type = payload.get("mime_type", "application/octet-stream")

        try:
            binary = base64.b64decode(data)
        except (base64.binascii.Error, TypeError) as exc:
            return {"status": "error", "message": f"Invalid file data: {exc}"}

        ext = Path(filename).suffix.lower()
        file_type_map = {
            ".xlsx": ("Excel Workbook (*.xlsx)",),
            ".docx": ("Word Document (*.docx)",),
            ".doc": ("Word Document (*.doc)",),
        }
        file_types = file_type_map.get(ext)

        # Prompt user for save location
        dialog_result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=filename,
            file_types=file_types,
        )

        if not dialog_result:
            return {"status": "cancelled"}

        target_path = Path(dialog_result if isinstance(dialog_result, str) else dialog_result[0])

        try:
            target_path.write_bytes(binary)
        except OSError as exc:
            return {"status": "error", "message": f"Failed to save file: {exc}"}

        return {
            "status": "success",
            "path": str(target_path),
            "mime_type": mime_type,
        }


def start_flask():
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def wait_for_server():
    start = time.time()
    while time.time() - start < TIMEOUT:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Flask server did not start in time")


if __name__ == "__main__":
    api = AppApi()
    thread = threading.Thread(target=start_flask, daemon=True)
    thread.start()
    wait_for_server()
    window = webview.create_window(
        "Faculty Allotment",
        f"http://{HOST}:{PORT}/",
        width=1200,
        height=800,
        js_api=api,
    )
    api.set_window(window)
    webview.start()
