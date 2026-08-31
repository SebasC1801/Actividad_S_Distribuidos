# Taller — Protocolos de Comunicación Distribuida

**Asignatura:** Sistemas Distribuidos  
**Implementación:** Python 3 (librería estándar + grpcio)

---

## Estructura del proyecto

```
taller-protocolos/
├── parte1-rest/
│   ├── servidor_rest.py    ← Servidor HTTP/1.1 (GET y POST /productos)
│   └── cliente_rest.py     ← Cliente con análisis de overhead de headers
└── parte2-grpc/
    ├── inventario.proto    ← Definición del servicio (Protocol Buffers v3)
    ├── generar_proto.py    ← Script para compilar el .proto
    ├── servidor_grpc.py    ← Servidor gRPC (HTTP/2)
    └── cliente_grpc.py     ← Cliente gRPC con comparativa Protobuf vs JSON
```

---

## Parte 1 — REST (HTTP/1.1)

### Cómo ejecutar

```bash
# Terminal 1 — iniciar servidor
cd parte1-rest
python servidor_rest.py

# Terminal 2 — ejecutar cliente
cd parte1-rest
python cliente_rest.py
```

No se requieren dependencias externas; ambos scripts usan la librería estándar de Python (`http.server`, `http.client`, `json`).

### Endpoints

| Método | Ruta         | Descripción                              |
|--------|--------------|------------------------------------------|
| GET    | `/productos` | Devuelve el catálogo completo en JSON    |
| POST   | `/productos` | Registra un nuevo producto (JSON en body)|

**Body del POST (ejemplo):**
```json
{
  "nombre": "Monitor 4K UltraWide",
  "precio": 549.99,
  "stock": 8
}
```

### Overhead de headers HTTP/1.1

En HTTP/1.1 los headers se transmiten como texto plano en cada petición, sin compresión ni reutilización entre conexiones.

```
──────────────────────────────────────────────────────
  ANÁLISIS DE OVERHEAD — GET /productos
──────────────────────────────────────────────────────
  Headers de petición  :    ~120 bytes
  Headers de respuesta :    ~210 bytes
  Body (payload JSON)  :    ~250 bytes
  Total transferido    :    ~580 bytes
  Overhead de headers  :   ~56.9 %
──────────────────────────────────────────────────────
```

> Los valores exactos varían según el tamaño del catálogo. El cliente muestra los números reales en tiempo de ejecución.

| Situación | Impacto |
|-----------|---------|
| Payload pequeño (un ID, un flag) | Headers > Body |
| Alta frecuencia de peticiones (polling) | Cada petición repite headers idénticos |
| Redes con bajo ancho de banda | El overhead acumulado consume más canal que los datos útiles |
| Microservicios internos | El parsing de texto suma latencia |

#### Causas del overhead

1. Headers en texto plano sin comprimir.
2. Sin mecanismo para omitir headers que no cambiaron entre peticiones.
3. Una conexión TCP por petición (o pipelining limitado).
4. Verbosidad de JSON: nombres de campo repetidos en cada objeto de la lista.

---

## Parte 2 — gRPC (HTTP/2 + Protocol Buffers)

### Instalación de dependencias

```bash
pip install grpcio grpcio-tools
```

### Paso 1 — Compilar el archivo .proto

```bash
cd parte2-grpc
python generar_proto.py
```

Genera `inventario_pb2.py` e `inventario_pb2_grpc.py` en la misma carpeta.

### Paso 2 — Ejecutar

```bash
# Terminal 1 — servidor gRPC
cd parte2-grpc
python servidor_grpc.py

# Terminal 2 — cliente gRPC
cd parte2-grpc
python cliente_grpc.py
```

### Definición del servicio (`inventario.proto`)

```protobuf
service Inventario {
  rpc ObtenerProducto (SolicitudProducto)      returns (Producto);
  rpc ListarProductos (SolicitudListar)         returns (ListaProductos);
  rpc AgregarProducto (SolicitudAgregarProducto) returns (RespuestaAgregar);
}
```

### Comparativa Protobuf vs JSON

| Mensaje           | Protobuf (bytes) | JSON (bytes) | Reducción |
|-------------------|-----------------|--------------|-----------|
| 1 Producto        | ~20             | ~70          | ~71 %     |
| Lista 3 productos | ~65             | ~220         | ~70 %     |
| Request agregar   | ~35             | ~58          | ~40 %     |

> Valores aproximados; el cliente gRPC imprime los bytes exactos en ejecución.

---

## Análisis: gRPC vs REST en microservicios con alto tráfico

### 1. Serialización (Protocol Buffers vs JSON)

REST usa JSON: texto plano, nombres de campo repetidos, sin tipado estricto.  
gRPC usa Protobuf: codificación binaria basada en índices numéricos de campo.

- Mensajes 30–70 % más pequeños que JSON equivalente.
- Serialización/deserialización más rápida que parsear JSON.
- El contrato está definido en el `.proto`; el compilador detecta mensajes mal formados antes de ejecutar.

### 2. HTTP/2 como transporte

| Característica | HTTP/1.1 (REST) | HTTP/2 (gRPC) |
|----------------|----------------|---------------|
| Conexiones TCP | 1 por petición (o pool limitado) | 1 única, multiplexada |
| Compresión de headers | ✗ | ✓ HPACK |
| Streams paralelos | ✗ | ✓ Múltiples simultáneos |
| Server push | ✗ | ✓ |
| Streaming bidireccional | ✗ | ✓ |

Con multiplexación, un servicio que llama a 10 dependencias puede usar una sola conexión TCP en lugar de establecer 10 handshakes separados.

### 3. Contratos tipados

El archivo `.proto` define explícitamente el contrato entre productor y consumidor:
- Los field numbers permiten compatibilidad hacia atrás al versionar la API.
- Se puede generar código cliente/servidor para múltiples lenguajes (Python, Go, Java, C++, etc.).

### 4. Patrones de streaming

| Patrón | Descripción | Ejemplo de uso |
|--------|-------------|----------------|
| Unario | Request → Response | Consulta de producto |
| Server streaming | Request → stream de Responses | Logs en tiempo real |
| Client streaming | stream de Requests → Response | Carga masiva de datos |
| Bidireccional | stream ↔ stream | Chat, telemetría continua |

REST requiere WebSockets o SSE para lograr algo similar.

### 5. Rendimiento bajo carga

Benchmark orientativo (varía por hardware y payload):

| Métrica | REST/HTTP1.1 + JSON | gRPC/HTTP2 + Protobuf |
|---------|--------------------|-----------------------|
| Throughput (req/s) | ~10 000 | ~80 000 |
| Latencia p99 | ~5 ms | ~0.8 ms |
| CPU serialización | alta (JSON) | baja (Protobuf) |
| Bytes por mensaje | mayor | menor |

### 6. Cuándo REST es más adecuado

- APIs públicas consumidas desde navegadores.
- Integraciones con sistemas que solo entienden HTTP+JSON.
- Cuando la legibilidad de los mensajes (debug con `curl`) es prioritaria.
- Equipos sin experiencia con Protobuf o herramientas de compilación.

---

## Requisitos del entorno

| Herramienta  | Versión mínima |
|--------------|---------------|
| Python       | 3.10          |
| grpcio       | 1.60          |
| grpcio-tools | 1.60          |

```bash
pip install grpcio grpcio-tools
```

La Parte 1 (REST) no requiere dependencias externas.
