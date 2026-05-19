# Diseño Técnico de la Solución
## Sistema Distribuido de Clasificación de Órdenes Médicas — Chernovia

**Empresa oferente:** DataHealth Cloud Solutions  
**Versión:** 2.0 | **Fecha:** Mayo 2026

---

## 1. Arquitectura General

### 1.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOBIERNO DE CHERNOVIA — SISTEMA DE SALUD             │
│                                                                         │
│  Fuentes de datos          Procesamiento Distribuido      Servicios     │
│                                                                         │
│  ┌──────────────┐          ┌─────────────────────┐       ┌──────────┐  │
│  │ Hospitales   │          │    AWS S3 Bucket     │       │   EC2    │  │
│  │ Clínicas     │──CSV──▶  │  ┌───────────────┐  │       │ t3.micro │  │
│  │ Apps móviles │          │  │  raw/         │  │       │          │  │
│  └──────────────┘          │  │  ├ dataset.csv │  │──────▶│ FastAPI  │  │
│                            │  │  ├ servicios.  │  │       │ :8000   │  │
│                            │  │  └ perfiles.  │  │       └────┬─────┘  │
│                            │  └───────────────┘  │            │        │
│                            │  ┌───────────────┐  │            │        │
│                            │  │  results/     │  │◀───────────┘        │
│                            │  │  └ *.parquet  │  │            │        │
│                            │  └───────────────┘  │            │        │
│                            │  ┌───────────────┐  │            ▼        │
│                            │  │  frontend/    │  │       ┌──────────┐  │
│                            │  │  └ index.html │  │       │Dashboard │  │
│                            │  └───────────────┘  │       │  React   │  │
│                            └──────────┬──────────┘       └──────────┘  │
│                                       │                                 │
│                            ┌──────────▼──────────┐                     │
│                            │    AWS GLUE ETL      │                     │
│                            │  ┌─────────────────┐ │                     │
│                            │  │  PySpark Job    │ │                     │
│                            │  │  Worker 1 ──┐   │ │                     │
│                            │  │  Worker 2 ──┼──▶│ │  Clasificación     │
│                            │  │  Worker N ──┘   │ │  distribuida       │
│                            │  └─────────────────┘ │                     │
│                            └──────────┬──────────┘                     │
│                                       │                                 │
│                            ┌──────────▼──────────┐                     │
│                            │   AWS CloudWatch     │                     │
│                            │   Logs & Métricas    │                     │
│                            └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Componentes y Responsabilidades

| Componente | Tecnología | Rol | Costo |
|---|---|---|---|
| **Almacenamiento distribuido** | AWS S3 | Raw data + Resultados + Frontend | $0.05/mes |
| **Motor de procesamiento** | AWS Glue + PySpark | ETL distribuido de 1.2M+ registros | $2.20/mes |
| **API REST** | FastAPI + EC2 t3.micro | Servicio de datos al dashboard | $7.50/mes |
| **Dashboard** | React + S3 Static Website | Visualización en tiempo real | $0/mes |
| **Observabilidad** | AWS CloudWatch | Logs, métricas, alertas | $0.50/mes |
| **Trazabilidad** | S3 Versioning | Auditoría de cada resultado | $0.09/mes |

---

## 2. Flujo de Datos Detallado

### 2.1 Pipeline de Procesamiento (5 Etapas)

```
ETAPA 1: RECEPCIÓN
├── Las solicitudes médicas en formato CSV llegan al bucket S3 (raw/)
├── S3 Event Notifications detecta nuevos archivos (opcional: Lambda trigger)
└── Dataset: COIL_dataset_glosas_salud_1_2M.csv (360 MB, 1.2M registros)

ETAPA 2: EXTRACCIÓN (AWS Glue PySpark)
├── Glue lee el CSV directamente desde S3 (streaming distribuido)
├── Extracción de campos de la glosa mediante expresiones regulares:
│   ├── ServicioSolicitado: regex → r"ServicioSolicitado:\s*([^;]+)"
│   └── PerfilCobertura:    regex → r"PerfilCobertura:\s*([^;]+)"
└── Broadcast de catálogos a todos los workers (optimización clave)

ETAPA 3: CLASIFICACIÓN (Distribuida en N Workers)
├── Worker 1..N: is_covered(servicio) → lookup en conjunto broadcast
├── Regla: si servicio ∈ catálogo_cubiertos → cubre = TRUE
└── Complejidad: O(1) por registro (lookup en Set)

ETAPA 4: CÁLCULO DE COBERTURA
├── Lookup perfil → porcentaje (100%, 50%, 25%)
├── Si cubre = FALSE → porcentaje = 0, valor_cubierto = 0
└── valor_cubierto = valor_procedimiento × porcentaje / 100

ETAPA 5: DECISIÓN Y ALMACENAMIENTO TRAZABLE
├── Resultado guardado como Parquet en S3 (results/)
├── S3 Versioning: cada ejecución genera una versión versionada
├── CloudWatch: registro de tiempo, workers usados, registros procesados
└── FastAPI lee resultados y los sirve al Dashboard en tiempo real
```

### 2.2 Estructura de Datos de Entrada (Glosa)

```
Paciente: María González; DNO: 12345678; SeguroSocial: SS-987654;
Edad: 45; PerfilCobertura: BASICO; ServicioSolicitado: Cirugía cardiovascular;
Medicacion: Aspirina|Warfarina|Metoprolol
```

### 2.3 Estructura de Datos de Salida (Parquet)

