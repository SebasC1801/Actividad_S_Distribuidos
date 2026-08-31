"""
Parte 1 - Servidor REST (HTTP/1.1)
===================================
Expone dos endpoints sobre el catálogo de productos:
  GET  /productos        -> devuelve la lista completa en JSON
  POST /productos        -> registra un nuevo producto (JSON en el body)

Usa únicamente la librería estándar de Python (http.server + json).
No requiere instalar ningún paquete externo.
"""

import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ---------------------------------------------------------------------------
# Base de datos en memoria (lista de diccionarios)
# ---------------------------------------------------------------------------
PRODUCTOS = [
    {"id": "p-001", "nombre": "Laptop Pro 15",   "precio": 1250.00, "stock": 10},
    {"id": "p-002", "nombre": "Mouse Inalámbrico","precio":   25.99, "stock": 50},
    {"id": "p-003", "nombre": "Teclado Mecánico", "precio":   89.99, "stock": 30},
]

HOST = "localhost"
PORT = 8080


# ---------------------------------------------------------------------------
# Handler HTTP
# ---------------------------------------------------------------------------
class ProductosHandler(BaseHTTPRequestHandler):

    # Silencia el log de acceso por defecto para que la salida sea más limpia;
    # podemos activarlo cambiando el flag LOG_REQUESTS.
    LOG_REQUESTS = True

    def log_message(self, format, *args):
        if self.LOG_REQUESTS:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {self.address_string()} - {format % args}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _enviar_json(self, codigo: int, datos: dict | list):
        """Serializa `datos` a JSON y lo envía con los headers correctos."""
        cuerpo = json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        # Header de fecha/hora del servidor (ilustra overhead de headers HTTP)
        self.send_header("Date", self.date_time_string())
        self.send_header("Server", "TallerREST/1.0 Python/http.server")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _leer_body_json(self):
        """Lee el body de la petición y lo parsea como JSON."""
        longitud = int(self.headers.get("Content-Length", 0))
        if longitud == 0:
            return None
        raw = self.rfile.read(longitud)
        return json.loads(raw.decode("utf-8"))

    # ------------------------------------------------------------------
    # GET /productos
    # ------------------------------------------------------------------
    def do_GET(self):
        if self.path == "/productos":
            respuesta = {
                "total": len(PRODUCTOS),
                "productos": PRODUCTOS,
            }
            self._enviar_json(200, respuesta)
        else:
            self._enviar_json(404, {"error": f"Ruta '{self.path}' no encontrada"})

    # ------------------------------------------------------------------
    # POST /productos
    # ------------------------------------------------------------------
    def do_POST(self):
        if self.path == "/productos":
            try:
                datos = self._leer_body_json()
                if datos is None:
                    self._enviar_json(400, {"error": "Body vacío o Content-Length ausente"})
                    return

                # Validación mínima de campos obligatorios
                campos_requeridos = {"nombre", "precio", "stock"}
                faltantes = campos_requeridos - datos.keys()
                if faltantes:
                    self._enviar_json(400, {
                        "error": f"Campos obligatorios faltantes: {sorted(faltantes)}"
                    })
                    return

                # Crear producto con ID autogenerado
                nuevo = {
                    "id":     f"p-{uuid.uuid4().hex[:6]}",
                    "nombre": str(datos["nombre"]),
                    "precio": float(datos["precio"]),
                    "stock":  int(datos["stock"]),
                }
                PRODUCTOS.append(nuevo)
                print(f"  [+] Producto registrado: {nuevo}")
                self._enviar_json(201, {"mensaje": "Producto creado", "producto": nuevo})

            except (json.JSONDecodeError, ValueError) as e:
                self._enviar_json(400, {"error": f"JSON inválido: {e}"})
        else:
            self._enviar_json(404, {"error": f"Ruta '{self.path}' no encontrada"})


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main():
    servidor = HTTPServer((HOST, PORT), ProductosHandler)
    print("=" * 55)
    print("  Servidor REST - Taller Sistemas Distribuidos")
    print("=" * 55)
    print(f"  Escuchando en  http://{HOST}:{PORT}")
    print(f"  Endpoints disponibles:")
    print(f"    GET  http://{HOST}:{PORT}/productos")
    print(f"    POST http://{HOST}:{PORT}/productos")
    print("  Presiona Ctrl+C para detener.")
    print("=" * 55)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido.")
        servidor.server_close()


if __name__ == "__main__":
    main()
