"""
Parte 1 - Cliente REST (HTTP/1.1) con análisis de overhead
===========================================================
Realiza peticiones GET y POST al servidor REST y mide:
  - Tamaño de los headers HTTP enviados y recibidos
  - Tamaño del payload (body) JSON
  - Overhead relativo = headers / (headers + body) * 100

Usa únicamente la librería estándar de Python (urllib + http.client).
No requiere instalar ningún paquete externo.

Cómo usar:
  1. Inicia primero el servidor:  python servidor_rest.py
  2. Luego ejecuta este cliente:  python cliente_rest.py
"""

import json
import time
import http.client
from typing import Any


HOST = "localhost"
PORT = 8080

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de medición
# ─────────────────────────────────────────────────────────────────────────────

def calcular_overhead(headers_enviados: str, headers_recibidos: str, body: bytes) -> dict:
    """
    Devuelve un desglose del tamaño (bytes) de cada componente de la petición/respuesta.

    overhead_rel = bytes_de_headers / bytes_totales * 100
    """
    bytes_req_headers  = len(headers_enviados.encode("utf-8"))
    bytes_resp_headers = len(headers_recibidos.encode("utf-8"))
    bytes_body         = len(body)
    bytes_totales      = bytes_req_headers + bytes_resp_headers + bytes_body

    return {
        "headers_peticion_bytes":  bytes_req_headers,
        "headers_respuesta_bytes": bytes_resp_headers,
        "body_bytes":              bytes_body,
        "total_bytes":             bytes_totales,
        "overhead_relativo_%":    round(
            (bytes_req_headers + bytes_resp_headers) / bytes_totales * 100, 2
        ) if bytes_totales > 0 else 0,
    }


def formatear_headers_enviados(metodo: str, path: str, extra: dict | None = None) -> str:
    """Reconstruye la línea de petición + headers como texto para medir su tamaño."""
    lineas = [f"{metodo} {path} HTTP/1.1", f"Host: {HOST}:{PORT}", "Accept: application/json"]
    if extra:
        for k, v in extra.items():
            lineas.append(f"{k}: {v}")
    return "\r\n".join(lineas) + "\r\n\r\n"


def formatear_headers_respuesta(response: http.client.HTTPResponse) -> str:
    """Convierte los headers de la respuesta a texto para medir su tamaño."""
    lineas = [f"HTTP/1.1 {response.status} {response.reason}"]
    for nombre, valor in response.getheaders():
        lineas.append(f"{nombre}: {valor}")
    return "\r\n".join(lineas) + "\r\n\r\n"


def imprimir_analisis(titulo: str, overhead: dict, tiempo_ms: float):
    ancho = 52
    print(f"\n{'─' * ancho}")
    print(f"  ANÁLISIS DE OVERHEAD — {titulo}")
    print(f"{'─' * ancho}")
    print(f"  Headers de petición  : {overhead['headers_peticion_bytes']:>6} bytes")
    print(f"  Headers de respuesta : {overhead['headers_respuesta_bytes']:>6} bytes")
    print(f"  Body (payload JSON)  : {overhead['body_bytes']:>6} bytes")
    print(f"  Total transferido    : {overhead['total_bytes']:>6} bytes")
    print(f"  Overhead de headers  : {overhead['overhead_relativo_%']:>5.1f} %")
    print(f"  Tiempo de respuesta  : {tiempo_ms:>6.2f} ms")
    print(f"{'─' * ancho}")


# ─────────────────────────────────────────────────────────────────────────────
# Operaciones REST
# ─────────────────────────────────────────────────────────────────────────────

def get_productos() -> dict[str, Any]:
    """GET /productos — consulta el catálogo completo."""
    conn = http.client.HTTPConnection(HOST, PORT, timeout=5)

    headers_extra = None  # GET no tiene body extra
    headers_req_str = formatear_headers_enviados("GET", "/productos")

    t0 = time.perf_counter()
    conn.request("GET", "/productos", headers={"Accept": "application/json"})
    response = conn.getresponse()
    t1 = time.perf_counter()

    body_raw = response.read()
    tiempo_ms = (t1 - t0) * 1000

    headers_resp_str = formatear_headers_respuesta(response)
    conn.close()

    datos = json.loads(body_raw.decode("utf-8"))
    overhead = calcular_overhead(headers_req_str, headers_resp_str, body_raw)

    return {"datos": datos, "overhead": overhead, "tiempo_ms": tiempo_ms,
            "status": response.status}


