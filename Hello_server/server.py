from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

PORT = 8000

Handler = SimpleHTTPRequestHandler

with TCPServer(("", PORT), Handler) as server:
    print("Hello Server is running at http://localhost:8000")
    server.serve_forever()
