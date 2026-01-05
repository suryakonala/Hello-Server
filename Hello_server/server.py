from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import hashlib
from pymongo import MongoClient

# ================= CONFIG =================
PORT = int(os.environ.get("PORT", 8000))

# Admin password (use ENV in Render, fallback for local)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Surya@135")

# MongoDB connection (comes from Render ENV)
MONGO_URL = os.environ.get("MONGO_URL")

# ================= MONGODB =================
client = MongoClient(MONGO_URL)
mongo_db = client["helloserver"]

users_col = mongo_db["users"]
records_col = mongo_db["records"]

print("✅ MongoDB Connected")

# ================= ADMIN SESSION =================
ADMIN_SESSION = False


class MyHandler(BaseHTTPRequestHandler):

    # ---------- helpers ----------
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
        except Exception:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Page not found")

    # ---------- GET ----------
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

            users = users_col.find({}, {"password": 0})
            records = records_col.find({})

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
            <table>
            <tr><th>ID</th><th>Username</th></tr>
            """

            for u in users:
                html += f"<tr><td>{u['_id']}</td><td>{u['username']}</td></tr>"

            html += """
            </table>

            <h2>Messages</h2>
            <table>
            <tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th></tr>
            """

            for r in records:
                html += f"<tr><td>{r['_id']}</td><td>{r.get('name','')}</td><td>{r.get('email','')}</td><td>{r.get('message','')}</td></tr>"

            html += "</table></body></html>"

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    # ---------- POST ----------
    def do_POST(self):
        global ADMIN_SESSION

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        data = json.loads(body or b"{}")

        # ✅ ADMIN LOGIN
        if self.path == "/admin-login":
            if data.get("password") == ADMIN_PASSWORD:
                ADMIN_SESSION = True
                self.send_json({"status": "success"})
            else:
                self.send_json({"status": "failed"}, 401)

        # ✅ USER REGISTER
        elif self.path == "/register-api":
            username = data.get("username", "").strip()
            password = data.get("password", "")

            if not username or not password:
                self.send_json({"status": "Missing fields"}, 400)
                return

            hashed = hashlib.sha256(password.encode()).hexdigest()

            if users_col.find_one({"username": username}):
                self.send_json({"status": "User exists"}, 409)
                return

            users_col.insert_one({
                "username": username,
                "password": hashed
            })

            self.send_json({"status": "Registered"})

        # ✅ USER LOGIN
        elif self.path == "/login-api":
            username = data.get("username", "").strip()
            password = data.get("password", "")

            hashed = hashlib.sha256(password.encode()).hexdigest()

            user = users_col.find_one({
                "username": username,
                "password": hashed
            })

            if user:
                self.send_json({"status": "Login success"})
            else:
                self.send_json({"status": "Invalid"}, 401)

        # ✅ SAVE MESSAGE
        elif self.path == "/save":
            records_col.insert_one({
                "name": data.get("name"),
                "email": data.get("email"),
                "message": data.get("message")
            })
            self.send_json({"status": "Saved"})

        else:
            self.send_json({"error": "Not found"}, 404)


# ================= START SERVER =================
server = HTTPServer(("", PORT), MyHandler)
print("🚀 Secure Server Running on port", PORT)
server.serve_forever()
