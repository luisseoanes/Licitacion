# Diseño Técnico de la Solución
## Sistema Distribuido de Clasificación de Órdenes Médicas — Chernovia

**Empresa oferente:** DataHealth Cloud Solutions  
**Versión:** 3.0 | **Fecha:** Mayo 2026

---

## 1. Arquitectura General

### 1.1 Diagrama de Arquitectura

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     GOBIERNO DE CHERNOVIA — SISTEMA DE SALUD                 │
│                                                                              │
│  Fuentes de datos          Procesamiento Distribuido        Servicios        │
│                                                                              │
│  ┌──────────────┐          ┌──────────────────────┐       ┌─────────────┐   │
│  │ Hospitales   │          │    AWS S3 Bucket      │       │ EC2 t3.micro│   │
│  │ Clínicas     │──CSV──▶  │  ┌────────────────┐  │       │             │   │
│  │ Apps móviles │          │  │  raw/          │  │──────▶│  FastAPI    │   │
│  └──────────────┘          │  │  catálogos CSV │  │       │  :8000      │   │
│                            │  └────────────────┘  │       │             │   │
│                            │  ┌────────────────┐  │       │ ClasificadorML  │
│                            │  │  results/      │  │◀──────│ DetectorAno.│   │
│                            │  │  └ *.parquet   │  │       │ SimuladorPol│   │
│                            │  └────────────────┘  │       │ GeneradorPDF│   │
│                            │  ┌────────────────┐  │       │ CatálogoAdm.│   │
│                            │  │  deploy/       │  │       └──────┬──────┘   │
│                            │  │  └ scripts py  │  │              │          │
│                            │  └────────────────┘  │              ▼          │
│                            └──────────┬───────────┘       ┌─────────────┐   │
│                                       │                    │  Dashboard  │   │
│                            ┌──────────▼───────────┐       │  React SPA  │   │
│                            │    AWS GLUE ETL       │       │  5 páginas  │   │
│                            │  ┌──────────────────┐ │       └─────────────┘   │
│                            │  │  PySpark Job     │ │                         │
│                            │  │  Worker 1 ──┐    │ │  Clasificación          │
│                            │  │  Worker 2 ──┼───▶│ │  distribuida            │
│                            │  │  Worker N ──┘    │ │  + razon_decision       │
│                            │  └──────────────────┘ │                         │
│                            └──────────┬───────────┘                         │
│                                       │                                      │
│                            ┌──────────▼───────────┐                         │
│                            │   AWS CloudWatch      │                         │
│                            │   Logs & Métricas     │                         │
│                            └──────────────────────┘                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Componentes y Responsabilidades

| Componente | Tecnología | Rol | Costo |
|---|---|---|---|
| **Almacenamiento distribuido** | AWS S3 | Raw data + Resultados + Frontend + Catálogos | $0.25/mes |
| **Motor de procesamiento** | AWS Glue + PySpark | ETL distribuido de 1.2M+ registros + razon_decision | $0.76/mes |
| **API REST + Módulos** | FastAPI + EC2 t3.micro | 16 endpoints: servicio, anomalías, simulador, PDF, catálogos | $9.11/mes |
| **Dashboard** | React SPA (5 páginas) | Dashboard · Solicitudes · Demo ML · Anti-Fraude · Simulador · Catálogos | $0/mes |
| **Observabilidad** | AWS CloudWatch | Logs, métricas, alertas por job Glue | $0.50/mes |
| **Trazabilidad** | S3 Versioning | Auditoría de cada resultado + campo razon_decision | $0/mes adicional |

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

ETAPA 3: CLASIFICACIÓN HÍBRIDA (Distribuida en N Workers)
├── Nivel 1 — Exacto: servicio ∈ catálogo_cubiertos → cubre = TRUE/FALSE
│   └── Complejidad: O(1) por registro (lookup en Set)
├── Nivel 2 — Fuzzy ML (API, tiempo real): TF-IDF char_wb ngrams 2–4
│   ├── Vectorización: scikit-learn TfidfVectorizer
│   ├── Similitud: cosine_similarity vs. catálogo completo
│   ├── Umbral: sim ≥ 0.72 → fuzzy_ml; sim ≥ 0.40 → sin_match
│   └── Resultado incluye: servicio_canonico, confianza, metodo
└── El nivel 2 opera por solicitud individual vía /api/classify

