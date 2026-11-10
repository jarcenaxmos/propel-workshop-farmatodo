# Prerrequisitos de los labs · Workshop Propel Farmatodo

Cada participante hace los labs desde Cloud Shell (en el navegador de su PC), en **un proyecto de Google Cloud propio**. Deja todo listo y verificado antes de la sesión para no gastar tiempo del hands-on en accesos.

## 1. Proyecto y permisos

- Un **proyecto sandbox por participante**, con **billing activo**. Nunca un proyecto productivo.
- **Opción simple (recomendada):** el participante es `roles/owner` de su proyecto sandbox.
- **Opción mínima:** estos roles predefinidos sobre el proyecto.

| Rol | Para qué | Sesión |
|---|---|---|
| `roles/aiplatform.user` | Gemini, Agent Runtime y evaluación | todas |
| `roles/mcp.toolUser` | Llamar herramientas de los servidores MCP de Google Cloud | IV |
| `roles/logging.viewer` | Herramientas de lectura del MCP de Cloud Logging | IV |
| `roles/monitoring.viewer` | Herramientas de lectura del MCP de Cloud Monitoring | IV |
| `roles/logging.logWriter` | `setup.sh` escribe los logs de ejemplo | IV |
| `roles/monitoring.editor` | `setup.sh` escribe las métricas de ejemplo y crea la política de alertas | IV |
| `roles/serviceusage.serviceUsageAdmin` | Habilitar APIs (no hace falta si un admin ya las habilitó) | todas |
| `roles/resourcemanager.projectIamAdmin` | Darle roles a la Agent Identity del agente (`otorgar_roles.sh`) y quitárselos al limpiar | II |
| `roles/modelarmor.admin` | Crear el template de Model Armor | VI |
| `roles/agentregistry.viewer` | Ver agentes y servidores MCP en Agent Registry | II |

La documentación de los MCP pide `roles/logging.admin` y `roles/monitoring.admin`. Los labs solo usan herramientas de lectura y se probaron con los roles viewer de la tabla. La opción mínima no se probó completa de punta a punta: la prueba se hizo con `roles/owner`.

**Agent Identity (sesión II).** El agente se despliega con Agent Identity, nunca con una cuenta de servicio. La identidad es un principal `principal://agents.global.org-ID_ORG.system.id.goog/resources/aiplatform/...` si el proyecto está dentro de una organización, o `principal://agents.global.proj-NUMERO_DE_PROYECTO.system.id.goog/resources/aiplatform/...` si **no** tiene organización; `otorgar_roles.sh` detecta cuál corresponde. Requisitos: la API `aiplatform.googleapis.com` habilitada, poder crear instancias de Agent Runtime (`roles/aiplatform.user` o `roles/owner`) y poder asignar roles en el proyecto (`roles/resourcemanager.projectIamAdmin` o `roles/owner`). Una política de organización no debe bloquear a las identidades de agentes ni las ubicaciones usadas.

Si la organización restringe ubicaciones (`gcp.resourceLocations`), el proyecto debe permitir `global` (Gemini) y una región de Agent Runtime, por defecto `us-central1`.

## 2. APIs a habilitar

`setup.sh` las habilita. Si prefieres que lo haga un administrador antes:

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudresourcemanager.googleapis.com \
  cloudtrace.googleapis.com \
  telemetry.googleapis.com \
  storage.googleapis.com \
  modelarmor.googleapis.com \
  agentregistry.googleapis.com \
  --project=PROJECT_ID
```

Las tres primeras alcanzan para el hands-on de la sesión IV. Los servidores MCP de Logging (`https://logging.googleapis.com/mcp`) y Monitoring (`https://monitoring.googleapis.com/mcp`) quedan disponibles al habilitar sus APIs. No hay paso extra.

## 3. Modelos Gemini y región

- Gemini se usa por Agent Platform con la ubicación `global`. El modelo de los labs es `gemini-3.8-flash`.
- Agent Runtime y Model Armor usan una región, por defecto `us-central1`. Se cambia con la variable `REGION`. No hay región de Agent Runtime en Colombia; la más cercana es `southamerica-east1` (São Paulo).

## 4. Equipo y red

- **Google Chrome** actualizado, con la cuenta que tiene acceso al proyecto.
- **Cloud Shell (recomendado):** ya trae `gcloud`, `git` y Python. No hay que instalar nada.
- **Local (alternativa):** Python **3.11 o superior**, Google Cloud CLI con `gcloud auth application-default login`, y `git`.
- **Red:** que el proxy o la VPN no bloqueen `console.cloud.google.com`, `*.googleapis.com`, `accounts.google.com`, `*.gstatic.com`, Cloud Shell y su vista previa web (`*.cloudshell.dev`), `github.com`, `pypi.org` y `files.pythonhosted.org`.

## 5. Verificación en 5 minutos

En Cloud Shell, con el proyecto del participante:

```bash
# 1. Cuenta y proyecto correctos
P=PROJECT_ID
gcloud auth list --filter=status:ACTIVE --format="value(account)"
# 2. Billing activo: debe decir True
gcloud billing projects describe $P --format="value(billingEnabled)"
# 3. APIs habilitadas: deben salir las 9
gcloud services list --enabled --project=$P --format="value(config.name)" \
 | grep -E "aiplatform|logging|monitoring|cloudtrace|telemetry|storage\.googleapis|cloudresourcemanager|modelarmor|agentregistry"
# 4. Python 3.11 o superior
python3 --version
# 5. Gemini responde: debe aparecer "ok" en el texto
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
 -H "Content-Type: application/json" \
 "https://aiplatform.googleapis.com/v1/projects/$P/locations/global/publishers/google/models/gemini-3.8-flash:generateContent" \
 -d '{"contents":[{"role":"user","parts":[{"text":"Responde solo: ok"}]}]}' | grep '"text"'
# 6. El MCP de Cloud Logging responde: debe aparecer "result"
curl -s -X POST https://logging.googleapis.com/mcp \
 -H "Authorization: Bearer $(gcloud auth print-access-token)" \
 -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
 -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"list_log_names\",\"arguments\":{\"parent\":\"projects/$P\"}}}" | cut -c1-80
# 7. Salida a GitHub y PyPI
git ls-remote https://github.com/google/adk-python HEAD && pip download --no-deps -q -d /tmp/x google-adk==2.14.0 && echo red-ok
```

Después de clonar el repo, `./setup.sh` termina con una verificación más completa (`python scripts/verificar.py`).

## 6. Qué no necesitan y cuidados

- No necesitan licencia de Gemini Enterprise, Jira ni ServiceNow: los tickets del lab son simulados.
- No usar un proyecto productivo ni datos reales de clientes.
- El costo esperado es bajo: menos de USD 5 por participante (estimación), con llamadas a Gemini Flash y recursos pequeños. Recomendamos un presupuesto con alerta en cada proyecto.
- Al final, ejecutar `./cleanup.sh` o borrar el proyecto sandbox completo.
