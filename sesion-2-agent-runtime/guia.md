# Sesión II · Desplegar en Agent Runtime y verlo en Agent Registry (ejemplo corto, 10 min)

Acompaña la charla de Agent Runtime y Agent Registry. Despliegas el agente de la sesión IV como servicio gestionado, con identidad propia, y compruebas que quedó registrado.

Requisito: haber ejecutado `./setup.sh`. Despliega la solución del paso 5, así que puedes hacerlo antes de terminar el hands-on.

```bash
cd propel-workshop-farmatodo && source .venv/bin/activate
```

## 1 · Despliega (1 min tuyo, 6 min de espera)

```bash
./sesion-2-agent-runtime/desplegar.sh
```

El script hace tres cosas, y vale la pena leerlo:

1. **Identidad.** Crea la cuenta de servicio `agente-obs` con permisos de solo lectura sobre las señales (`roles/mcp.toolUser`, `roles/logging.viewer`, `roles/monitoring.viewer`), más `roles/aiplatform.user` para llamar a Gemini y los roles para escribir su propia telemetría. Desplegado, el agente ya no usa tu usuario.
2. **Paquete.** Arma en `build/agente_obs/` una carpeta autocontenida: el agente, el servidor MCP de contexto, el catálogo, `requirements.txt` y `.env`.
3. **Despliegue.** Ejecuta `adk deploy agent_engine` con `--service_account` y `--otel_to_cloud`.

**Qué deberías ver.** Al final, `Deployed to Agent Platform: projects/.../reasoningEngines/NNN` y un enlace al playground de la consola. En la prueba tardó 6 minutos la primera vez y 3 minutos y medio al actualizar. Lánzalo y sigue escuchando la charla.

Los nombres cambiaron en 2026 y el código no: el producto se llama Agent Runtime, pero el comando sigue siendo `agent_engine` y el recurso `reasoningEngines`.

Para desplegar tu propia versión en lugar de la solución: `./sesion-2-agent-runtime/desplegar.sh --mio`. Si ya habías desplegado, actualiza el mismo recurso.

## 2 · Consulta el agente desplegado (2 min)

```bash
python sesion-2-agent-runtime/consultar.py
python sesion-2-agent-runtime/consultar.py "Que equipo atiende pedidos-api?"
```

**Qué deberías ver.** Las mismas líneas `[tool]` que en tu máquina y el diagnóstico del incidente. Ahora las llamadas a los MCP las hace la cuenta de servicio del agente, y el servidor MCP de contexto corre como proceso hijo dentro del contenedor.

`consultar.py` son 15 líneas útiles: `vertexai.Client(...).agent_engines.get(name=...)` y `async_stream_query(...)`.

## 3 · Míralo en Agent Registry (2 min)

```bash
python sesion-2-agent-runtime/ver_registro.py
```

**Qué deberías ver.**

- En `Agentes en REGION`: `agente-obs-farmalab`. Nadie lo registró a mano: Agent Runtime lo hace al desplegar.
- En `Servidores MCP en global`: `logging.googleapis.com`, `monitoring.googleapis.com` y los demás servidores MCP de las APIs que tienes habilitadas.

En la consola: **Agent Platform → Agent Registry**.

## Para tener en cuenta

- Dentro de Agent Runtime, `GOOGLE_CLOUD_PROJECT` trae el **número** del proyecto. Los filtros de logs necesitan el id, y por eso el paquete define `SIGNALS_PROJECT_ID`.
- La aprobación humana del paso 5 también funciona desplegada: el pedido de confirmación llega como un evento y se responde con otro mensaje en la misma sesión. Se probó por API, no en el playground de la consola.
- Los tickets se escriben en `/tmp/tickets` del contenedor y se pierden. En producción la herramienta llamaría a la mesa de ayuda real.
- No hay región de Agent Runtime en Colombia. En Sudamérica solo existe `southamerica-east1`.
- Cuota por defecto: 90 consultas por minuto por proyecto y región.
- Para borrarlo: `./cleanup.sh`.