ETAPA 4: CÁLCULO DE COBERTURA
├── Lookup perfil → porcentaje (100%, 50%, 25%)
├── Si cubre = FALSE → porcentaje = 0, valor_cubierto = 0
└── valor_cubierto = valor_procedimiento × porcentaje / 100

ETAPA 5: DECISIÓN EXPLICADA Y ALMACENAMIENTO TRAZABLE
├── Generación de razon_decision: texto en lenguaje natural por registro
├── Resultado guardado como Parquet en S3 (results/) con razon_decision
├── S3 Versioning: cada ejecución genera una versión versionada
├── CloudWatch: registro de tiempo, workers usados, registros procesados
├── FastAPI lee resultados y los sirve al Dashboard en tiempo real
└── DetectorAnomalias analiza el batch completo post-clasificación
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
perfil_cobertura     → Extraído de glosa (PRIORITARIO/ESTANDAR/COPAGO)
cubre                → Boolean: TRUE/FALSE
porcentaje_cobertura → 0, 25, 50 o 100
valor_cubierto       → valor_procedimiento × porcentaje / 100
razon_decision  ★   → Justificación en lenguaje natural (NUEVO v3.0)
                       Ej: "Servicio 'Cirugía cardiovascular' identificado en el
                       catálogo de servicios cubiertos bajo resolución DS-2024-001.
                       Perfil PRIORITARIO: cobertura del 100% ($1,500.00 cubiertos)."
```

> **★ Campo diferencial:** `razon_decision` convierte cada fila del Parquet en un registro completamente auditable y legible por humanos, cumpliendo con los principios de explicabilidad de la IA en decisiones que afectan derechos ciudadanos.

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
    │  razon_decision │         ┌────────────────┼────────────────┐
    │  explica        │         │                │                │
    └─────────────────┘  PRIORITARIO        ESTANDAR          COPAGO
                                │                │                │
                                ▼                ▼                ▼
                          100% cubierto    50% cubierto    25% cubierto
                          razon_decision   razon_decision   razon_decision
                          referencia       referencia       referencia
                          DS-2024-001      DS-2024-001      DS-2024-001
```

### 3.2 Reglas de Negocio Implementadas

```python
# Regla 1: Clasificación de cobertura (batch Glue + exacto API)
cubre = servicio_solicitado IN catalogo_servicios_cubiertos

# Regla 2: Porcentaje por perfil (solo si cubre = TRUE)
porcentaje = {
    "PRIORITARIO": 100,
    "ESTANDAR":     50,
    "COPAGO":       25,
}.get(perfil_cobertura, 0)

# Regla 3: Valor cubierto
valor_cubierto = valor_procedimiento * porcentaje / 100 if cubre else 0

# Regla 4: Explicabilidad (NUEVO v3.0)
razon_decision = _generar_razon(row)
# → "Servicio '{svc}' identificado en catálogo DS-2024-001. Perfil {p}: {pct}%."
# → "Servicio '{svc}' no figura en catálogo DS-2024-001. Cobertura denegada."
```

### 3.3 Motor ML — Fuzzy Matching (ClasificadorML)

Para solicitudes individuales en tiempo real (`/api/classify`), el motor ML maneja variantes ortográficas:

```python
# TF-IDF sobre n-gramas de caracteres (2–4): robusto ante errores tipográficos
vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)

# Similitud coseno contra catálogo completo
sims = cosine_similarity(query_vec, catalogo_matrix)[0]

# Umbrales de decisión
if sim >= 0.72:  metodo = "fuzzy_ml"   # match aproximado
elif sim < 0.40: metodo = "sin_match"  # no encontrado
else:            metodo = "exacto"     # match exacto previo

# razon_decision diferenciada por método (NUEVO v3.0)
# fuzzy_ml:  "Match aproximado (confianza 0.94) entre 'Cirugia cardiovascular'
#             y 'Cirugía cardiovascular' via TF-IDF ngrams. DS-2024-001."
# sin_match: "Servicio 'XYZ' no pudo ser identificado (confianza < 0.72)."
```

