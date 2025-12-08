from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import os
import hashlib

PORT = int(os.environ.get("PORT", 8000))

# 🔐 YOUR ADMIN PASSWORD (CHANGE THIS!)
ADMIN_PASSWORD = "admin123"

# ===== Database =====
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

# ===== Session (admin login) =====
ADMIN_SESSION = False

class MyHandler(BaseHTTPRequestHandler):

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def serve_html(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        except:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Page not found")

    def do_GET(self):
        global ADMIN_SESSION

        if self.path == "/":
            self.serve_html("index.html")

        elif self.path == "/register":
            self.serve_html("register.html")

        elif self.path == "/login":
            self.serve_html("login.html")

        elif self.path == "/admin":
            self.serve_html("admin_login.html")

        elif self.path == "/admin-panel":
            if not ADMIN_SESSION:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden: Admin not logged in")
                return

            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()

            cursor.execute("SELECT * FROM records")
            records = cursor.fetchall()

            html = """
            <html>
            <head>
            <title>Admin Panel</title>
            <style>
                body{background:black;color:white;font-family:Arial;}
                h1,h2{color:#0ff}
                table{border-collapse:collapse;width:100%;margin-bottom:20px}
                th,td{border:1px solid #555;padding:8px}
            </style>
            </head>
            <body>
            <h1>Admin Panel</h1>
            <h2>Users</h2>
            <table><tr><th>ID</th><th>Username</th></tr>
            """

            for u in users:
                html += f"<tr><td>{u[0]}</td><td>{u[1]}</td></tr>"

            html += "</table><h2>Messages</h2><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th></tr>"

            for r in records:
                html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"

            html += "</table></body></html>"

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        global ADMIN_SESSION

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        data = json.loads(body)

        # ✅ ADMIN LOGIN
        if self.path == "/admin-login":
            if data.get("password") == ADMIN_PASSWORD:
                ADMIN_SESSION = True
                self.send_json({"status": "success"})
            else:
                self.send_json({"status": "failed"}, 401)

        # ✅ USER REGISTER
        elif self.path == "/register-api":
            username = data["username"]
            password = hashlib.sha256(data["password"].encode()).hexdigest()

            try:
                cursor.execute("INSERT INTO users (username,password) VALUES (?,?)", (username, password))
                db.commit()
                self.send_json({"status": "Registered"})
            except:
                self.send_json({"status": "User exists"}, 409)

        # ✅ USER LOGIN
        elif self.path == "/login-api":
            username = data["username"]
            password = hashlib.sha256(data["password"].encode()).hexdigest()

            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            if cursor.fetchone():
                self.send_json({"status": "Login success"})
            else:
                self.send_json({"status": "Invalid"}, 401)

        # ✅ SAVE MESSAGE
        elif self.path == "/save":
            cursor.execute(
                "INSERT INTO records (name,email,message) VALUES (?,?,?)",
                (data["name"], data["email"], data["message"])
            )
            db.commit()
            self.send_json({"status": "Saved"})

        else:
            self.send_json({"error": "Not found"}, 404)

# ===== Start Server =====
server = HTTPServer(("", PORT), MyHandler)
print("✅ Secure Server Running on port", PORT)
server.serve_forever()
