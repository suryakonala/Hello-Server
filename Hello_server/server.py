from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import os
import hashlib
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 8000))
# 🔑 Secret API key – change this if you want
SECRET_KEY = os.environ.get("API_KEY", "mysecret123")

# ===== Database Setup (SQLite for now) =====
db = sqlite3.connect("data.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

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

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        # CORS preflight support (for JS frontends)
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-KEY")
        self.end_headers()

    def require_api_key(self):
        key = self.headers.get("X-API-KEY", "")
        if key != SECRET_KEY:
            self.send_json({"error": "Forbidden: invalid API key"}, status=403)
            return False
        return True

    # ===== GET Requests =====
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ROOT → serve index.html
        if path == "/":
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    html = f.read()

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"index.html error: {str(e)}".encode())

        # 🔐 Admin panel (HTML) – /admin?key=SECRET
        elif path == "/admin":
            key_param = query.get("key", [""])[0]
            if key_param != SECRET_KEY:
                self.send_response(403)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Forbidden: invalid admin key")
                return

            # fetch users and records
            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()
            cursor.execute("SELECT id, name, email, message FROM records")
            records = cursor.fetchall()

            html_parts = [
                "<!DOCTYPE html><html><head><title>Admin Panel</title>",
                "<style>body{background:black;color:white;font-family:Arial;}",
                "table{border-collapse:collapse;width:100%;margin-bottom:20px;}",
                "th,td{border:1px solid #666;padding:8px;text-align:left;}",
                "h1,h2{color:#0ff;}</style></head><body>",
                "<h1>Hello Server – Admin Panel</h1>",
                "<h2>Users</h2><table><tr><th>ID</th><th>Username</th></tr>"
            ]
            for uid, uname in users:
                html_parts.append(f"<tr><td>{uid}</td><td>{uname}</td></tr>")
            html_parts.append("</table><h2>Messages</h2>")
            html_parts.append("<table><tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th></tr>")
            for rid, name, email, message in records:
                # basic HTML escaping
                name = (name or "").replace("<", "&lt;").replace(">", "&gt;")
                email = (email or "").replace("<", "&lt;").replace(">", "&gt;")
                message = (message or "").replace("<", "&lt;").replace(">", "&gt;")
                html_parts.append(
                    f"<tr><td>{rid}</td><td>{name}</td><td>{email}</td><td>{message}</td></tr>"
                )
            html_parts.append("</table></body></html>")
            html = "".join(html_parts)

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        # View all users (JSON, protected)
        elif path == "/users":
            if not self.require_api_key():
                return
            cursor.execute("SELECT id, username FROM users")
            rows = cursor.fetchall()
            self.send_json(rows)

        # View all saved messages (JSON, protected)
        elif path == "/data":
            if not self.require_api_key():
                return
            cursor.execute("SELECT * FROM records")
            rows = cursor.fetchall()
            self.send_json(rows)

        else:
            self.send_json({"error": "Not found"}, status=404)

    # ===== POST Requests =====
    def do_POST(self):
        # All POST APIs require API key
        if not self.require_api_key():
            return

        content_length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(content_length or 0)
        try:
            data = json.loads(body or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, status=400)
            return

        # 🔹 Register user
        if self.path == "/register":
            username = data.get("username", "").strip()
            password = data.get("password", "")

            if not username or not password:
                self.send_json({"error": "username and password required"}, status=400)
                return

            hashed = hashlib.sha256(password.encode()).hexdigest()

            try:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hashed)
                )
                db.commit()
                self.send_json({"status": "User registered"})
            except sqlite3.IntegrityError:
                self.send_json({"status": "Username already exists"}, status=409)

        # 🔹 Login user
        elif self.path == "/login":
            username = data.get("username", "").strip()
            password = data.get("password", "")

            hashed = hashlib.sha256(password.encode()).hexdigest()

            cursor.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, hashed)
            )
            user = cursor.fetchone()

            if user:
                self.send_json({"status": "Login successful"})
            else:
                self.send_json({"status": "Invalid username or password"}, status=401)

        # 🔹 Save message
        elif self.path == "/save":
            name = data.get("name", "")
            email = data.get("email", "")
            message = data.get("message", "")

            cursor.execute(
                "INSERT INTO records (name, email, message) VALUES (?, ?, ?)",
                (name, email, message)
            )
            db.commit()
            self.send_json({"status": "Data saved"})

        else:
            self.send_json({"error": "Not found"}, status=404)

# ===== Start Server =====
server = HTTPServer(("", PORT), MyHandler)
print(f"Login + Data API Server Running on port {PORT} ...")
server.serve_forever()
