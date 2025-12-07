from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import os

PORT = int(os.environ.get("PORT", 8000))

# ===== Database Setup =====
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

# ====== Server Handler ======
class MyHandler(BaseHTTPRequestHandler):

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    # ===== GET Requests =====
    def do_GET(self):

        # ROOT → serve index.html
        if self.path == "/":
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

        # View all users
        elif self.path == "/users":
            cursor.execute("SELECT id, username FROM users")
            rows = cursor.fetchall()
            self.send_json(rows)

        # View all saved messages
        elif self.path == "/data":
            cursor.execute("SELECT * FROM records")
            rows = cursor.fetchall()
            self.send_json(rows)

    # ===== POST Requests =====
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body)

        # Register user
        if self.path == "/register":
            username = data.get("username")
            password = data.get("password")

            try:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password)
                )
                db.commit()
                self.send_json({"status": "User registered"})
            except:
                self.send_json({"status": "Username already exists"})

        # Login user
        elif self.path == "/login":
            username = data.get("username")
            password = data.get("password")

            cursor.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, password)
            )
            user = cursor.fetchone()

            if user:
                self.send_json({"status": "Login successful"})
            else:
                self.send_json({"status": "Invalid username or password"})

        # Save message
        elif self.path == "/save":
            cursor.execute(
                "INSERT INTO records (name, email, message) VALUES (?, ?, ?)",
                (data["name"], data["email"], data["message"])
            )
            db.commit()
            self.send_json({"status": "Data saved"})

# ===== Start Server =====
server = HTTPServer(("", PORT), MyHandler)
print("Login + Data API Server Running...")
server.serve_forever()
