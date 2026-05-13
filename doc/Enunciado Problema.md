# Enunciado Problema

## Página 1

Proyecto COIL interdisciplinario
Big Data y
Metodología de la
Investigación
Diseño e implementación de una solución distribuida 
en la nube para el procesamiento masivo de 
órdenes médicas en un sistema público de salud
Big Data Metodología de la Investigación
Reto académico para diseñar, justificar e implementar una propuesta 
competitiva ante un comité evaluador.
• Desarrollar desde Metodología de la Investigación una propuesta 
innovadora usando componentes técnicos para resolver un problema 
basado en la vida real y lograr un trabajo interdisciplinario 
• Desarrollar desde Arquitecturas de Big Data, una solución aplicada de 
los conceptos vistos en el curso
Presentación Ejecutiva

## Página 2

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Planteamiento del problema
Los estudiantes de los cursos Metodología de la Investigacióny Arquitecturas de Nube y Big Datade la UP y la UPB deberán conformar equipos mixtos e 
interdisciplinarios, integrados por participantes de ambas instituciones y países, con el fin de desarrollar un proyecto conjunto de finalización de curso en el 
marco de una experiencia COIL.
En este contexto, cada equipo asumirá el rol de una empresa de base tecnológicaque participa en una licitación internacional convocada por el Gobierno del 
país ficticio de Chernovia.. Chernovia cuenta con un sistema público de salud que administra la cobertura financiera de procedimientos y tratamientos médicos de 
sus ciudadanos. Como parte de un proceso de modernización institucional, el gobierno ha abierto una licitación para contrataruna solución tecnológica capaz de 
analizar, clasificar y procesar diariamente las solicitudes de cobertura recibidas por el sistema de salud, con el propósito de determinar cuáles deben ser cubiertas 
por el seguro público y cuáles no.
La entidad contratante espera que las empresas oferentes propongan una solución apoyada en tecnologías de la cuarta revolución industrial, particularmente en 
áreas como Big Data, analítica de datos, procesamiento distribuido, almacenamiento distribuido e inteligencia artificial, de modo que el sistema pueda 
operar con criterios de escalabilidad, eficiencia, trazabilidad y viabilidad económica.
Cada equipo deberá trabajar sobre una base de datos de ejemplo suministrada por los docentes, a partir de la cual deberá desarrollar una prueba de 
concepto funcionalque permita demostrar la capacidad de su propuesta para procesar solicitudes mediante servicios de Big Data y analítica de datos.
Además de la implementación técnica, cada equipo deberá estructurar y presentar una propuesta integral de licitación, que incluya como mínimo los siguientes 
componentes:
• Estado del artesobre soluciones tecnológicas relacionadas con el problema. 
• Análisis de soluciones similaresexistentes en el sector o en contextos comparables. 
• Propuesta de solución diseñada por el equipo, con justificación metodológica, técnica y funcional. 
• Propuesta económicapara el desarrollo de la solución, considerando criterios de costo y competitividad. 
• Presentación ejecutivade la solución ante un comité evaluador. 
El proyecto será valorado no solo por la calidad de la implementación técnica, sino también por la solidez de la investigación realizada, la claridad metodológica, la 
pertinencia de la arquitectura propuesta, la viabilidad económica y la capacidad del equipo para comunicar y defender su propuesta de manera profesional.
El equipo que presente la propuesta más sólida y equilibrada, considerando conjuntamente la calidad de la propuesta, la factibilidad económicay la 
implementación técnica de la prueba de concepto, recibirá un reconocimiento especial. 0
3

## Página 3

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Contexto del reto
Un gobierno federal desea automatizar el análisis de 
órdenes médicas para decidir cobertura pública, 
porcentaje reconocido y trazabilidad de la decisión.
Cada documento incluye fecha, glosa, medio emisor, valor del 
procedimiento y entidad emisora.
La glosa contiene identificación del paciente, edad y medicación 
asociada al tratamiento.
La solución debe clasificar si cubre o no cubre y calcular 100%, 
50% o 25% según el perfil del usuario.
El comité valorará desempeño técnico, metodología de trabajo y 
costo razonable.
12 millones
consultas objetivo
< 24 horas
ventana máxima de procesamiento
Variables críticas de evaluación
Tiempo total Costo de operación
Escalabilidad Trazabilidad
La propuesta debe comportarse como una licitación 
real: sólida técnicamente, sustentada 
metodológicamente y defendible ante un comité.
0
2

## Página 4

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Planteamiento del problema
Recepción
Ingreso del 
documento
desde el sistema 
fuente
Extracción
Lectura de glosa y
datos mínimos
Clasificación
Determinar si el
Estado cubre o no
Cobertura
Calcular 100%, 50%
o 25%
Decisión
Registrar salida
trazable
Campos mínimos del 
documento
Fecha
Glosa
Medio emisor
Valor del 
procedimiento
Entidad emisora
La glosa concentra la 
información clínica y 
administrativa clave 
para decidir la 
cobertura.
Estructura de la 
glosa
Paciente: nombre + identificador DNO + seguro social
Edad del paciente
Medicación o listado de medicamentos
Base de decisión de cobertura y reconocimiento 
económico
0
3

