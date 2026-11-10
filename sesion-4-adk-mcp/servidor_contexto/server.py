"""Servidor MCP local (stdio) con el contexto de negocio de Farmalab.

Representa los sistemas externos a Google Cloud de los que un agente de
observabilidad toma contexto: el catalogo de servicios (CMDB), los runbooks y
el historial de despliegues. Aqui lee un JSON; en tu empresa, cada tool
llamaria a la API real (Backstage, ServiceNow CMDB, tu pipeline de CI/CD).

Probarlo solo:  python servidor_contexto/server.py   (queda esperando por stdio)
"""

import datetime as dt
import json
import pathlib

from mcp.server.mcpserver import MCPServer

# Busca la carpeta datos/ subiendo desde este archivo: asi funciona igual en el
# repo y dentro del paquete que se despliega en Agent Runtime.
RAIZ = pathlib.Path(__file__).resolve().parent
while not (RAIZ / "datos" / "catalogo_servicios.json").exists():
  RAIZ = RAIZ.parent
CATALOGO = json.loads((RAIZ / "datos" / "catalogo_servicios.json").read_text())
ARCHIVO_INCIDENTE = RAIZ / "datos" / ".incidente.json"

mcp = MCPServer("contexto-farmalab")


def _inicio_incidente() -> dt.datetime:
  """Hora en que empezo el incidente sembrado (o hace 22 min si no hay archivo)."""
  if ARCHIVO_INCIDENTE.exists():
    texto = json.loads(ARCHIVO_INCIDENTE.read_text())["inicio_incidente"]
    return dt.datetime.fromisoformat(texto.replace("Z", "+00:00"))
  return dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=22)


@mcp.tool()
def listar_servicios() -> list[str]:
  """Lista los nombres de los servicios registrados en el catalogo."""
  return sorted(CATALOGO["servicios"])


@mcp.tool()
def obtener_servicio(servicio: str) -> dict:
  """Devuelve la ficha de un servicio: equipo responsable, guardia, criticidad,
  dependencias, SLO y runbook.

  Args:
    servicio: nombre exacto del servicio, por ejemplo "pagos-gateway".
  """
  ficha = CATALOGO["servicios"].get(servicio)
  if ficha is None:
    return {"error": f"Servicio desconocido: {servicio}",
            "servicios_validos": sorted(CATALOGO["servicios"])}
  return {"servicio": servicio, **ficha}


@mcp.tool()
def listar_despliegues(servicio: str) -> list[dict]:
  """Devuelve los despliegues recientes de un servicio, del mas nuevo al mas
  antiguo, con version, hora (UTC), autor y descripcion del cambio.

  Args:
    servicio: nombre exacto del servicio, por ejemplo "pagos-gateway".
  """
  inicio = _inicio_incidente()
  return [
      {"servicio": d["servicio"], "version": d["version"],
       "desplegado_utc": (inicio - dt.timedelta(
           minutes=d["minutos_antes_del_incidente"])).strftime(
               "%Y-%m-%dT%H:%M:%SZ"),
       "autor": d["autor"], "cambio": d["cambio"]}
      for d in CATALOGO["despliegues"] if d["servicio"] == servicio
  ]


if __name__ == "__main__":
  mcp.run()  # transporte stdio por defecto
