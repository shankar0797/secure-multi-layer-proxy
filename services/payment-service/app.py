from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/payments":
            response = {
                "service": "payment-service",
                "status": "success",
                "message": "Payment service is working"
            }
            self.send_response(200)
        elif self.path == "/health":
            response = {"service": "payment-service", "status": "healthy"}
            self.send_response(200)
        else:
            response = {"error": "Not Found"}
            self.send_response(404)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

HTTPServer(("0.0.0.0", 8003), Handler).serve_forever()
