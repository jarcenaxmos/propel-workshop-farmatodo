"""Conexion a los servidores MCP de Google Cloud. YA VIENE HECHO: no lo edites.

En tu maquina el agente se autentica con tu usuario y esto no hace nada
especial. Desplegado en Agent Runtime el agente usa Agent Identity, y el token
de esa identidad esta LIGADO al certificado del agente (mTLS): hay que
presentarlo al conectar, y para eso se usa el endpoint
https://SERVICIO.mtls.googleapis.com/mcp. Sin el certificado el servidor
responde 401. Las librerias de Google lo hacen solas; el cliente HTTP del MCP
no, por eso existe este archivo.
"""

from google.auth.transport import mtls

try:
  import httpx2 as _httpx  # el SDK de MCP 2.x usa httpx2
except ImportError:  # pragma: no cover
  import httpx as _httpx


def _certificado():
  """Contexto SSL con el certificado del agente, o None si no hay (en local)."""
  contexto = mtls.get_default_ssl_context()
  if contexto is None or not mtls.should_use_mtls_endpoint(True):
    return None
  return contexto


def url_mcp(servicio: str) -> str:
  """URL del servidor MCP de un servicio ("logging", "monitoring")."""
  sufijo = "mtls." if _certificado() is not None else ""
  return f"https://{servicio}.{sufijo}googleapis.com/mcp"


def cliente_http(headers=None, timeout=None, auth=None):
  """Fabrica de clientes HTTP para McpToolset (httpx_client_factory)."""
  if timeout is None:
    timeout = _httpx.Timeout(30.0, read=300.0)
  parametros = {"timeout": timeout}
  if headers is not None:
    parametros["headers"] = headers
  if auth is not None:
    parametros["auth"] = auth
  certificado = _certificado()
  if certificado is not None:
    parametros["verify"] = certificado
  return _httpx.AsyncClient(**parametros)
