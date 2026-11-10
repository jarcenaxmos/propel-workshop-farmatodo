# Solución de problemas

Primero ejecuta `python scripts/verificar.py`: dice cuál de las piezas falla.

La mayoría de las entradas apareció al probar los labs. Las marcadas con *(previsto)* son problemas esperables que no se reprodujeron en la prueba, así que su solución no está verificada.

## Setup y entorno

**`No hay un proyecto activo`**
Cloud Shell no define `PROJECT_ID`. Ejecuta `export PROJECT_ID=tu-proyecto` y repite `./setup.sh`.

**`Se necesita Python 3.11 o superior`** *(previsto)*
Indica otro intérprete: `PYTHON=python3.12 ./setup.sh`.

**`adk: command not found`, o `ModuleNotFoundError: No module named 'google.adk'`**
El entorno virtual no está activo en esa terminal. Ejecuta `source .venv/bin/activate` desde la raíz del repo.

**`KeyError: 'GOOGLE_CLOUD_PROJECT'` al ejecutar el agente**
Falta el archivo `.env` en la raíz del repo. Lo crea `./setup.sh`. ADK lo lee solo, buscando hacia arriba desde la carpeta del agente.

**`DefaultCredentialsError` o "Credenciales por defecto (ADC)" en FALLA** *(previsto)*
En Cloud Shell, acepta el aviso de autorización. En tu equipo, ejecuta `gcloud auth application-default login`.

**`pip` falla por certificados detrás del proxy corporativo** *(previsto)*
Configura el certificado raíz de tu empresa: `export REQUESTS_CA_BUNDLE=/ruta/ca.pem SSL_CERT_FILE=/ruta/ca.pem` y `pip config set global.cert /ruta/ca.pem`. En Cloud Shell no ocurre.

## Modelo

**`404 NOT_FOUND ... Publisher model ... gemini-2.5-flash`**
Ese modelo fue retirado. Los labs usan `gemini-3.8-flash`. Si el 404 es con un modelo 3.x, revisa que la ubicación sea `global`: en `us-east1` esos modelos no están.

**`429 RESOURCE_EXHAUSTED`** *(previsto)*
Demasiadas llamadas en poco tiempo, típico si varias personas comparten un proyecto. Espera un minuto y repite. Un proyecto por persona lo evita.

**`400 ... The input token count exceeds the maximum number of tokens allowed 1048576`**
Un `McpToolset` de Cloud Monitoring sin `tool_filter`. Las nueve herramientas del servidor traen esquemas enormes. Agrega `tool_filter=["list_timeseries", "list_alert_policies"]`.

## Servidores MCP de Google Cloud

**"MCP de Cloud Logging responde" en FALLA, con 403 o `PERMISSION_DENIED`** *(previsto)*
Tu usuario necesita `roles/mcp.toolUser` más `roles/logging.viewer` y `roles/monitoring.viewer` en el proyecto. Con `roles/owner` ya los tienes.

**`list_log_entries` devuelve `{}` o solo un `nextPageToken`**
Pasa en tres casos:
- El filtro usa el número del proyecto en `logName`. Tiene que ser el id.
- Un `pageSize` muy chico: el servidor puede devolver una página vacía con token. Usa 50.
- No hay señales recientes. Ejecuta `python scripts/sembrar_senales.py --forzar`.

**`Cannot find metric(s) that match type = "custom.googleapis.com/farmalab/error_rate"`**
La métrica es nueva o se borró hace poco. Cloud Monitoring tarda hasta 10 minutos. Espera y repite `python scripts/sembrar_senales.py`.

**El agente dice que no hay errores en la última hora**
Las señales cubren 60 minutos desde que se sembraron. Renueva el incidente con `python scripts/sembrar_senales.py --forzar`.

**"Existe la política de alertas de Farmalab" en FALLA**
La política no se pudo crear porque la métrica todavía no estaba disponible. El lab funciona sin ella. Para crearla, repite `python scripts/sembrar_senales.py` en unos minutos.

**Timeout al conectar con un servidor MCP** *(previsto)*
Detrás de un proxy que almacena en búfer las respuestas `text/event-stream`, las llamadas MCP pueden colgarse. Prueba en Cloud Shell. Si necesitas trabajar local, pide una excepción para `logging.googleapis.com` y `monitoring.googleapis.com`.

## Servidor MCP de contexto

**`ModuleNotFoundError: No module named 'mcp.server.fastmcp'`**
Con `mcp` 2.x, `FastMCP` pasó a llamarse `MCPServer` (`from mcp.server.mcpserver import MCPServer`). El repo ya usa el nombre nuevo. Si copias código de un tutorial antiguo, cámbialo.

**El agente no ve `obtener_servicio` ni `listar_despliegues`**
Prueba el servidor solo: `python sesion-4-adk-mcp/servidor_contexto/server.py`. Debe quedar esperando sin imprimir errores (Ctrl+C para salir). Si falla, falta `datos/catalogo_servicios.json` o el entorno virtual no está activo.

## Aprobación humana

**El ticket no se crea y el resultado dice `This tool call requires confirmation`**
Es el comportamiento esperado: falta la respuesta de la persona. Con `probar_agente.py` agrega `--aprobar`. En `adk web`, responde el pedido de confirmación en la interfaz.

**Se crearon tickets de más durante las pruebas**
Borra la carpeta: `rm -rf sesion-4-adk-mcp/tickets`.

## Evaluación

**Las métricas con juez fallan con 404**
El juez por defecto de ADK 2.14 es `gemini-2.5-flash`, ya retirado. Fija `judge_model` en el archivo de configuración, como hacen los de `sesion-3-evaluacion/`.

**El evalset de incidente falla después de un rato**
Las señales ya no caen en la última hora. Ejecuta `python scripts/sembrar_senales.py --forzar` y repite.

## Agent Runtime

**`desplegar.sh` falla al otorgar roles**
Necesitas `roles/resourcemanager.projectIamAdmin` y `roles/iam.serviceAccountAdmin`, o `roles/owner`. Si el error es `concurrent policy changes`, el script ya reintenta; vuelve a ejecutarlo.

**El despliegue tarda más de 10 minutos o falla en la construcción** *(previsto)*
Revisa `sesion-2-agent-runtime/build/deploy.log` y los logs en la consola: **Agent Platform → Agent Runtime → tu agente → Logs**. Volver a ejecutar `./desplegar.sh` actualiza el mismo recurso.

**La organización restringe ubicaciones** *(previsto)*
Elige una región permitida: `REGION=us-east1 ./setup.sh` y después `./sesion-2-agent-runtime/desplegar.sh`. Gemini necesita además la ubicación `global`.

**`gcloud agent-registry: Invalid choice`**
Tu Google Cloud CLI es anterior a ese grupo de comandos. Usa `python sesion-2-agent-runtime/ver_registro.py`, que llama a la API REST, o actualiza con `gcloud components update`.

## Model Armor

**`404` o `PERMISSION_DENIED` al crear o usar el template** *(previsto)*
Model Armor solo atiende en endpoints regionales. Los scripts del repo ya lo configuran. Si usas `gcloud` a mano: `export CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.REGION.rep.googleapis.com/"`.

**El template no existe en la región**
El template se crea en la `REGION` de tu `.env`. Si cambiaste de región, vuelve a ejecutar `./sesion-6-model-armor/crear_template.sh`.

## Empezar de cero

```bash
./cleanup.sh --local      # borra recursos del proyecto y archivos locales
# espera unos 10 minutos
./setup.sh
```
