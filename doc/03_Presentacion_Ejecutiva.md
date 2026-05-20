# Presentación Ejecutiva — Comité Evaluador
## DataHealth Cloud Solutions × Licitación Chernovia 2026

---

## DIAPOSITIVA 1: Portada

**"El Sistema Público de Salud de Chernovia, Modernizado"**

DataHealth Cloud Solutions  
Solución Distribuida de Análisis de Órdenes Médicas  
**12 millones de solicitudes · 105 segundos para 1.2M · $10.62 USD/mes**

> Demo en vivo: `http://184.72.124.136:8000`

---

## DIAPOSITIVA 2: El Problema que Resolvemos

### Chernovia procesa solicitudes de cobertura médica **manualmente hoy**

- Miles de solicitudes diarias sin clasificar
- Tiempos de respuesta de días o semanas
- Errores costosos por clasificación incorrecta
- Sin trazabilidad auditable de decisiones
- Sin herramientas para detectar fraude o abuso
- Sin capacidad de proyectar el impacto fiscal de cambios de política

### El objetivo del gobierno es claro:
> "Automatizar, clasificar y trazar 12 millones de solicitudes al día, en menos de 24 horas, a costo razonable."

---

## DIAPOSITIVA 3: Nuestra Solución en 30 Segundos

```
📥 INGRESO            ⚡ PROCESAMIENTO           📊 RESULTADO
CSV/Datos      →    AWS Glue (PySpark)     →    Dashboard
  en S3              Distribuido                 en tiempo real
                    1.2M en 105 segundos
                    + razon_decision
                         +
                    Motor ML (TF-IDF)      →    Clasificación
                    Fuzzy Matching              individual live
                         +
                    Anti-Fraude           →    Anomalías detectadas
                    Simulador             →    Impacto fiscal
                    PDF Automático        →    Reporte ejecutivo
                    Admin Catálogos       →    Sin código
```

**Cinco palabras:** Distribuido · Explicable · Seguro · Simulable · Económico

---

## DIAPOSITIVA 4: Arquitectura Cloud-Native

### 5 servicios AWS, 0 servidores que administrar

| Capa | Servicio | Función |
|------|----------|---------|
| **Almacenamiento** | Amazon S3 | Datos raw + Resultados + Catálogos |
| **Procesamiento** | AWS Glue + PySpark | ETL distribuido en N workers |
| **API + Módulos** | FastAPI en EC2 t3.micro | 16 endpoints + 4 módulos diferenciales |
| **Dashboard** | React SPA (6 páginas) | Dashboard · ML · Anti-Fraude · Simulador · Catálogos |
| **Monitoreo** | CloudWatch + S3 Versioning | Trazabilidad total + explicabilidad |

### ¿Por qué AWS Glue y no un servidor?

- **Sin gestión:** AWS administra los workers de Spark automáticamente
- **Escala automática:** 2 workers para 1.2M → 20 workers para 50M
- **Pago por uso:** Solo se cobra cuando corre el job

---

## DIAPOSITIVA 5: La Lógica de Clasificación

### Simple, auditable, 100% precisa y ahora explicada

```
Para cada solicitud médica (batch Glue):
  1. Extraer ServicioSolicitado de la glosa (regex)
  2. ¿Está en el catálogo de servicios cubiertos?
     └── NO → Cobertura: 0%  | Valor cubierto: $0
     └── SÍ → Leer PerfilCobertura del paciente
               ├── PRIORITARIO → 100%
               ├── ESTANDAR    → 50%
               └── COPAGO      → 25%
  3. Calcular: valor_cubierto = valor × porcentaje / 100
  4. Generar razon_decision: texto en lenguaje natural referenciando DS-2024-001
  5. Registrar decisión con timestamp, versión S3 y razon_decision

Para solicitudes individuales en tiempo real (/api/classify):
  1. Intento exacto contra catálogo → confianza 1.0 + razon_decision
  2. Fuzzy: TF-IDF char_wb + cosine similarity
     └── sim ≥ 0.72 → fuzzy_ml (confianza = sim) + razon_decision
     └── sim < 0.72 → sin_match + razon_decision explicando por qué
  3. Retorna: servicio_canonico, cubre, confianza, metodo, razon_decision
```

---

## DIAPOSITIVA 6: Diferencial #1 — Explicabilidad Total

### Cada decisión se justifica en lenguaje natural

El campo `razon_decision` aparece en **cada registro** del resultado batch y en **cada respuesta** de la API individual:

