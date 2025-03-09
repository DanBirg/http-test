#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import socket

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        client_ip = self.client_address[0]
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        print(f"[{current_time}] Received request from {client_ip} - Path: {self.path}")
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        response_message = f"""
        <html>
        <head>
            <title>Simple HTTP Server</title>
        </head>
        <body>
            <h1>Hello from the Server!</h1>
            <p>Your IP: {client_ip}</p>
            <p>Requested path: {self.path}</p>
            <p>Server time: {current_time}</p>
            <p>Server hostname: {socket.gethostname()}</p>
        </body>
        </html>
        """
        
        self.wfile.write(response_message.encode('utf-8'))

def run_server(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Starting server on port {port}...")
    print(f"Server hostname: {socket.gethostname()}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()
        print("Server shutdown complete.")

if __name__ == "__main__":
    # Note: Running on port 80 typically requires root/administrator privileges
    run_server(80)
