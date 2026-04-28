"""
Локальный HTTP-сервер для calculator.html.
- Раздаёт страницу по /
- Проксирует курсы валют (обход CORS и надёжный запрос с ПК)
Слушает 0.0.0.0 — можно открыть с другого устройства в LAN (http://<IP>:порт/).
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://api.exchangerate-api.com/v4/latest/RUB"
PORT = int(os.environ.get("CALC_PORT", "8080"))


def local_ipv4() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


class CalcHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_calculator()
            return
        if path == "/calculator.html":
            self._serve_calculator()
            return
        if path == "/api/currency":
            self._proxy_currency()
            return
        self.send_error(404, "Not found")

    def _serve_calculator(self) -> None:
        fp = os.path.join(ROOT, "calculator.html")
        if not os.path.isfile(fp):
            self.send_error(404, "calculator.html not found")
            return
        with open(fp, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _proxy_currency(self) -> None:
        try:
            req = urllib.request.Request(
                API_URL,
                headers={"User-Agent": "CalculatorLocalServer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            body = json.dumps({"error": f"HTTP {e.code}: {e.reason}"}).encode("utf-8")
            self._send_json_error(502, body)
        except urllib.error.URLError as e:
            body = json.dumps({"error": str(e.reason or e)}).encode("utf-8")
            self._send_json_error(502, body)
        except Exception as e:
            body = json.dumps({"error": str(e)}).encode("utf-8")
            self._send_json_error(502, body)

    def _send_json_error(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print("[%s] %s" % (self.address_string(), fmt % args))


def main() -> None:
    host = "0.0.0.0"
    httpd = HTTPServer((host, PORT), CalcHandler)
    lan = local_ipv4()
    print("Калькулятор: http://127.0.0.1:%d/" % PORT)
    if lan:
        print("С другого устройства (та же сеть Wi-Fi/LAN): http://%s:%d/" % (lan, PORT))
    print("Порт можно задать: set CALC_PORT=8080 && python server.py")
    print("Остановка: Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")


if __name__ == "__main__":
    main()