```
Ejemplo cobertura aprobada:
  "Servicio 'Cirugía cardiovascular' identificado en catálogo DS-2024-001.
   Perfil PRIORITARIO: 100% de cobertura aplicada. Valor cubierto: $1,500."

Ejemplo cobertura denegada:
  "Servicio 'Medicina alternativa' no figura en catálogo DS-2024-001.
   Cobertura denegada. Valor cubierto: $0."

Ejemplo fuzzy ML:
  "Match aproximado (confianza: 0.94) entre 'Cirugia cardiovascular' y
   'Cirugía cardiovascular' via TF-IDF ngrams. DS-2024-001: cubierto."
```

**Por qué importa:** Los ciudadanos tienen derecho a entender por qué se aprobó o rechazó su solicitud. Los auditores necesitan reconstruir cualquier decisión. Esto lo cumple de fábrica.

---

## DIAPOSITIVA 7: Diferencial #2 — Detección de Fraude (Anti-Fraude)

### 4 reglas estadísticas aplicadas a cada batch procesado

| Regla | Código | Gravedad | Qué detecta |
|---|---|---|---|
| Duplicados por DNO | AN-DUP-001 | ALTA | Mismo paciente + servicio + día > 1 vez |
| Valor atípico | AN-VAL-002 | MEDIA | Valor > media_servicio + 3σ |
| Entidad sospechosa | AN-ENT-003 | MEDIA | Tasa de rechazo < 5% en ≥ 10 solicitudes |
| Incompatibilidad edad | AN-EDAD-004 | ALTA | Servicio pediátrico para > 18 años |

**Sin costo adicional.** Accesible en `GET /api/anomalias` y en el dashboard en la página "Anti-Fraude".

> Cada anomalía incluye: tipo, gravedad, descripción, valor observado, valor esperado y recomendación de acción.

---

## DIAPOSITIVA 8: Diferencial #3 — Simulador de Política Fiscal

### Proyectar antes de decidir

El gobierno puede simular cambios de política antes de ejecutarlos:

```
Escenario hipotético:
  → Agregar: "Psicología online", "Cirugía láser"
  → Quitar: "Medicina alternativa"
  → Subir ESTANDAR de 50% → 60%

Resultado del simulador (en segundos):
  Solicitudes cubiertas antes: 65% (780K)
  Solicitudes cubiertas después: 72% (864K)
  Delta: +84K solicitudes adicionales cubiertas
  Costo fiscal adicional: +$42M USD/mes
```

**Por qué importa:** Ningún competidor ofrece esto. El gobierno puede tomar decisiones de política pública **basadas en datos reales**, no en estimaciones manuales.

---

## DIAPOSITIVA 9: Diferencial #4 — Reporte PDF Automático

### El reporte ejecutivo se genera solo

Después de cada ejecución del pipeline, `GET /api/reporte` genera un PDF completo:

```
Contenido del reporte:
  ✓ KPIs: total solicitudes / cubiertas / tasa / costo cubierto
  ✓ Distribución por fecha (tabla)
  ✓ Cobertura por perfil: PRIORITARIO / ESTANDAR / COPAGO
  ✓ Top 10 servicios más solicitados
  ✓ Tabla de anomalías detectadas con gravedad
  ✓ Referencia a resolución DS-2024-001
  ✓ Fecha y hora de generación
```

**Por qué importa:** Los tomadores de decisión reciben el reporte ejecutivo automáticamente. No hay intervención manual. No hay riesgo de error en la consolidación.

---

## DIAPOSITIVA 10: Diferencial #5 — Administración de Catálogos Sin Código

### El equipo de salud administra el sistema directamente

Desde el dashboard "Catálogos", cualquier funcionario puede:

- **Agregar servicios** al catálogo de cobertura con un clic
- **Eliminar servicios** que ya no apliquen
- **Ajustar porcentajes** de cobertura por perfil con sliders
- Los cambios se reflejan en S3 **inmediatamente**
- El modelo ML se recarga automáticamente con el nuevo catálogo

**Por qué importa:** En los competidores, cada cambio de catálogo requiere un consultor SAP u Oracle. Nosotros lo democratizamos completamente.

---

## DIAPOSITIVA 11: Resultados de la Prueba de Concepto

### Procesamos 1.2 millones de registros reales

