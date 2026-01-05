from http.server import BaseHTTPRequestHandler, HTTPServer
import json, os, hashlib
from urllib.parse import urlparse
from pymongo import MongoClient

PORT = int(os.environ.get("PORT", 8000))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Surya123")
MONGO_URL = os.environ.get("MONGO_URL")

client = MongoClient(MONGO_URL)
db = client["helloserver"]
users = db["users"]
records = db["records"]

ADMIN_SESSION = False


class MyHandler(BaseHTTPRequestHandler):

    def send_html(self, file):
        try:
            with open(file, encoding="utf-8") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        except:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Page not found")

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        global ADMIN_SESSION
        path = urlparse(self.path).path

        if path == "/":
            self.send_html("index.html")

        elif path == "/register":
            self.send_html("register.html")

        elif path == "/login":
            self.send_html("login.html")

        elif path == "/admin":
            self.send_html("admin_login.html")

        elif path == "/admin-panel":
            if not ADMIN_SESSION:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return

            html = "<h1 style='color:cyan'>Admin Panel</h1><body style='background:black;color:white'>"
            html += "<h2>Users</h2><ul>"
            for u in users.find({}, {"password": 0}):
                html += f"<li>{u['username']}</li>"
            html += "</ul></body>"

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        global ADMIN_SESSION
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))

        if self.path == "/register-api":
            password = hashlib.sha256(data["password"].encode()).hexdigest()
            if users.find_one({"username": data["username"]}):
                self.send_json({"error": "User exists"}, 409)
            else:
                users.insert_one({
                    "username": data["username"],
                    "password": password
                })
                self.send_json({"status": "Registered"})

        elif self.path == "/login-api":
            password = hashlib.sha256(data["password"].encode()).hexdigest()
            user = users.find_one({
                "username": data["username"],
                "password": password
            })
            self.send_json({"status": "success"} if user else {"error": "Invalid"}, 401)

        elif self.path == "/admin-login":
            if data["password"] == ADMIN_PASSWORD:
                ADMIN_SESSION = True
                self.send_json({"status": "success"})
            else:
                self.send_json({"error": "Wrong password"}, 401)

        else:
            self.send_json({"error": "Not found"}, 404)


server = HTTPServer(("", PORT), MyHandler)
print("🚀 Hello Server running on port", PORT)
server.serve_forever()
