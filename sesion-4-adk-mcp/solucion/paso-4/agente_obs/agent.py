"""Agente de observabilidad de Farmalab. Solucion.

Paso 4: toma contexto de sistemas externos con un servidor MCP propio.
"""

import datetime as dt
import os
import pathlib
import sys

import google.auth
import google.auth.transport.requests
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams
from mcp import StdioServerParameters

# Proyecto donde estan las senales. Desplegado en Agent Runtime,
# GOOGLE_CLOUD_PROJECT trae el NUMERO del proyecto y los filtros de logs
# necesitan el id, por eso se puede indicar aparte.
PROJECT_ID = os.environ.get("SIGNALS_PROJECT_ID",
                            os.environ["GOOGLE_CLOUD_PROJECT"])
# Gemini 3.x se sirve desde la ubicacion "global". Se fija aqui para que el
# agente funcione igual en tu maquina y desplegado en una region.
MODEL = Gemini(model=os.environ.get("MODEL", "gemini-3.8-flash"),
               client_kwargs={"location": "global"})


# --- Autenticacion hacia los servidores MCP de Google Cloud -----------------
# Usan OAuth 2.0 + IAM. El agente presenta un access token de las credenciales
# por defecto: tu usuario en Cloud Shell, la cuenta de servicio en Agent Runtime.
_credenciales, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"])


def encabezados_google(_contexto=None) -> dict[str, str]:
  """Encabezados de autenticacion. Renueva el token si ya vencio."""
  if not _credenciales.valid:
    _credenciales.refresh(google.auth.transport.requests.Request())
  return {
      "Authorization": f"Bearer {_credenciales.token}",
      "x-goog-user-project": PROJECT_ID,
  }


# --- PASO 2: senales de Cloud Logging por MCP --------------------------------
logging_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://logging.googleapis.com/mcp", timeout=30),
    header_provider=encabezados_google,
    # Solo lectura y solo lo necesario: el modelo no ve el resto de las tools.
    tool_filter=["list_log_entries", "list_log_names"],
)


# --- PASO 3: senales de Cloud Monitoring por MCP -----------------------------
monitoring_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://monitoring.googleapis.com/mcp", timeout=30),
    header_provider=encabezados_google,
    tool_filter=["list_timeseries", "list_alert_policies"],
)


# --- PASO 4: contexto de sistemas externos (servidor MCP propio, por stdio) --
# ADK lanza el servidor como un proceso hijo y le habla por stdin/stdout.
_LAB = pathlib.Path(__file__).resolve().parent
while not (_LAB / "servidor_contexto" / "server.py").exists():
  _LAB = _LAB.parent  # sube hasta la carpeta sesion-4-adk-mcp/
contexto_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[str(_LAB / "servidor_contexto" / "server.py")]),
        timeout=30),
)


def instruccion(_contexto=None) -> str:
  """Instruccion del agente. Es una funcion para poder incluir la hora actual."""
  ahora = dt.datetime.now(dt.timezone.utc)
  hace_una_hora = ahora - dt.timedelta(hours=1)
  f = "%Y-%m-%dT%H:%M:%SZ"
  return f"""
Eres el agente de observabilidad de Farmalab, una cadena de farmacias ficticia.
Ayudas a la guardia a entender incidentes y a abrir el ticket correcto.

Hora actual (UTC): {ahora.strftime(f)}. Hace una hora: {hace_una_hora.strftime(f)}.
Proyecto de Google Cloud: {PROJECT_ID}. En las herramientas de Google Cloud usa
siempre "projects/{PROJECT_ID}" como name, parent o resourceNames.

SENALES DISPONIBLES

Logs de aplicacion (herramienta list_log_entries):
- filter: logName="projects/{PROJECT_ID}/logs/farmalab-app"
  AND timestamp>="{hace_una_hora.strftime(f)}" y agrega lo que necesites, por
  ejemplo AND severity>=ERROR o AND labels.service="pagos-gateway".
- Usa orderBy "timestamp desc" y pageSize 50.
- Campos: severity, labels.service, labels.version, jsonPayload.error_code,
  jsonPayload.message, jsonPayload.status, jsonPayload.tienda_id.

Metricas (herramienta list_timeseries):
- custom.googleapis.com/farmalab/error_rate (fraccion de 0 a 1) y
  custom.googleapis.com/farmalab/latency_p95_ms, con la etiqueta service.
- Ejemplo de argumentos:
  filter: metric.type="custom.googleapis.com/farmalab/error_rate" AND
  metric.labels.service="pagos-gateway"
  interval: startTime "{hace_una_hora.strftime(f)}", endTime "{ahora.strftime(f)}"
  view: "FULL"
- Politicas de alerta: herramienta list_alert_policies.

Contexto del negocio (catalogo de servicios, runbooks y despliegues):
herramientas listar_servicios, obtener_servicio y listar_despliegues.

COMO INVESTIGAR UN INCIDENTE
1. Metricas del servicio: desde cuando sube el error o la latencia.
2. Logs con severity>=ERROR: cual es el error_code dominante.
3. Ficha del servicio y despliegues recientes: compara la hora del despliegue
   con el inicio del problema y lee el runbook.
4. Resume: que pasa, desde cuando, impacto, causa probable y evidencia.
No repitas consultas que ya hiciste. Con 4 a 6 llamadas suele alcanzar.

Responde en espanol, breve y con datos concretos (horas en UTC, valores).
"""


root_agent = LlmAgent(
    name="agente_obs",
    model=MODEL,
    description=("Investiga incidentes con senales de Cloud Logging y Cloud Monitoring"
                 " y contexto del negocio."),
    instruction=instruccion,
    tools=[
        logging_mcp,
        monitoring_mcp,
        contexto_mcp,
    ],
)