## Página 5

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Lo que deben lograr los estudiantes
Propósito formativo
Integrar
investigación, diseño
técnico y análisis
económico
Investigar y justificar una 
solución a la medida.
Diseñar arquitectura distribuida 
y metodología.
Defender técnicamente el 
proyecto ante un comité.
1 Presentación de proyectos
Comunicar con claridad una 
propuesta técnica y académica.
2 Estado del arte
Comparar enfoques existentes y 
detectar vacíos del mercado.
3 Diseño económico
Relacionar arquitectura, 
rendimiento y costo razonable.
4 Competencia técnica
Resolver el problema con nube, 
procesamiento y almacenamiento 
distribuido.
5 Trabajo multidisciplinario
Coordinar perfiles distintos en un 
contexto COIL e intercultural.
6 Comunicación y método
Usar metodologías de desarrollo, 
seguimiento y colaboración 
geográfica.
0
4

## Página 6

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Dos rutas de solución posibles
Opción 1
Procesamiento por lotes
Privilegia rendimiento batch para grandes 
volúmenes y ventanas definidas de ejecución.
Adecuada cuando la meta principal es el tiempo total 
de corrida.
Favorece control de costos por volumen procesado.
Exige estrategia robusta de almacenamiento y 
orquestación.
Valor 
esperadoMayor eficiencia para cargas masivas 
repetibles.
Opción 2
Ingesta continua e híbrida
Integra recepción continua, almacenamiento 
distribuido y consolidación analítica.
Aporta flexibilidad operativa y trazabilidad ampliada.
Permite combinar analítica, monitoreo y 
procesamiento diferido.
Requiere justificar con claridad el balance costo -
complejidad.
Valor 
esperado
Mayor flexibilidad para operaciones continuas y 
analítica posterior.
Ambas opciones deben demostrar escalabilidad, razonabilidad económica y coherencia metodológica.
0
5

## Página 7

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Ruta sugerida de trabajo
1
Comprensión
Delimitar 
problema, 
supuestos y 
cobertura.
2
Estado del 
arte
Revisar 
antecedentes y 
soluciones 
comparables.
3
Formulación
Objetivo, 
método y 
criterios de 
validación.
4
Diseño 
técnico
Arquitectura, 
flujo de datos y 
lógica.
5
Implementación
Prototipo 
funcional en 
AWS con 
evidencia.
6
Evaluación
Análisis 
económico, 
defensa y 
cierre.
Fase transversal: coordinación COIL, bitácora de decisiones, comunicación entre sedes y seguimiento docente por hitos.
0
6

## Página 8

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Entregables esperados
01
Documento de 
propuesta
25%
del curso
Problema, estado del arte, 
objetivos, metodología y 
análisis económico.
Formato Word editable
02
Diseño técnico
25%
del curso
Arquitectura distribuida, 
flujo de datos, lógica y 
estrategia de costo.
Diagrama + justificación
03
Implementación
25%
del curso
Prototipo funcional en 
AWS, pruebas, evidencia y 
alcance implementado.
Código y resultados
04
Presentación 
final
25%
del curso
Documento consolidado y 
defensa ejecutiva ante 
comité evaluador.
Pitch + defensa oral
Material disponible para el desarrollo: laboratorio de AWS.
0
7

## Página 9

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Esquema de evaluación y rúbrica
4 componentes · 25% cada 
uno
25%
Propuesta
metodológica
25%
Diseño
técnico
25%
Implementación
25%
Documento y
presentación
La rúbrica se alinea exactamente con los cuatro 
productos del proyecto.
Propuesta metodológica
Problema bien formulado, estado del arte pertinente, objetivos y 
metodología coherentes.
Solución técnica
Arquitectura distribuida clara, lógica de clasificación defendible y 
balance costo-rendimiento.
Implementación
Prototipo funcional, uso pertinente de AWS y evidencia de pruebas.
Documento y presentación
Calidad del informe, claridad ejecutiva y defensa convincente ante el 
comité.
0
8

## Página 10

PROYECTO COIL · BIG DATA + METODOLOGÍA DE LA INVESTIGACIÓN
Paquete docente listo para usar
Qué se entrega
Guía docente formal,
versión resumida y
presentación editable
para acompañar la
experiencia COIL.
Versión breve para inducción.
Documento marco para planeación.
Presentación editable para clase y comité.
Recurso disponible: laboratorio de 
AWS
Vista del 
material
Guía resumida
 Guía extensa
 Presentación PPTX
Listo para adaptar, presentar y lanzar en clase.
0
9

