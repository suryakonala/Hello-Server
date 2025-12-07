from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import os

PORT = int(os.environ.get("PORT", 8000))

db = sqlite3.connect("data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    message TEXT
)
""")
db.commit()

class MyHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/save":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            name = data.get("name")
            email = data.get("email")
            message = data.get("message")

            cursor.execute(
                "INSERT INTO records (name, email, message) VALUES (?, ?, ?)",
                (name, email, message)
            )
            db.commit()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "Data saved"}).encode())

    def do_GET(self):
        if self.path == "/data":
            cursor.execute("SELECT * FROM records")
            rows = cursor.fetchall()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps(rows).encode())

server = HTTPServer(("", PORT), MyHandler)
print("Data Server Running...")
server.serve_forever()
