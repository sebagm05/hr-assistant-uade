import os
import sys
import json
from http.server import BaseHTTPRequestHandler

# Asegura que el modulo hermano knowledge_base sea importable en Vercel y en local
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from knowledge_base import retrieve


def process(body):
    """Recibe {query|jd|cv, k?, area?} y devuelve los documentos de referencia recuperados."""
    query = body.get("query", "")
    if not query:
        query = (body.get("jd", "") + " " + body.get("cv", "")).strip()
    if not query.strip():
        return 400, {"error": "Falta el texto de consulta (JD)."}
    k = int(body.get("k", 3))
    area = body.get("area")
    docs = retrieve(query, k=k, area=area)
    return 200, {"documentos": docs}


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            status, result = process(body)
            self.send_json(status, result)
        except Exception as e:
            self.send_json(500, {"error": str(e)})