**Ejemplo real:** "Cirugia cardiovascular" → "Cirugía cardiovascular" con confianza 0.94, método fuzzy_ml.

---

## 4. Módulos Diferenciales (v3.0)

Los siguientes módulos corren en la misma instancia EC2 t3.micro. **Costo adicional: $0.**

### 4.1 DetectorAnomalías (`detector_anomalias.py`)

Analiza el dataset batch post-clasificación y aplica 4 reglas estadísticas para detectar fraude y anomalías:

```
REGLA AN-DUP-001 — Duplicados (GRAVEDAD: ALTA)
  Condición: mismo DNO + mismo servicio + mismo día > 1 solicitud
  Acción: marca todas las ocurrencias adicionales como sospechosas

REGLA AN-VAL-002 — Valor atípico (GRAVEDAD: MEDIA)
  Condición: valor_procedimiento > media_por_servicio + 3 desviaciones estándar
  Acción: alerta al auditor con el valor observado vs. esperado

REGLA AN-ENT-003 — Entidad sospechosa (GRAVEDAD: MEDIA)
  Condición: tasa de rechazo de una entidad < 5% en ≥ 10 solicitudes
  Interpretación: tasa de cobertura anormalmente alta → posible captura de beneficios
  Acción: agrega entidad a lista de vigilancia

REGLA AN-EDAD-004 — Incompatibilidad edad-servicio (GRAVEDAD: ALTA)
  Condición: servicio pediátrico solicitado para paciente mayor de 18 años
  Acción: marca solicitud para revisión manual
```

**Endpoint:** `GET /api/anomalias` → retorna JSON con `total_anomalias`, `tasa_anomalia_pct`, `resumen_por_tipo`, lista de anomalías con detalle.

### 4.2 SimuladorPolítica (`/api/simulate`)

Permite al equipo de política pública proyectar el impacto fiscal de cambios en el catálogo **antes** de aplicarlos:

```
Entrada (POST /api/simulate):
  agregar_servicios: ["Cirugía láser", "Psicología online"]
  quitar_servicios:  ["Medicina alternativa"]
  cambiar_perfiles:  {"ESTANDAR": 60, "COPAGO": 30}

Proceso:
  1. Aplica los cambios hipotéticos sobre una copia del catálogo
  2. Reclasifica la muestra de 10K solicitudes disponibles
  3. Calcula delta de cobertura y costo fiscal adicional

Salida:
  solicitudes_antes: 6,500 cubiertas (65%)
  solicitudes_despues: 7,200 cubiertas (72%)
  delta_cobertura_pct: +7%
  costo_fiscal_adicional_usd: +$124,500
  detalle_por_cambio: [{servicio, impacto_solicitudes, impacto_usd}]
```

### 4.3 GeneradorReporte (`generador_reporte.py`)

Genera automáticamente un PDF ejecutivo post-ejecución usando `reportlab`:

```
Contenido del PDF (secciones):
  1. Header: logo DataHealth + fecha ejecución + total registros
  2. KPIs principales: total solicitudes / cubiertas / tasa / costo cubierto
  3. Distribución diaria: tabla por fecha
  4. Cobertura por perfil: PRIORITARIO / ESTANDAR / COPAGO
  5. Top 10 servicios más solicitados
  6. Resumen de anomalías detectadas (si las hay)
  7. Footer con referencia DS-2024-001
```

**Endpoint:** `GET /api/reporte` → `StreamingResponse` con Content-Type `application/pdf`.

### 4.4 CatálogoAdmin (Endpoints CRUD)

Permite actualizar el catálogo de servicios y perfiles de cobertura desde el dashboard, sin programadores:

