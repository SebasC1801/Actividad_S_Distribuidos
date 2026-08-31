"""
generar_proto.py
================
Script auxiliar que compila inventario.proto y genera:
  - inventario_pb2.py        (clases de mensajes Protobuf)
  - inventario_pb2_grpc.py   (stubs y servicer gRPC)

Uso:
  python generar_proto.py

Requiere tener instalado:  pip install grpcio-tools
"""

import subprocess
import sys
import os

def main():
    carpeta = os.path.dirname(os.path.abspath(__file__))
    proto   = os.path.join(carpeta, "inventario.proto")

    print("[*] Compilando inventario.proto ...")
    resultado = subprocess.run(
        [
            sys.executable, "-m", "grpc_tools.protoc",
            f"-I{carpeta}",
            f"--python_out={carpeta}",
            f"--grpc_python_out={carpeta}",
            proto,
        ],
        capture_output=True,
        text=True,
    )

    if resultado.returncode == 0:
        print("[✓] Compilación exitosa.")
        print(f"    → {os.path.join(carpeta, 'inventario_pb2.py')}")
        print(f"    → {os.path.join(carpeta, 'inventario_pb2_grpc.py')}")
    else:
        print("[✗] Error al compilar:")
        print(resultado.stderr)
        print("\nAsegúrate de tener instalado:  pip install grpcio-tools")
        sys.exit(1)


if __name__ == "__main__":
    main()
