# GeoOpportunity AI — Fase 2A territorial (GeoML separado)

Base reproducible para **dos dominios separados**: GeoOpportunity procesa datos territoriales públicos de Valparaíso y Viña del Mar; GeoML se reserva para un futuro modelo de ventas basado en datos históricos comerciales independientes. **No hay datasets, entrenamiento ni predicciones incluidos.** GeoML no predice ventas de cafeterías chilenas.

## Ejecutar en Windows con Docker Desktop

1. Instalá Docker Desktop con WSL 2, iniciá el motor y abrí PowerShell en la raíz del proyecto.
2. Ejecutá `docker compose up --build -d` (la primera descarga/construcción necesita conexión a Internet).
3. Consultá `http://localhost:8000/health` (esperado: `{"status":"ok"}`), `http://localhost:8000/model/info` (estado `not_trained`) y `http://localhost:8501` (panel de estado).
4. Detené los servicios con `docker compose down`.

La documentación interactiva de FastAPI está en `http://localhost:8000/docs`. Si los puertos 8000/8501 están ocupados, liberá esos puertos antes de iniciar Compose. El panel muestra mapas territoriales sólo cuando se procesaron fuentes verificadas. Sin datos presenta un estado vacío.

## Datos opcionales, nunca precargados

Ubicá **tus propios archivos autorizados** en `data/raw/`. Para una fuente comercial se admiten CSV o Parquet tabulares; para una territorial, GeoJSON o GeoParquet. Los formatos y esquemas de producción todavía no están definidos; ingresar datos no los valida como aptos para entrenar. El pipeline escribe `data/processed/commercial.parquet` o `data/processed/territorial.parquet` y **rechaza sobrescribirlos**. Estos archivos se ignoran en Git y ambos dominios nunca se unen.

En PowerShell, por ejemplo, para ingerir un CSV comercial que efectivamente exista:

```powershell
$env:GEOAI_COMMERCIAL_SOURCE = '/app/data/raw/mi-historico.csv'
docker compose run --rm -e GEOAI_COMMERCIAL_SOURCE=$env:GEOAI_COMMERCIAL_SOURCE api python -m geoopportunity.data.pipeline --domain commercial
```

Para un GeoJSON territorial usá `GEOAI_TERRITORIAL_SOURCE=/app/data/raw/mi-territorio.geojson` y `--domain territorial` en el mismo comando. Si el archivo no existe, la fuente no está configurada, el formato no es admitido o la salida ya existe, el comando termina con error y no inventa datos. Para volver a generar una salida, retirala manualmente después de revisar su contenido; el pipeline no la reemplaza por sí solo. Para cambiar el nivel de logs de la API, definí `GEOAI_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`) antes de `docker compose up`.

## Desarrollo y pruebas