```
Servicios:
  GET    /api/catalogo/servicios           → lista todos los servicios
  POST   /api/catalogo/servicios           → agrega servicio {nombre, cubre_sistema_publico}
  DELETE /api/catalogo/servicios/{servicio} → elimina servicio

Perfiles:
  GET  /api/catalogo/perfiles              → lista todos los perfiles con porcentaje
  PUT  /api/catalogo/perfiles/{perfil}     → actualiza porcentaje de un perfil

Comportamiento:
  - Cada cambio persiste en S3 (COIL_catalogo_servicios_cubiertos.csv)
  - El modelo ML (_ml_model) se resetea a None para forzar recarga con el nuevo catálogo
  - Próxima clasificación usará el catálogo actualizado automáticamente
```

---

## 5. Estrategia de Escalabilidad

### 5.1 Escalabilidad Horizontal (AWS Glue)

AWS Glue escala automáticamente el número de workers según el volumen de datos:

| Volumen diario | Workers | Tiempo estimado | Costo por ejecución |
|---|---|---|---|
| 1.2M registros (demo) | 2 G.1X | **~105 segundos (medido)** | $0.026 |
| 5M registros | 4 G.1X | ~8 min | $0.093 |
| 12M registros (objetivo) | 8 G.1X | ~12 min | $0.280 |
| 50M registros (escala máxima) | 20 G.1X | ~18 min | $1.160 |

**Nota clave:** El tiempo de procesamiento crece logarítmicamente, no linealmente, gracias a la paralelización. El campo `razon_decision` se genera distribuido en cada worker, sin overhead medible.

### 5.2 Optimizaciones Implementadas

1. **Broadcast variables:** Los catálogos (servicios y perfiles) se distribuyen a todos los workers una sola vez, evitando joins costosos.
2. **Formato Parquet:** Columnar, comprimido y optimizado para consultas analíticas. 10x más eficiente que CSV para lectura.
3. **Stats pre-agregadas:** La API computa agregaciones archivo-por-archivo en carga y descarta el DataFrame completo. Mantiene únicamente una muestra de 10K filas (~15MB) para paginación, evitando OOM en instancias t3.micro.
4. **Chunked reading:** Lectura del CSV en chunks de 200K registros para manejo eficiente de memoria en modo local.
5. **Módulos diferenciales co-localizados:** DetectorAnomalías, SimuladorPolítica, GeneradorReporte y CatálogoAdmin reutilizan el DataFrame ya cargado en memoria, sin I/O adicional.

---

## 6. Estrategia de Trazabilidad (4 Pilares)

### 6.1 S3 Versioning

Cada vez que se ejecuta el pipeline, el archivo `results/resultado_clasificacion.parquet` en S3 genera automáticamente una nueva versión:

```
results/resultado_clasificacion.parquet
├── Version ID: abc123 (ejecución: 2026-05-19 02:00)
├── Version ID: def456 (ejecución: 2026-05-18 02:00)
└── Version ID: ghi789 (ejecución: 2026-05-17 02:00)
```

### 6.2 CloudWatch Logs

Cada ejecución del Glue Job registra automáticamente en CloudWatch:
- Timestamp de inicio y fin
- Número de workers activos
- Registros procesados
- Errores (si los hay)
- Tiempo de ejecución total

### 6.3 Campos de Trazabilidad en Resultados

Cada fila del resultado incluye: `id_solicitud`, `fecha_solicitud`, `entidad_emisora`, `cubre`, `porcentaje_cobertura`, `valor_cubierto` — suficiente para reconstruir cualquier decisión.

### 6.4 Explicabilidad Nativa — `razon_decision` ★ (Nuevo v3.0)

Cada registro incluye un texto en lenguaje natural que explica la decisión tomada, con referencia explícita a la resolución DS-2024-001:

