"""Mesa de ayuda simulada: cada ticket es un archivo JSON en la carpeta tickets/.

Reemplaza a Jira o ServiceNow para que el lab no dependa de un sistema externo.
En produccion esta funcion seria una llamada a ApplicationIntegrationToolset,
a un servidor MCP de tu mesa de ayuda o a su API REST.
"""

import datetime as dt
import json
import os
import pathlib

CARPETA = pathlib.Path(os.environ.get("TICKETS_DIR", "tickets"))


def crear_ticket(titulo: str, servicio: str, severidad: str, equipo: str,
                 resumen: str, evidencia: list[str],
                 accion_sugerida: str) -> dict:
  """Abre un ticket de incidente en la mesa de ayuda.

  Args:
    titulo: titulo corto del incidente.
    servicio: servicio afectado, por ejemplo "pagos-gateway".
    severidad: "alta", "media" o "baja".
    equipo: equipo responsable que debe atenderlo, segun el catalogo.
    resumen: que esta pasando y desde cuando, en dos o tres frases.
    evidencia: hallazgos concretos de logs y metricas que sustentan el ticket.
    accion_sugerida: accion recomendada segun el runbook.

  Returns:
    El id del ticket creado y la ruta del archivo.
  """
  CARPETA.mkdir(parents=True, exist_ok=True)
  numero = len(list(CARPETA.glob("TCK-*.json"))) + 1
  ticket_id = f"TCK-{numero:04d}"
  ticket = {
      "id": ticket_id,
      "creado_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
      "titulo": titulo, "servicio": servicio, "severidad": severidad,
      "equipo": equipo, "resumen": resumen, "evidencia": evidencia,
      "accion_sugerida": accion_sugerida, "estado": "abierto",
  }
  ruta = CARPETA / f"{ticket_id}.json"
  ruta.write_text(json.dumps(ticket, ensure_ascii=False, indent=2))
  return {"ticket_id": ticket_id, "archivo": str(ruta), "estado": "abierto"}