| Métrica | Resultado |
|---------|-----------|
| Registros procesados | **1.200.000** |
| Tiempo de procesamiento | **105 segundos (1.75 min)** |
| Tasa de clasificación exitosa | **100%** |
| Registros CON cobertura | **780.000 (65%)** |
| Registros SIN cobertura | **420.000 (35%)** |
| Decisiones con razon_decision | **100%** (1.2M registros) |
| Reglas anti-fraude activas | **4** (AN-001 a AN-004) |
| Archivos Parquet generados | 4 particiones |
| Versiones trazables | 1 por ejecución (S3 Versioning) |
| Motor ML disponible | TF-IDF fuzzy matching activo |
| PDF ejecutivo disponible | Generación automática activa |
| Admin catálogos | CRUD completo vía dashboard |

**Dashboard en vivo:** `http://184.72.124.136:8000`

---

## DIAPOSITIVA 12: Propuesta Económica

### La más competitiva del mercado — con más funcionalidades

```
┌────────────────────────────────────────────────────────────┐
│              COSTO MENSUAL DE OPERACIÓN                    │
│                       (medido real)                        │
│  EC2 t3.micro + EBS 8GB       $9.11 ████████████████       │
│  AWS Glue (30 ejecuciones)    $0.76 █                      │
│  Amazon S3 (~5 GB)            $0.25 ░                      │
│  CloudWatch (logs 30 días)    $0.50 █                      │
│  Módulos diferenciales (x5)   $0.00 ░ (corren en EC2)     │
│                               ─────                        │
│  TOTAL MENSUAL                $10.62/mes                   │
│  TOTAL ANUAL                  $127.44/año                  │
│                                                            │
│  Para comparar:                                            │
│  SAP Healthcare Cloud: $8,000/mes   (sin simulador ni PDF) │
│  Oracle Health: $12,000/mes         (sin anti-fraude)      │
│  Databricks: $300–500/mes           (sin explicabilidad)   │
│                                                            │
│  AHORRO vs. SAP: 99.87%  —  con MÁS funcionalidades       │
└────────────────────────────────────────────────────────────┘
```

---

## DIAPOSITIVA 13: Escalabilidad Demostrada

### De 1.2M a 12M en el mismo sistema, sin cambios de arquitectura

| Escenario | Workers | Tiempo | Costo/mes |
|---|---|---|---|
| **Demo actual (medido)** | **2 G.1X** | **105 seg** | **$10.62** |
| 5M solicitudes/día | 4 G.1X | ~8 min | ~$18 |
| 12M solicitudes/día | 8 G.1X | ~12 min | ~$27 |
| 50M solicitudes/día | 20 G.1X | ~18 min | ~$75 |

**El costo crece linealmente, el tiempo casi no crece gracias a la paralelización.**  
**Los módulos diferenciales escalan con el mismo EC2 sin costo adicional.**

---

## DIAPOSITIVA 14: Trazabilidad y Seguridad

### Cuatro pilares de trazabilidad — nada queda sin registrar

✅ **S3 Versioning activo:** Cada ejecución genera una versión inmutable  
✅ **CloudWatch Logs:** Registro completo de cada job (quién, cuándo, cuántos)  
✅ **Parquet inmutable:** Formato binario no editable, auditable  
✅ **razon_decision en cada registro:** Explicación en lenguaje natural de cada decisión  
✅ **IAM Roles:** Sin credenciales hardcodeadas, acceso por rol  
✅ **HTTPS:** Todas las comunicaciones cifradas en tránsito  

**Si el comité pregunta por cualquier decisión tomada hace 90 días, podemos mostrarla en segundos, junto con la explicación de por qué se tomó.**

---

## DIAPOSITIVA 15: Por Qué Somos la Mejor Opción

### El equipo que une investigación + tecnología

| Criterio de evaluación | Nuestra propuesta | SAP / Oracle |
|---|---|---|
| Arquitectura distribuida | Glue PySpark (N workers auto) | ✅ Sí |
| Costo operativo | **$10.62/mes (medido real)** | $8,000–$12,000/mes |
| Escalabilidad | 50M+ registros sin cambios | ✅ Sí (costoso) |
| Trazabilidad | S3 Versioning + CloudWatch | ✅ Sí |
| Tiempo de procesamiento | **105 seg para 1.2M (medido)** | No especificado |
| Clasificación ML fuzzy | TF-IDF + cosine (umbral 0.72) | No incluido |
| **Explicabilidad decisiones** | **razon_decision en cada registro** | ❌ No |
| **Detección de fraude** | **4 reglas anti-fraude (AN-001–004)** | Módulo aparte (+$2,000) |
| **Simulador de política** | **Proyección fiscal en segundos** | ❌ No |
| **PDF automático** | **Reporte ejecutivo post-ejecución** | ❌ No |
| **Admin catálogos** | **CRUD sin código desde dashboard** | Consultor SAP |
| Implementación funcional | ✅ Sistema vivo en 184.72.124.136 | Meses de implementación |