```
Ejemplo 1 (cubierto, batch):
  "Servicio 'Cirugía cardiovascular' identificado en el catálogo de servicios
   cubiertos bajo resolución DS-2024-001. Perfil PRIORITARIO: cobertura del
   100% aplicada. Valor cubierto: $1,500.00."

Ejemplo 2 (no cubierto, batch):
  "Servicio 'Medicina alternativa' no figura en el catálogo de servicios
   cubiertos según resolución DS-2024-001. Cobertura denegada. Valor cubierto: $0."

Ejemplo 3 (fuzzy ML, API individual):
  "Match aproximado (confianza: 0.94) entre 'Cirugia cardiovascular' y
   'Cirugía cardiovascular' mediante TF-IDF ngrams char_wb. Resolución
   DS-2024-001: servicio cubierto. Perfil ESTANDAR: 50% cubierto."
```

Este campo convierte el sistema en un registro legible para auditores, médicos y funcionarios públicos, cumpliendo con los principios de IA explicable (XAI) y los requisitos de transparencia en decisiones administrativas.

---

## 7. API REST — Endpoints (v3.0)

| Método | Endpoint | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/process` | Dispara AWS Glue ETL (procesamiento distribuido) | API Key |
| `GET` | `/api/process/status` | Estado del job Glue en tiempo real | API Key |
| `GET` | `/api/stats` | Estadísticas agregadas pre-calculadas | API Key |
| `GET` | `/api/solicitudes` | Lista paginada con filtros (perfil, cubre, search) | API Key |
| `GET` | `/api/export` | Descarga CSV con razon_decision incluida | API Key |
| `POST` | `/api/classify` | Clasificación individual ML + razon_decision | API Key |
| `GET` | `/api/quality` | Métricas de calidad del modelo ML (parseo, confianza) | API Key |
| `GET` | `/api/glue/status` | Verifica disponibilidad del job de Glue | API Key |
| `GET` | `/api/anomalias` | **★ Detección de fraude y anomalías (4 reglas)** | API Key |
| `POST` | `/api/simulate` | **★ Simulador de política fiscal** | API Key |
| `GET` | `/api/reporte` | **★ Genera PDF ejecutivo automático** | API Key |
| `GET` | `/api/catalogo/servicios` | **★ Lista catálogo de servicios** | API Key |
| `POST` | `/api/catalogo/servicios` | **★ Agrega servicio al catálogo** | API Key |
| `DELETE` | `/api/catalogo/servicios/{svc}` | **★ Elimina servicio del catálogo** | API Key |
| `GET` | `/api/catalogo/perfiles` | **★ Lista perfiles de cobertura** | API Key |
| `PUT` | `/api/catalogo/perfiles/{perfil}` | **★ Actualiza porcentaje de perfil** | API Key |
| `GET` | `/health` | Health check del sistema (sin auth) | — |

> **★ Endpoints diferenciales v3.0:** 8 nuevos endpoints que no ofrecen los competidores.

**Base URL de producción:** `http://184.72.124.136:8000`  
**Autenticación:** Header `X-API-Key: <clave>` en todos los endpoints `/api/*`.

---

## 8. Tecnologías Seleccionadas y Justificación

| Tecnología | Justificación | Alternativa descartada |
|---|---|---|
| **AWS Glue (PySpark)** | Serverless, escalable, pago por uso, integrado con S3 | EMR: más caro, requiere gestión de cluster |
| **Amazon S3** | Durabilidad 99.999999999%, acceso global, versioning nativo | EFS/EBS: más caro, menor durabilidad |
| **FastAPI (Python)** | Más rápido que Flask, async nativo, documentación automática | Django REST: más pesado, mayor consumo de memoria |
| **EC2 t3.micro** | Free tier elegible, suficiente para servir resultados Parquet + 4 módulos diferenciales | Lambda: límite 15 min, no apto para polling de Glue |
| **React + Vite** | SPA moderna, bundle optimizado, 5 páginas funcionales | Angular: más pesado, mayor tiempo de carga |
| **Parquet** | 5-10x más eficiente que CSV, compresión nativa, columnar | CSV: lento para consultas, sin compresión |
| **scikit-learn TF-IDF** | Fuzzy matching robusto con n-gramas de caracteres, sin dependencias externas | Elasticsearch: caro, requiere cluster separado |
| **reportlab 4.1.0** | Generación de PDF en Python puro, sin servidor de documentos, 0 costo adicional | WeasyPrint: dependencias de sistema; Puppeteer: requiere Node.js |
| **Terraform >= 1.5** | Infrastructure as Code: toda la infraestructura AWS versionada en git, reproducible con `terraform apply` | CloudFormation: sintaxis más verbosa, solo AWS; CDK: requiere Node.js |

