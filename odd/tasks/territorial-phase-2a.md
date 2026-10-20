# GeoOpportunity AI — Phase 2A
Territorial MVP; do not change GeoML contracts. Data must be real, traceable, reproducible.

## Specs
S1. "Filtrar `amenity=cafe`." Preserve OSM ID, name, geometry, tags; bounded Valparaíso/Viña del Mar queries, cache, cautious retries, attribution.
S2. "Preparar un adaptador para incorporar datos censales a nivel de manzana." Validate official IDs and dictionary, preserve suppressed/missing values, allow manual local files.
S3. "Usar CRS proyectado adecuado para mediciones métricas. No calcular distancias en grados." Compute territorial coverage, nearest cafe, 300/500/1.000m radii and resident indicators when available.
S4. "Implementar un ranking exploratorio y transparente." Configurable normalized weights, contributions, missing data and sensitivity; never sales prediction.
S5. "Si faltan fuentes, mostrar estados de ausencia de datos. No utilizar valores ficticios como resultados reales." Interactive map, provenance, limitations.
S6. "Docker Compose sigue levantando API y dashboard." Existing and new tests pass; report actual verification.

## Tasks
T1 S1-S2: ingest official/local inputs and document sources; route inline; commit pending.
T2 S3-S4: territorial indicators and ranking with tests; route inline; commit pending.
T3 S5-S6: dashboard, docs and checks; route inline; commit pending.

## Log
L1: User requests GeoOpportunity AI Phase 2A territorial intelligence for cafes in Valparaíso and Viña del Mar with real traceable reproducible OSM and INE Censo 2024 sources, metric features, transparent exploratory ranking, Streamlit map, quality report, offline tests, Docker and README; no GeoML modifications, cloud, RAG, agents, fabricated data or sales forecasts. Full verbatim original request is present in the conversation.
L2: INE publication https://censo2024.ine.gob.cl/ine-publica-bases-de-datos-a-nivel-de-manzana-y-cartografia-del-censo-de-poblacion-y-vivienda-2024/ confirms 189 variables, cartography and dictionary, but does not specify the variable names/join key on that page; require user-supplied verified mapping.
L3: Local suite 17 passed, 1 preexisting Starlette warning; Docker Compose rebuilt, API /health healthy, UI HTTP 200, territorial module import confirmed. No official INE or live OSM dataset loaded; no actual map rendering/data quality verified. Independent verifier failed to start (not retried). Native RDD assess returned unassessable due all project files untracked/no initial commit. T1 and final proof blocked; no work-unit commit created because the initial project is wholly untracked and no explicit authorization was given to establish a baseline.
