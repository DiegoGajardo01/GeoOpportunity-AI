# GeoOpportunity AI — first phase
Status: implemented; local tests and Docker endpoints verified. No source datasets or trained model are assumed.
Scope: repository skeleton, contracts, reproducible local execution and verification.

## Specs
S1. "Crear una arquitectura modular con separación entre datos, features, entrenamiento, evaluación, inferencia y presentación."
S2. "Implementar Docker Compose con servicios independientes para FastAPI y Streamlit."
S3. "Crear endpoints `/health` y `/model/info`."
S4. "Preparar un pipeline de datos configurable, sin asumir que los datasets ya existen."
S5. "Definir contratos Pydantic para las futuras solicitudes y respuestas de inferencia."
S6. "Incorporar logging estructurado, configuración mediante variables de entorno y manejo explícito de errores."
S7. "Agregar pruebas unitarias para los componentes implementados."
S8. "Crear un README con instrucciones para ejecutar el proyecto en Windows mediante Docker Desktop."
S9. "Documentar una arquitectura futura de despliegue en AWS, sin implementarla todavía."
S10. "Los resultados de GeoML NO deben presentarse como predicciones válidas para cafeterías chilenas, porque ambos módulos utilizan dominios de datos distintos."
S11. "No inventar datasets, resultados ni métricas." "No generar predicciones ficticias." "No entrenar modelos con etiquetas sintéticas para presentarlos como resultados reales." "No confundir análisis territorial con predicción de ventas." "No implementar agentes, RAG ni funcionalidades ajenas al MVP." "No crear infraestructura innecesaria." "No introducir complejidad sin justificación."

## Tasks
T1 [S1,S3,S5,S6,S7,S10,S11] API and contracts with tests; route: inline; tests 4/4; commit: not authorized.
T2 [S1,S4,S6,S7,S10,S11] Configurable ingestion with tests; route: inline; tests 6/6; commit: not authorized.
T3 [S2,S8,S9,S7,S10,S11] Compose, README and AWS design, verify; route: inline; Compose config verified, API healthy, endpoints verified, Streamlit HTTP 200; commit: not authorized.

## Log
L1 (user request, verbatim):
Actúa como Senior Data Scientist, ML Engineer y Software Architect.

Vamos a desarrollar **GeoOpportunity AI**, un proyecto de portafolio profesional que demuestra capacidades de Data Science, Machine Learning, ingeniería de datos geoespaciales y MLOps.

**Contexto**

El proyecto tendrá dos módulos:

1. **GeoOpportunity:** análisis de oportunidades de expansión para cafeterías en Valparaíso y Viña del Mar, Chile, utilizando datos geoespaciales públicos.
2. **GeoML:** motor de predicción de ventas entrenado con datos históricos reales de un dataset comercial independiente.

Los resultados de GeoML NO deben presentarse como predicciones válidas para cafeterías chilenas, porque ambos módulos utilizan dominios de datos distintos.

**Stack**

- Python 3.11+
- pandas, NumPy, GeoPandas
- DuckDB y Parquet
- scikit-learn y XGBoost
- FastAPI y Pydantic
- Streamlit y PyDeck
- Docker y Docker Compose
- pytest

**Objetivo de esta primera fase**

Construir la estructura inicial del repositorio, las configuraciones, los contratos entre módulos y un entorno reproducible.

**Requisitos**

1. Crear una arquitectura modular con separación entre datos, features, entrenamiento, evaluación, inferencia y presentación.
2. Implementar Docker Compose con servicios independientes para FastAPI y Streamlit.
3. Crear endpoints `/health` y `/model/info`.
4. Preparar un pipeline de datos configurable, sin asumir que los datasets ya existen.
5. Definir contratos Pydantic para las futuras solicitudes y respuestas de inferencia.
6. Incorporar logging estructurado, configuración mediante variables de entorno y manejo explícito de errores.
7. Agregar pruebas unitarias para los componentes implementados.
8. Crear un README con instrucciones para ejecutar el proyecto en Windows mediante Docker Desktop.
9. Documentar una arquitectura futura de despliegue en AWS, sin implementarla todavía.

**Restricciones**

- No inventar datasets, resultados ni métricas.
- No generar predicciones ficticias.
- No entrenar modelos con etiquetas sintéticas para presentarlos como resultados reales.
- No confundir análisis territorial con predicción de ventas.
- No implementar agentes, RAG ni funcionalidades ajenas al MVP.
- No crear infraestructura innecesaria.
- No introducir complejidad sin justificación.

**Forma de trabajo**

Primero inspecciona el repositorio y presenta un plan breve con estructura, dependencias, riesgos y criterios de aceptación.

Después implementa la primera fase y ejecuta las pruebas disponibles.

Al finalizar, informa qué funciona, qué queda pendiente y cómo ejecutar el proyecto localmente.

No declares completada ninguna funcionalidad que no hayas verificado.

L2 (verification): `.venv/Scripts/python -m pytest -q` passed 10/10 (one external Starlette deprecation warning); `docker compose config --quiet` passed. Docker Desktop subsequently started; `docker compose ps` showed API healthy and UI up, `/health` returned `{"status":"ok"}`, `/model/info` returned `not_trained` with commercial-only disclaimer, and Streamlit root returned HTTP 200. This is HTTP reachability, not a visual UI inspection. Independent verifier could not launch; native RDD assessment was unassessable because untracked files require explicit declaration. No commit was authorized or created.