---

## 9. Infraestructura como Código (IaC) — Terraform

Toda la infraestructura AWS del proyecto está declarada en código Terraform bajo el directorio `terraform/`, siguiendo las mejores prácticas de Infrastructure as Code (IaC). Esto garantiza que el entorno sea **reproducible**, **versionado en git** y **auditable** — un requisito implícito en cualquier sistema de salud pública que deba ser replicable en distintas regiones o entornos.

### 9.1 Archivos del Módulo Terraform

```
terraform/
├── main.tf                  # Recursos AWS: S3, IAM, EC2, Glue, CloudWatch, SG
├── variables.tf             # Variables con validación (instance_type, glue_workers, etc.)
├── outputs.tf               # Outputs: API URL, EC2 ID, bucket ARN, Glue job name
└── terraform.tfvars.example # Plantilla de configuración
```

### 9.2 Recursos Declarados

| Recurso Terraform | Tipo AWS | Configuración |
|---|---|---|
| `aws_s3_bucket.data_lake` | S3 Bucket | Versioning + AES-256 + acceso privado + lifecycle 30/90 días |
| `aws_iam_role.glue_role` | IAM Role | Trust: glue.amazonaws.com + política S3 + CloudWatch |
| `aws_iam_role.ec2_role` | IAM Role | Trust: ec2.amazonaws.com + S3 + Glue + SSM + CloudWatch |
| `aws_security_group.api` | Security Group | Ingress :8000 (público) + :22 (SSH) |
| `aws_instance.api` | EC2 t3.micro | AMI Amazon Linux 2 + user_data bootstrap completo |
| `aws_glue_job.clasificacion` | Glue Job | PySpark 4.0 + G.1X workers + CloudWatch continuo |
| `aws_cloudwatch_log_group.api` | CloudWatch | Retención 30 días |
| `aws_cloudwatch_log_group.glue` | CloudWatch | Retención 30 días |

### 9.3 Flujo de Aprovisionamiento

```bash
# 1. Configurar variables
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Editar terraform.tfvars con bucket_suffix = ID de cuenta AWS

# 2. Inicializar providers
terraform -chdir=terraform init

# 3. Verificar plan antes de aplicar
terraform -chdir=terraform plan

# 4. Aprovisionar infraestructura completa (~3 minutos)
terraform -chdir=terraform apply

# 5. Obtener URL del sistema
terraform -chdir=terraform output api_url
# → http://<IP>:8000

# 6. Para escalar a 12M solicitudes (cambiar solo instance_type)
terraform -chdir=terraform apply -var="instance_type=t3.small"
```

### 9.4 Escalado Declarativo

El escalado de 1.2M a 12M solicitudes diarias requiere cambiar **una sola variable** en el tfvars:

```hcl
# Para 1.2M solicitudes/día (demo actual)
instance_type     = "t3.micro"
glue_max_capacity = 4   # 2 G.1X workers

# Para 12M solicitudes/día (objetivo Chernovia)
instance_type     = "t3.small"
glue_max_capacity = 16  # 8 G.1X workers
```

`terraform apply` aplica únicamente los cambios necesarios, sin recrear recursos estables (S3, IAM, CloudWatch). **Tiempo de escalado: ~90 segundos** (reemplazo de instancia EC2 + ajuste del Glue job).

---

*Documento técnico — DataHealth Cloud Solutions — Mayo 2026*  
*Versión 3.0 — Incluye módulos diferenciales: Explicabilidad, Anti-fraude, Simulador, PDF, Admin catálogos, IaC Terraform*