```
id_solicitud         → Identificador único
fecha_solicitud      → Timestamp de la solicitud
medio_emisor         → Canal de ingreso
valor_procedimiento  → Valor monetario del procedimiento
entidad_emisora      → Hospital/Clínica emisora
servicio_solicitado  → Extraído de glosa
perfil_cobertura     → Extraído de glosa (BASICO/INTERMEDIO/PREMIUM)
cubre                → Boolean: TRUE/FALSE
porcentaje_cobertura → 0, 25, 50 o 100
valor_cubierto       → valor_procedimiento × porcentaje / 100
```

---

## 3. Lógica de Clasificación

### 3.1 Árbol de Decisión

```
                    ┌─────────────────────────┐
                    │  ¿Servicio en catálogo  │
                    │     de cubiertos?       │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │ NO                                │ SÍ
              ▼                                  ▼
    ┌─────────────────┐               ┌──────────────────────┐
    │   NO CUBRE      │               │ ¿Perfil del usuario? │
    │  Porcentaje: 0% │               └──────────┬───────────┘
    │  Valor: $0      │                          │
    └─────────────────┘         ┌────────────────┼────────────────┐
                                │                │                │
                           PREMIUM           INTERMEDIO        BASICO
                                │                │                │
                                ▼                ▼                ▼
                          100% cubierto    50% cubierto    25% cubierto
```

### 3.2 Reglas de Negocio Implementadas

```python
# Regla 1: Clasificación de cobertura
cubre = servicio_solicitado IN catalogo_servicios_cubiertos

# Regla 2: Porcentaje por perfil (solo si cubre = TRUE)
porcentaje = {
    "PREMIUM":     100,
    "INTERMEDIO":  50,
    "BASICO":      25,
}.get(perfil_cobertura, 0)

# Regla 3: Valor cubierto
valor_cubierto = valor_procedimiento * porcentaje / 100 if cubre else 0
```

---

## 4. Estrategia de Escalabilidad

### 4.1 Escalabilidad Horizontal (AWS Glue)

AWS Glue escala automáticamente el número de workers según el volumen de datos:

| Volumen diario | Workers DPU | Tiempo estimado | Costo por ejecución |
|---|---|---|---|
| 1.2M registros (demo) | 2 DPU | ~8 min | $0.073 |
| 5M registros | 4 DPU | ~10 min | $0.15 |
| 12M registros (objetivo) | 8 DPU | ~12 min | $0.29 |
| 50M registros (escala máxima) | 20 DPU | ~18 min | $0.73 |

**Nota clave:** El tiempo de procesamiento crece logarítmicamente, no linealmente, gracias a la paralelización.

### 4.2 Optimizaciones Implementadas

1. **Broadcast variables:** Los catálogos (servicios y perfiles) se distribuyen a todos los workers una sola vez, evitando joins costosos.
2. **Formato Parquet:** Columnar, comprimido y optimizado para consultas analíticas. 10x más eficiente que CSV para lectura.
3. **In-memory caching:** La API mantiene el DataFrame en memoria para consultas < 1ms.
4. **Chunked reading:** Lectura del CSV en chunks de 200K registros para manejo eficiente de memoria en modo local.

---

## 5. Estrategia de Trazabilidad

### 5.1 S3 Versioning

Cada vez que se ejecuta el pipeline, el archivo `results/resultado_clasificacion.parquet` en S3 genera automáticamente una nueva versión:

```
results/resultado_clasificacion.parquet
├── Version ID: abc123 (ejecución: 2026-05-19 02:00)
├── Version ID: def456 (ejecución: 2026-05-18 02:00)
└── Version ID: ghi789 (ejecución: 2026-05-17 02:00)
```

Esto permite **auditoría completa** de cualquier decisión pasada consultando la versión correspondiente.

### 5.2 CloudWatch Logs

Cada ejecución del Glue Job registra automáticamente en CloudWatch:
- Timestamp de inicio y fin
- Número de workers activos
- Registros procesados
- Errores (si los hay)
- Tiempo de ejecución total

### 5.3 Campos de Trazabilidad en Resultados

Cada fila del resultado incluye: `id_solicitud`, `fecha_solicitud`, `entidad_emisora`, `cubre`, `porcentaje_cobertura`, `valor_cubierto` — suficiente para reconstruir cualquier decisión.

---

## 6. API REST — Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/process` | Dispara AWS Glue ETL (procesamiento distribuido) |
| `GET` | `/api/process/status` | Estado del job Glue en tiempo real |
| `GET` | `/api/stats` | Estadísticas agregadas del dataset |
| `GET` | `/api/solicitudes` | Lista paginada con filtros |
| `GET` | `/api/export` | Descarga CSV completo de resultados |
| `GET` | `/health` | Health check del sistema |

---

## 7. Tecnologías Seleccionadas y Justificación

| Tecnología | Justificación | Alternativa descartada |
|---|---|---|
| **AWS Glue (PySpark)** | Serverless, escalable, pago por uso, integrado con S3 | EMR: más caro, requiere gestión de cluster |
| **Amazon S3** | Durabilidad 99.999999999%, acceso global, versioning nativo | EFS/EBS: más caro, menor durabilidad |
| **FastAPI (Python)** | Más rápido que Flask, async nativo, documentación automática | Django REST: más pesado, mayor consumo de memoria |
| **EC2 t3.micro** | Free tier elegible, suficiente para servir resultados Parquet | Lambda: límite 15 min, no apto para polling de Glue |
| **React + Vite** | SPA moderna, bundle optimizado, despliegue en S3 sin servidor | Angular: más pesado, mayor tiempo de carga |
| **Parquet** | 5-10x más eficiente que CSV, compresión nativa, columnar | CSV: lento para consultas, sin compresión |

---

*Documento técnico — DataHealth Cloud Solutions — Mayo 2026*
