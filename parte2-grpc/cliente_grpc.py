"""
Parte 2 - Cliente gRPC con comparativa vs REST
===============================================
Invoca los tres métodos del servicio Inventario y muestra:
  • Resultado de cada llamada remota
  • Tamaño serializado del mensaje Protobuf (bytes) vs JSON equivalente
  • Tiempo de respuesta de cada RPC

Requisitos:
  pip install grpcio grpcio-tools

Ejecutar (en esta carpeta, con el servidor ya iniciado):
  python cliente_grpc.py
"""

import json
import time
import grpc

import inventario_pb2
import inventario_pb2_grpc

HOST = "localhost"
PORT = 50051


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de comparación de tamaño de serialización
# ─────────────────────────────────────────────────────────────────────────────

def serializar_producto_json(producto: inventario_pb2.Producto) -> bytes:
    """Convierte un mensaje Producto a su equivalente JSON para comparar tamaño."""
    d = {
        "id":     producto.id,
        "nombre": producto.nombre,
        "precio": producto.precio,
        "stock":  producto.stock,
    }
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


def serializar_lista_json(lista: inventario_pb2.ListaProductos) -> bytes:
    """Convierte ListaProductos a JSON equivalente."""
    d = {
        "total": lista.total,
        "productos": [
            {"id": p.id, "nombre": p.nombre, "precio": p.precio, "stock": p.stock}
            for p in lista.productos
        ]
    }
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


def imprimir_comparativa(nombre_op: str, bytes_proto: int, bytes_json: int, tiempo_ms: float):
    reduccion = (1 - bytes_proto / bytes_json) * 100 if bytes_json > 0 else 0
    ancho = 52
    print(f"\n{'─' * ancho}")
    print(f"  SERIALIZACIÓN — {nombre_op}")
    print(f"{'─' * ancho}")
    print(f"  Protobuf (binario) : {bytes_proto:>6} bytes")
    print(f"  JSON (texto)       : {bytes_json:>6} bytes")
    print(f"  Reducción tamaño   : {reduccion:>5.1f} %")
    print(f"  Tiempo de RPC      : {tiempo_ms:>6.2f} ms")
    print(f"{'─' * ancho}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Cliente gRPC — Taller Sistemas Distribuidos")
    print("=" * 55)

    # Crear canal gRPC (HTTP/2 multiplexado, inseguro para el taller)
    canal = grpc.insecure_channel(f"{HOST}:{PORT}")
    stub  = inventario_pb2_grpc.InventarioStub(canal)

    # ── 1. ObtenerProducto ─────────────────────────────────
    print("\n[1] ObtenerProducto(id='p-001')...")
    try:
        solicitud = inventario_pb2.SolicitudProducto(id="p-001")
        t0 = time.perf_counter()
        producto = stub.ObtenerProducto(solicitud)
        t1 = time.perf_counter()
    except grpc.RpcError as e:
        print(f"  ERROR gRPC: {e.code()} — {e.details()}")
        print("  Asegúrate de iniciar primero: python servidor_grpc.py")
        canal.close()
        return

    tiempo_ms = (t1 - t0) * 1000
    print(f"  Producto recibido:")
    print(f"    ID     : {producto.id}")
    print(f"    Nombre : {producto.nombre}")
    print(f"    Precio : ${producto.precio:.2f}")
    print(f"    Stock  : {producto.stock} unidades")

    bytes_proto = len(producto.SerializeToString())
    bytes_json  = len(serializar_producto_json(producto))
    imprimir_comparativa("ObtenerProducto", bytes_proto, bytes_json, tiempo_ms)

    # ── 2. ObtenerProducto — ID inexistente ────────────────
    print("\n[2] ObtenerProducto(id='p-999')  →  esperando NOT_FOUND...")
    try:
        t0 = time.perf_counter()
        stub.ObtenerProducto(inventario_pb2.SolicitudProducto(id="p-999"))
        t1 = time.perf_counter()
    except grpc.RpcError as e:
        t1 = time.perf_counter()
        print(f"  Código de estado : {e.code()}")
        print(f"  Detalle          : {e.details()}")
        print(f"  Tiempo           : {(t1 - t0) * 1000:.2f} ms")

    # ── 3. ListarProductos ─────────────────────────────────
    print("\n[3] ListarProductos()...")
    solicitud_lista = inventario_pb2.SolicitudListar(pagina=0, por_pagina=0)
    t0 = time.perf_counter()
    lista = stub.ListarProductos(solicitud_lista)
    t1 = time.perf_counter()
    tiempo_ms = (t1 - t0) * 1000

    print(f"  Total productos: {lista.total}")
    for p in lista.productos:
        print(f"    • [{p.id}] {p.nombre:<22} ${p.precio:.2f}  (stock: {p.stock})")

    bytes_proto = len(lista.SerializeToString())
    bytes_json  = len(serializar_lista_json(lista))
    imprimir_comparativa("ListarProductos", bytes_proto, bytes_json, tiempo_ms)

    # ── 4. AgregarProducto ─────────────────────────────────
    print("\n[4] AgregarProducto(nombre='Monitor 4K UltraWide', precio=549.99, stock=8)...")
    solicitud_agregar = inventario_pb2.SolicitudAgregarProducto(
        nombre="Monitor 4K UltraWide",
        precio=549.99,
        stock=8,
    )
    t0 = time.perf_counter()
    respuesta = stub.AgregarProducto(solicitud_agregar)
    t1 = time.perf_counter()
    tiempo_ms = (t1 - t0) * 1000

    print(f"  Éxito   : {respuesta.exito}")
    print(f"  Mensaje : {respuesta.mensaje}")
    print(f"  ID asignado: {respuesta.producto.id}")
    bytes_proto = len(solicitud_agregar.SerializeToString())
    bytes_json  = len(json.dumps(
        {"nombre": "Monitor 4K UltraWide", "precio": 549.99, "stock": 8}
    ).encode("utf-8"))
    imprimir_comparativa("AgregarProducto (request)", bytes_proto, bytes_json, tiempo_ms)

    # ── 5. Verificar catálogo actualizado ──────────────────
    print("\n[5] ListarProductos() — verificando producto nuevo...")
    lista2 = stub.ListarProductos(inventario_pb2.SolicitudListar(pagina=0, por_pagina=0))
    print(f"  Total ahora: {lista2.total}")
    for p in lista2.productos:
        print(f"    • [{p.id}] {p.nombre:<22} ${p.precio:.2f}  (stock: {p.stock})")

    # ── 6. Resumen comparativo ─────────────────────────────
    print("\n" + "=" * 55)
    print("  RESUMEN: PROTOBUF vs JSON")
    print("=" * 55)
    print("""
  • Protobuf serializa los campos en binario compacto usando
    índices numéricos (field numbers) en lugar de nombres de
    cadena, eliminando la redundancia textual del JSON.

  • Para mensajes simples la reducción suele ser 30–60 %.
    A mayor complejidad y volumen, el ahorro escala.

  • Además, gRPC corre sobre HTTP/2:
      - Multiplexación: N solicitudes en una sola conexión TCP
      - Compresión de headers HPACK (sin repetir headers)
      - Streams bidireccionales (no disponible en REST/HTTP1.1)
  """)
    print("=" * 55)

    canal.close()


if __name__ == "__main__":
    main()