Requiere Python 3.11+. En PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m pytest -q
```

El entorno de pruebas utiliza archivos aislados en directorios temporales; no es un dataset de entrenamiento ni produce predicciones. El contenedor instala además scikit-learn, XGBoost, GeoPandas, DuckDB, PyDeck y las demás dependencias declaradas en `pyproject.toml`. Las versiones están acotadas por intervalos compatibles, no fijadas a un lockfile: para reproducibilidad binaria completa, queda pendiente fijar hashes/imagen base al avanzar a despliegue.

## Mapa de responsabilidades

| Ruta | Responsabilidad actual |
| --- | --- |
| `src/geoopportunity/data/` | CLI de ingestión general y CLI territorial OSM/INE con GeoParquet |
| `src/geoopportunity/features/` | Reservado para features, sin transformaciones todavía |
| `src/geoopportunity/training/` | Reservado; sin entrenamiento ni artefactos |
| `src/geoopportunity/evaluation/` | Reservado; sin métricas calculadas |
| `src/geoopportunity/inference/` | Contratos tipados futuros de ventas comerciales |
| `src/geoopportunity/api/` | Salud y estado real del modelo (`not_trained`) |
| `src/geoopportunity/presentation/` | Mapa territorial, indicadores y ranking heurístico sólo cuando hay datos cargados |

`SalesPredictionRequest` y `SalesPredictionResponse` son **solo contratos futuros**, no endpoints activos. El campo `domain` acepta exclusivamente `independent_commercial_sales`; la respuesta futura exige el aviso de no transferibilidad. Antes de activar inferencia habrá que elegir un dataset comercial con licencia, definir variables y objetivo, separar entrenamiento/validación temporal y registrar un modelo real. El análisis territorial requiere fuentes públicas verificadas, metadatos de licencias, CRS y cobertura; no se infiere demanda ni ventas a partir de ubicaciones.

## Análisis territorial: fuentes, ejecución y límites

**Fuentes verificables.** El INE publicó el 16-12-2025 la base manzana–entidad del Censo 2024 (189 variables), cartografía y diccionario: [publicación oficial](https://censo2024.ine.gob.cl/ine-publica-bases-de-datos-a-nivel-de-manzana-y-cartografia-del-censo-de-poblacion-y-vivienda-2024/). Descargá manualmente cartografía, base y diccionario desde los portales oficiales vinculados allí; contrastá en el diccionario las columnas de identificador geográfico y población residente **antes** de usarlas. La publicación informativa no especifica nombres exactos ni garantiza la correspondencia de archivos concretos: no se declara verificada una unión INE hasta validar la edición local. Prepará un GeoParquet de **manzanas de las dos comunas** con columnas `zone_id` (identificador oficial, texto para conservar ceros iniciales), `comuna` (`Valparaíso` o `Viña del Mar`) y polígonos con CRS; no sustituyas la cartografía por polígonos inventados. Asegurate de que los ID de la tabla correspondan exactamente a esos ID oficiales. La ingesta falla si hay IDs duplicados, geometrías inválidas o CRS ausente; sin coincidencias la población queda ausente, nunca se imputa. Valores reservados/no numéricos también quedan ausentes, conservando `population_raw` y marcando `non_numeric_or_protected` sin atribuirles una causa definitiva; IDs sin unión se marcan `unmatched_id`, nulos `missing`. Conservá los archivos originales y su licencia para auditoría. No se distribuyen aquí datos del INE.

OSM se consulta mediante Overpass por `amenity=cafe` en cajas que abarcan las manzanas de cada comuna más 1 km para reducir sesgo de borde. Sólo se desduplican elementos con el **mismo tipo e ID OSM**; diferentes ID cercanos no se fusionan sin evidencia. Los polígonos se representan por un punto interior para distancias y conservan su geometría original en `source_geometry_wkt`. El caché almacena respuestas originales con una clave derivada de la consulta; no descarga en modo `--offline`. Los datos OSM pueden ser incompletos o desactualizados; se requiere [© OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright). Respetá límites de Overpass: ejecuciones manuales, dos consultas acotadas, pausa entre consultas y reintentos limitados; no programes sondeos frecuentes. Las teselas del mapa se sirven conforme a la política de su proveedor.

Después de validar archivos locales, ejecutá (PowerShell; rutas dentro del volumen `data/`):

```powershell
docker compose run --rm api python -m geoopportunity.data.territorial --zones /app/data/raw/manzanas-ine.geoparquet --census /app/data/raw/tabla-ine.csv --id-column ID_VERIFICADO --population-column POBLACION_VERIFICADA
# Si no hay estadísticas verificadas, omití --census y las dos opciones de columna.
# Para reusar respuestas OSM sin red, agregá --offline una vez poblado data/raw/osm-cache/.
```

El proceso crea `data/processed/zones.geoparquet`, `cafes.geoparquet` y `quality.json` con conteos, faltantes, fuente y fecha de extracción. No sobrescribe salidas existentes: para una nueva edición respaldá y retirá manualmente las tres salidas anteriores. Compose monta `data/` en la UI en modo lectura; refrescá la página tras procesar. **No se suministran datos reales en este repositorio**: no puede asegurarse cobertura ni validación de un archivo específico sin descargarlo. Distancias, áreas y buffers usan UTM 19S (`EPSG:32719`), no grados; cada radio se mide desde un punto interior de la manzana y el conteo de zona incluye puntos sobre límites (un café limítrofe podría contarse en ambas zonas). La cafetería más cercana puede estar fuera de la comuna; el búfer de consulta de 1 km limita la inferencia en los bordes. Sin puntos OSM la distancia más cercana es nula; el número cero refleja sólo OSM disponible. La población residente no es demanda comercial, especialmente en zonas turísticas. Sin POI verificados no se calcula distancia a POI. El ranking min–max es heurístico, sensible a pesos y cobertura: **no predice ventas ni acredita una oportunidad de negocio**.

## AWS (diseño futuro; nada aprovisionado)

Cuando existan fuentes autorizadas y requisitos de operación: contenedores de FastAPI/Streamlit en ECS Fargate detrás de un Application Load Balancer; artefactos/datos separados por dominio en S3, cifrados y con políticas IAM mínimas; imágenes en ECR; logs JSON en CloudWatch. Un trabajo batch independiente podría ejecutar ingestión/entrenamiento con validación, versionado de datos/modelo y promoción manual. Antes de implementarlo hay que acordar región, seguridad, presupuesto, volumen, modelo de datos, licencias y criterios de monitoreo. No hay Terraform, cuentas, buckets ni despliegue AWS en esta fase.
