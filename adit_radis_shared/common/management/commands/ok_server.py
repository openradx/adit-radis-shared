from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from django.core.management.base import BaseCommand


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()


class Command(BaseCommand):
    help = "A simplistic HTTP server that just responds with 200 OK."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--host", type=str, default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8000)

    def handle(self, *args: Any, **options: Any):
        host = options["host"]
        port = options["port"]
        print(f"Serving OK server on {host}:{port}")
        server = HTTPServer((host, port), SimpleHTTPRequestHandler)
        server.serve_forever()
