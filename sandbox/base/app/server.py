import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def validate_configuration() -> None:
    database_host = os.getenv("DATABASE_HOST", "database")
    if database_host != "database":
        print(f"fatal: DATABASE_HOST={database_host!r} is not a valid demo host", flush=True)
        raise SystemExit(1)


def consume_demo_memory() -> list[bytearray]:
    memory_mb = int(os.getenv("MEMORY_LOAD_MB", "0"))
    allocations: list[bytearray] = []
    for allocated in range(memory_mb):
        allocations.append(bytearray(1024 * 1024))
        if allocated % 16 == 0:
            print(f"allocated {allocated + 1} MiB", flush=True)
    return allocations


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "payment-api"}).encode())
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"http: {format % args}", flush=True)


if __name__ == "__main__":
    validate_configuration()
    retained_memory = consume_demo_memory()
    port = int(os.getenv("PORT", "8080"))
    print(f"payment-api listening on :{port}; retained blocks={len(retained_memory)}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
