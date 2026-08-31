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

No se requiere instalar ninguna dependencia; ambos scripts usan
exclusivamente la librería estándar de Python (`http.server`, `http.client`, `json`).

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

### Análisis de overhead de headers HTTP/1.1

En HTTP/1.1 los headers se transmiten como **texto plano** en cada petición,
sin compresión ni reutilización entre conexiones.

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

> Los valores exactos varían según el tamaño del catálogo.
> El cliente muestra los números reales en tiempo de ejecución.

#### ¿Por qué es un problema?

| Situación | Impacto del overhead |
|-----------|----------------------|
| Payload pequeño (un ID, un flag) | Headers > Body. El 80 % del tráfico es metadata |
| Alta frecuencia de peticiones (polling) | Cada petición repite headers idénticos (Host, Accept, Content-Type…) |
| Redes con bajo ancho de banda | El overhead acumulado satura el canal más rápido que los datos útiles |
| Microservicios internos (latencia baja requerida) | Cada ms adicional de parsing de texto impacta el SLA |

#### Razones técnicas del overhead

1. **Texto plano sin comprimir** — cada header es una cadena legible por humanos.
2. **Sin reutilización de estado de headers** — HTTP/1.1 no tiene mecanismo de "si el header no cambió, omítelo".
3. **Una conexión TCP por petición** (o pipelining limitado) — se añade latencia de handshake.
4. **Verbosidad de JSON** — nombres de campo repetidos en cada objeto de la lista.

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

Esto genera `inventario_pb2.py` e `inventario_pb2_grpc.py` en la misma carpeta.

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

### Comparativa de serialización Protobuf vs JSON

| Mensaje         | Protobuf (bytes) | JSON (bytes) | Reducción |
|-----------------|-----------------|--------------|-----------|
| 1 Producto      | ~20             | ~70          | ~71 %     |
| Lista 3 productos | ~65           | ~220         | ~70 %     |
| Request agregar | ~35             | ~58          | ~40 %     |

> Valores aproximados; el cliente gRPC imprime los bytes exactos en ejecución.

---

## Análisis: ¿Qué ventajas ofrece gRPC frente a REST en entornos de microservicios con alto tráfico?

### 1. Serialización binaria compacta (Protocol Buffers)

REST usa JSON: texto plano, nombres de campo repetidos en cada objeto, sin tipado estricto.  
gRPC usa Protobuf: codificación binaria basada en índices numéricos de campo.

- Mensajes **30–70 % más pequeños** que JSON equivalente.
- Serialización/deserialización **5–10× más rápida** que parsear JSON.
- El contrato del servicio está **definido en el `.proto`**: el compilador rechaza mensajes mal formados en tiempo de compilación, no en tiempo de ejecución.

### 2. HTTP/2 como transporte

| Característica | HTTP/1.1 (REST) | HTTP/2 (gRPC) |
|----------------|----------------|---------------|
| Conexiones TCP | 1 por petición (o pool limitado) | 1 única, multiplexada |
| Compresión de headers | ✗ | ✓ HPACK |
| Streams paralelos | ✗ | ✓ Múltiples simultáneos |
| Server push | ✗ | ✓ |
| Streaming bidireccional | ✗ | ✓ |

La **multiplexación** es especialmente valiosa en microservicios: un servicio que llama a 10 dependencias puede usar una sola conexión TCP abierta, eliminando el costo de establecer 10 handshakes.

### 3. Contratos fuertemente tipados

El archivo `.proto` actúa como un contrato explícito entre productor y consumidor:
- Versionado controlado de la API (fields numbers permiten compatibilidad hacia atrás).
- Generación automática de código cliente/servidor para cualquier lenguaje (Python, Go, Java, C++, etc.).
- Sin ambigüedades de "¿este campo es string o int?" que abundan en APIs REST sin esquema.

### 4. Streaming nativo

gRPC soporta cuatro patrones de comunicación:

| Patrón | Descripción | Caso de uso |
|--------|-------------|-------------|
| Unario | Request → Response | Consulta de producto |
| Server streaming | Request → stream de Responses | Logs en tiempo real |
| Client streaming | stream de Requests → Response | Carga masiva de datos |
| Bidireccional | stream ↔ stream | Chat, telemetría continua |

REST necesita WebSockets o SSE para aproximarse a alguno de estos patrones.

### 5. Rendimiento bajo alta carga

Benchmark orientativo (varía por hardware y payload):

| Métrica | REST/HTTP1.1 + JSON | gRPC/HTTP2 + Protobuf |
|---------|--------------------|-----------------------|
| Throughput (req/s) | ~10 000 | ~80 000 |
| Latencia p99 | ~5 ms | ~0.8 ms |
| CPU serialización | alta (JSON) | baja (Protobuf) |
| Bytes por mensaje | mayor | menor |

### 6. Cuándo REST sigue siendo preferible

- APIs públicas consumidas por navegadores o clientes no controlados.
- Equipos sin experiencia con Protobuf o herramientas de compilación.
- Integraciones con sistemas legacy que solo entienden HTTP+JSON.
- Cuando la legibilidad humana de los mensajes (debug con `curl`) es prioritaria.

### Conclusión

En arquitecturas de microservicios con **alto tráfico interno**, gRPC reduce significativamente el consumo de red, la latencia y la carga de CPU gracias a la combinación de Protobuf + HTTP/2. REST mantiene su ventaja en interoperabilidad y simplicidad de adopción para APIs públicas o equipos con menor madurez tecnológica.

---

## Requisitos del entorno

| Herramienta | Versión mínima |
|-------------|---------------|
| Python      | 3.10          |
| grpcio      | 1.60          |
| grpcio-tools| 1.60          |

Instalar dependencias de la Parte 2:
```bash
pip install grpcio grpcio-tools
```

La Parte 1 (REST) no requiere dependencias externas.
