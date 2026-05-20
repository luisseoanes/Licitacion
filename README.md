# Chernovia Health — Sistema Distribuido de Clasificación de Órdenes Médicas

Sistema cloud-native para clasificar automáticamente 1.2M+ órdenes médicas diarias, determinando elegibilidad y porcentaje de cobertura del seguro público de salud de Chernovia.

## Arquitectura

```
Datos CSV (S3)
     ↓
AWS Glue + PySpark (clasificación distribuida)
     ↓
Resultados Parquet (S3, versionado)
     ↓
FastAPI (EC2 t3.micro) — lectura cacheada
     ↓
React SPA (Dashboard analítico)
     ↓
CloudWatch (logs y métricas)
```

**Stack:** Python · FastAPI · PySpark · AWS Glue · S3 · EC2 · React · Tailwind CSS · Recharts

## Requisitos

- Python 3.11+
- Node.js 20+
- AWS CLI configurado (`aws configure`)
- Cuenta AWS con permisos para S3, Glue, EC2, CloudWatch, IAM

## Configuración de variables de entorno

Copia el archivo de ejemplo y completa los valores:

```bash
cp backend/.env.example backend/.env
```

Edita `backend/.env`:

```env
S3_BUCKET=tu-bucket-s3
GLUE_JOB_NAME=chernovia-clasificacion-batch
API_KEY=tu-clave-secreta-aqui
ALLOWED_ORIGINS=http://localhost:5173
```

## Ejecución local

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`.  
Documentación automática: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La app estará disponible en `http://localhost:5173`.

> El frontend usa proxy hacia `localhost:8000` en desarrollo (configurado en `vite.config.js`).

### Con Docker

```bash
# Solo el backend
docker build -t chernovia-backend ./backend
docker run -p 8000:8000 --env-file backend/.env chernovia-backend

# Stack completo
docker compose up
```

## Tests

```bash
cd backend
pip install pytest pytest-mock
pytest tests/ -v
```

## Despliegue en AWS

### 1. Infraestructura (Terraform)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edita terraform.tfvars con tus valores
terraform init
terraform plan
terraform apply
```

Esto crea: S3 bucket (cifrado, versionado), IAM roles, Glue job, grupo de logs CloudWatch.

### 2. Subir datos al bucket S3

```bash
aws s3 cp datos/ s3://TU_BUCKET/raw/ --recursive
```

### 3. Subir el script de Glue

```bash
aws s3 cp backend/glue_job.py s3://TU_BUCKET/scripts/glue_job.py
```

### 4. Desplegar backend en EC2

```bash
# En la instancia EC2 (Amazon Linux 2 / Ubuntu)
git clone <repo>
cd Licitacion/backend
pip install -r requirements.txt
cp .env.example .env && nano .env   # completar variables
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. Build y despliegue del frontend

```bash
cd frontend
VITE_API_URL=http://IP_EC2:8000 npm run build
# Copiar dist/ al directorio static/ del backend, o subir a S3
aws s3 sync dist/ s3://TU_BUCKET/frontend/ --delete
```

## Autenticación

Todos los endpoints `/api/*` requieren el header:

```
X-API-Key: tu-clave-secreta
```

Configura la misma clave en `backend/.env` (`API_KEY`) y en `frontend/.env.local` (`VITE_API_KEY`).

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/process` | Dispara clasificación (Glue o local) |
| `GET` | `/api/process/status` | Estado en tiempo real del job |
| `GET` | `/api/stats` | Estadísticas pre-agregadas del dashboard |
| `GET` | `/api/solicitudes` | Registros paginados con filtros |
| `GET` | `/api/export` | Descarga CSV de resultados |
| `POST` | `/api/classify` | Clasificación individual ML (fuzzy matching) |
| `GET` | `/api/quality` | Métricas de calidad del modelo ML |
| `GET` | `/api/glue/status` | Verifica disponibilidad del job Glue |
| `GET` | `/health` | Health check del sistema |

## Lógica de clasificación

```
¿ServicioSolicitado ∈ catálogo de servicios cubiertos?
├─ NO   → cubre=false, porcentaje=0%, valor_cubierto=$0
└─ SÍ   → leer PerfilCobertura (COIL_catalogo_perfiles_cobertura.csv):
          ├─ PRIORITARIO  → 100% cobertura
          ├─ ESTANDAR     → 50% cobertura
          └─ COPAGO       → 25% cobertura
          → valor_cubierto = valor_procedimiento × porcentaje / 100

Fuzzy matching ML (/api/classify):
  → TF-IDF char_wb ngrams 2–4 + cosine similarity
  → umbral: sim ≥ 0.72 → fuzzy_ml | exacto | sin_match
  → retorna: servicio_canonico, confianza, metodo
```

## Escalabilidad y costos

| Volumen diario | Workers Glue | Tiempo | Costo/ejecución |
|----------------|-------------|--------|-----------------|
| 1.2M           | 2 DPU       | ~8 min | $0.073          |
| 5M             | 4 DPU       | ~10 min| $0.15           |
| 12M            | 8 DPU       | ~12 min| $0.29           |
| 50M            | 20 DPU      | ~18 min| $0.73           |

**Costo mensual estimado:** ~$9.62 USD (S3 + Glue + EC2 t3.micro + CloudWatch)

## Seguridad y compliance

- **Cifrado en reposo:** S3 con SSE-AES256 (configurado via Terraform)
- **Autenticación:** API Key en header `X-API-Key`
- **CORS:** Restringido al dominio del frontend
- **Trazabilidad:** S3 Versioning + CloudWatch Logs para auditoría completa de decisiones
- **Sin PII en logs:** Los logs de CloudWatch no incluyen datos de pacientes

## Estructura del proyecto

```
Licitacion/
├── backend/
│   ├── main.py              # FastAPI REST API
│   ├── clasificador.py      # Motor de clasificación
│   ├── glue_job.py          # PySpark job para AWS Glue
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── tests/
│       └── test_clasificador.py
├── frontend/
│   ├── src/
│   │   ├── pages/           # DashboardPage, SolicitudesPage
│   │   ├── components/      # Charts, StatsCard, ProcessPanel, Layout
│   │   └── api/client.js    # API wrapper
│   ├── package.json
│   └── vite.config.js
├── terraform/
│   ├── main.tf              # S3, IAM, Glue, CloudWatch
│   ├── variables.tf
│   └── terraform.tfvars.example
├── datos/
│   ├── COIL_dataset_glosas_salud_1_2M.csv
│   ├── COIL_catalogo_servicios_cubiertos.csv
│   ├── COIL_catalogo_perfiles_cobertura.csv
│   └── COIL_diccionario_datos.md
├── doc/
│   ├── 01_Propuesta_Metodologica.md
│   ├── 02_Diseno_Tecnico.md
│   └── 03_Presentacion_Ejecutiva.md
├── docker-compose.yml
└── README.md
```