def post_producto(nombre: str, precio: float, stock: int) -> dict[str, Any]:
    """POST /productos — registra un producto nuevo."""
    conn = http.client.HTTPConnection(HOST, PORT, timeout=5)

    payload = json.dumps(
        {"nombre": nombre, "precio": precio, "stock": stock},
        ensure_ascii=False
    ).encode("utf-8")

    headers_extra = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(payload)),
    }
    headers_req_str = formatear_headers_enviados("POST", "/productos", headers_extra)

    t0 = time.perf_counter()
    conn.request(
        "POST", "/productos",
        body=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(payload)),
        }
    )
    response = conn.getresponse()
    t1 = time.perf_counter()

    body_raw = response.read()
    tiempo_ms = (t1 - t0) * 1000

    headers_resp_str = formatear_headers_respuesta(response)
    conn.close()

    datos = json.loads(body_raw.decode("utf-8"))
    overhead = calcular_overhead(headers_req_str, headers_resp_str, body_raw)

    return {"datos": datos, "overhead": overhead, "tiempo_ms": tiempo_ms,
            "status": response.status}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Cliente REST — Taller Sistemas Distribuidos")
    print("=" * 55)

    # ── 1. GET /productos ──────────────────────────────────
    print("\n[1] Consultando catálogo de productos (GET /productos)...")
    try:
        resultado = get_productos()
    except ConnectionRefusedError:
        print("\n  ERROR: No se pudo conectar al servidor.")
        print("  Asegúrate de iniciar primero: python servidor_rest.py")
        return

    print(f"  Estado HTTP : {resultado['status']}")
    print(f"  Total items : {resultado['datos']['total']}")
    print("\n  Productos recibidos:")
    for p in resultado["datos"]["productos"]:
        print(f"    • [{p['id']}] {p['nombre']:<22} ${p['precio']:.2f}  (stock: {p['stock']})")

    imprimir_analisis("GET /productos", resultado["overhead"], resultado["tiempo_ms"])

    # ── 2. POST /productos ─────────────────────────────────
    print("\n[2] Registrando nuevo producto (POST /productos)...")
    resultado_post = post_producto(
        nombre="Monitor 4K UltraWide",
        precio=549.99,
        stock=8,
    )
    print(f"  Estado HTTP : {resultado_post['status']}")
    print(f"  Respuesta   : {json.dumps(resultado_post['datos'], ensure_ascii=False, indent=4)}")
    imprimir_analisis("POST /productos", resultado_post["overhead"], resultado_post["tiempo_ms"])

    # ── 3. GET para verificar que el nuevo producto quedó ──
    print("\n[3] Verificando catálogo actualizado (GET /productos)...")
    resultado2 = get_productos()
    print(f"  Total items ahora: {resultado2['datos']['total']}")
    for p in resultado2["datos"]["productos"]:
        print(f"    • [{p['id']}] {p['nombre']:<22} ${p['precio']:.2f}  (stock: {p['stock']})")
    imprimir_analisis("GET /productos (2ª llamada)", resultado2["overhead"], resultado2["tiempo_ms"])

    # ── 4. Comparativa de overhead ─────────────────────────
    print("\n" + "=" * 55)
    print("  COMPARATIVA DE OVERHEAD HTTP")
    print("=" * 55)
    filas = [
        ("GET  /productos (vacío)",  resultado["overhead"]),
        ("POST /productos (payload)", resultado_post["overhead"]),
        ("GET  /productos (lleno)",  resultado2["overhead"]),
    ]
    print(f"  {'Operación':<30} {'Headers':>8} {'Body':>8} {'Overhead':>9}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*9}")
    for nombre_op, ov in filas:
        total_headers = ov["headers_peticion_bytes"] + ov["headers_respuesta_bytes"]
        print(f"  {nombre_op:<30} {total_headers:>7}B {ov['body_bytes']:>7}B {ov['overhead_relativo_%']:>8.1f}%")

    print("\n  CONCLUSIÓN:")
    print("  En HTTP/1.1 los headers se envían como texto plano en CADA")
    print("  petición, sin compresión ni reutilización. Para payloads")
    print("  pequeños el overhead puede superar el 50 %, lo que impacta")
    print("  directamente en la latencia y el ancho de banda consumido.")
    print("=" * 55)


if __name__ == "__main__":
    main()
