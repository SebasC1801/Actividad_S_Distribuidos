"""
Parte 2 - Servidor gRPC (HTTP/2 + Protocol Buffers)
====================================================
Implementa el servicio Inventario definido en inventario.proto.
Métodos disponibles:
  • ObtenerProducto  — busca un producto por ID
  • ListarProductos  — devuelve el catálogo completo
  • AgregarProducto  — registra un nuevo producto

Requisitos (instalar una sola vez):
  pip install grpcio grpcio-tools

Generar código desde el .proto (ejecutar en esta carpeta):
  python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. inventario.proto

Esto produce:
  inventario_pb2.py       — clases de mensajes (Protocol Buffers)
  inventario_pb2_grpc.py  — clases de servicio/stub gRPC
"""

import uuid
import time
import grpc
import concurrent.futures

import inventario_pb2
import inventario_pb2_grpc

HOST = "localhost"
PORT = 50051

# ─────────────────────────────────────────────────────────────────────────────
# Base de datos en memoria
# ─────────────────────────────────────────────────────────────────────────────
PRODUCTOS = [
    inventario_pb2.Producto(id="p-001", nombre="Laptop Pro 15",    precio=1250.00, stock=10),
    inventario_pb2.Producto(id="p-002", nombre="Mouse Inalámbrico", precio=25.99,  stock=50),
    inventario_pb2.Producto(id="p-003", nombre="Teclado Mecánico",  precio=89.99,  stock=30),
]


# ─────────────────────────────────────────────────────────────────────────────
# Implementación del servicio
# ─────────────────────────────────────────────────────────────────────────────
class InventarioServicio(inventario_pb2_grpc.InventarioServicer):

    def ObtenerProducto(self, request, context):
        """
        RPC unario: recibe SolicitudProducto, devuelve Producto.
        Si no existe, cancela con código NOT_FOUND.
        """
        print(f"  [gRPC] ObtenerProducto(id='{request.id}')")
        for producto in PRODUCTOS:
            if producto.id == request.id:
                return producto
        # Producto no encontrado → error estándar de gRPC
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Producto con id '{request.id}' no encontrado.")
        return inventario_pb2.Producto()

    def ListarProductos(self, request, context):
        """
        RPC unario: devuelve ListaProductos.
        Acepta paginación simple (pagina / por_pagina).
        """
        print(f"  [gRPC] ListarProductos(pagina={request.pagina}, "
              f"por_pagina={request.por_pagina})")

        todos = list(PRODUCTOS)

        # Paginación opcional
        if request.por_pagina > 0:
            inicio = request.pagina * request.por_pagina
            todos = todos[inicio: inicio + request.por_pagina]

        return inventario_pb2.ListaProductos(
            total=len(PRODUCTOS),
            productos=todos,
        )

    def AgregarProducto(self, request, context):
        """
        RPC unario: recibe SolicitudAgregarProducto, devuelve RespuestaAgregar.
        """
        print(f"  [gRPC] AgregarProducto(nombre='{request.nombre}', "
              f"precio={request.precio}, stock={request.stock})")

        if not request.nombre:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("El campo 'nombre' es obligatorio.")
            return inventario_pb2.RespuestaAgregar(exito=False,
                                                   mensaje="Nombre vacío.")

        nuevo = inventario_pb2.Producto(
            id=f"p-{uuid.uuid4().hex[:6]}",
            nombre=request.nombre,
            precio=request.precio,
            stock=request.stock,
        )
        PRODUCTOS.append(nuevo)
        print(f"  [+] Producto agregado: {nuevo.id} - {nuevo.nombre}")

        return inventario_pb2.RespuestaAgregar(
            exito=True,
            mensaje=f"Producto '{nuevo.nombre}' creado con ID {nuevo.id}.",
            producto=nuevo,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────
def main():
    servidor = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    inventario_pb2_grpc.add_InventarioServicer_to_server(InventarioServicio(), servidor)

    direccion = f"{HOST}:{PORT}"
    servidor.add_insecure_port(direccion)
    servidor.start()

    print("=" * 55)
    print("  Servidor gRPC — Taller Sistemas Distribuidos")
    print("=" * 55)
    print(f"  Escuchando en  {direccion}  (HTTP/2 sin TLS)")
    print(f"  Métodos expuestos:")
    print(f"    • Inventario.ObtenerProducto")
    print(f"    • Inventario.ListarProductos")
    print(f"    • Inventario.AgregarProducto")
    print("  Presiona Ctrl+C para detener.")
    print("=" * 55)

    try:
        while True:
            time.sleep(86400)          # duerme 1 día; el servidor corre en threads
    except KeyboardInterrupt:
        print("\n[!] Deteniendo servidor gRPC...")
        servidor.stop(grace=2)         # 2 s de gracia para RPC en curso
        print("[!] Servidor detenido.")


if __name__ == "__main__":
    main()
