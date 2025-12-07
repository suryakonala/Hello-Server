from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import os

PORT = int(os.environ.get("PORT", 8000))

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

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body)

        # ✅ REGISTER API
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

        # ✅ LOGIN API
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

        # ✅ SAVE MESSAGE API (OLD FEATURE)
        elif self.path == "/save":
            name = data.get("name")
            email = data.get("email")
            message = data.get("message")

            cursor.execute(
                "INSERT INTO records (name, email, message) VALUES (?, ?, ?)",
                (name, email, message)
            )
            db.commit()

            self.send_json({"status": "Data saved"})

    def do_GET(self):
        # ✅ VIEW ALL USERS
        if self.path == "/users":
            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()
            self.send_json(users)

        # ✅ VIEW ALL SAVED MESSAGES
        elif self.path == "/data":
            cursor.execute("SELECT * FROM records")
            rows = cursor.fetchall()
            self.send_json(rows)

server = HTTPServer(("", PORT), MyHandler)
print("Login + Data Server Running...")
server.serve_forever()