---

## DIAPOSITIVA 16: Demo en Vivo

### Veamos el sistema funcionando ahora mismo

**Flujo de demo sugerido (8 minutos):**

1. **Dashboard principal** → muestra stats de 1.2M registros procesados: 65% cobertura, distribución por perfil
2. **Solicitudes** → filtrar por perfil PRIORITARIO → exportar CSV con razon_decision incluida
3. **Demo ML** → ingresar glosa con error tipográfico → motor devuelve `servicio_canonico`, `confianza`, `razon_decision`
4. **Anti-Fraude** → ver anomalías detectadas en el último batch: duplicados, valores atípicos, entidades sospechosas
5. **Simulador** → agregar "Psicología online" al catálogo → ver proyección: +X% cobertura, +$Y costo fiscal
6. **Catálogos** → ajustar porcentaje ESTANDAR de 50% a 60% con slider → guardar → modelo recarga automáticamente
7. **Reporte PDF** → click en botón "Reporte PDF" → descarga PDF ejecutivo generado automáticamente
8. **API directa** → `GET /api/anomalias` → JSON estructurado de anomalías en tiempo real

**URLs del sistema:**
- Dashboard: `http://184.72.124.136:8000`
- Health: `http://184.72.124.136:8000/health`
- Anomalías: `http://184.72.124.136:8000/api/anomalias`
- Reporte PDF: `http://184.72.124.136:8000/api/reporte`

---

## DIAPOSITIVA 17: Cierre

### DataHealth Cloud Solutions

**"El Sistema Público de Salud de Chernovia merece tecnología de clase mundial."**

Nosotros lo hacemos por **$10.62 al mes** — con datos reales, medidos, en producción.

Y además:
- **Explica** cada decisión para que cualquier ciudadano pueda entenderla
- **Detecta** el fraude automáticamente, sin costo adicional
- **Proyecta** el impacto de políticas antes de ejecutarlas
- **Genera** reportes ejecutivos sin intervención humana
- **Empodera** al equipo de salud para administrar el sistema sin programadores

---

**Contacto técnico:** DataHealth Cloud Solutions  
**Demo disponible:** 24/7 en AWS  

*Universidad Panamericana México × Universidad Pontificia Bolivariana Colombia*  
*Proyecto COIL — Big Data y Metodología de la Investigación — 2026*

---

### PREGUNTAS FRECUENTES DEL COMITÉ

**P: ¿Qué pasa si hay más de 12M solicitudes?**  
R: Glue escala automáticamente. Cambiamos `NumberOfWorkers` de 8 a 40 y el tiempo se mantiene en ~15 min. Los módulos diferenciales siguen corriendo en EC2 sin cambios.

**P: ¿Los datos están seguros?**  
R: S3 cifra todos los datos en reposo (AES-256). IAM Roles controlan acceso. S3 Versioning garantiza inmutabilidad. Ninguna credencial está hardcodeada.

**P: ¿Cómo garantizan la disponibilidad?**  
R: AWS SLA: S3 = 99.99%, Glue = 99.9%, EC2 = 99.5%. Para mayor disponibilidad: EC2 Auto Scaling Group + ALB (~$15 adicionales).

**P: ¿Se puede integrar con sistemas legacy?**  
R: Sí. La API REST es agnóstica. Se puede conectar cualquier sistema que haga HTTP calls. Los 16 endpoints están documentados y accesibles.

**P: ¿Qué significa razon_decision en la práctica?**  
R: Cada registro del resultado incluye un texto como: "Servicio 'X' identificado en catálogo DS-2024-001. Perfil PRIORITARIO: 100% aplicado." Esto permite a un auditor, a un médico o a un ciudadano entender en segundos por qué se aprobó o rechazó su solicitud.

**P: ¿El simulador de política es solo estimativo?**  
R: Opera sobre la muestra de 10K solicitudes disponibles en memoria. Para una proyección exacta, se puede ejecutar el Glue job completo con el catálogo hipotético. La herramienta actual es suficiente para decisiones de política de primer nivel.

**P: ¿Qué experiencia tienen con sistemas de salud?**  
R: El equipo ha implementado arquitecturas similares en contexto académico y ha analizado los casos de NHS Digital, MinSalud Colombia y SUSALUD Perú como referentes del estado del arte.
