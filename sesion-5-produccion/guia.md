# Sesión V · Trazas del agente en producción (ejemplo corto, 5 min)

Acompaña la charla de agentes en producción. Miras qué hizo el agente desplegado, cuánto tardó cada paso y cuántos tokens consumió.

Requisito: haber desplegado el agente en la sesión II (`./sesion-2-agent-runtime/desplegar.sh`). El despliegue usa `--otel_to_cloud`, que exporta la telemetría de ADK a Cloud Trace.

```bash
cd propel-workshop-farmatodo && source .venv/bin/activate
```

## 1 · Genera una traza y resúmela (3 min)

```bash
python sesion-2-agent-runtime/consultar.py
python sesion-5-produccion/ver_trazas.py
```

Las trazas tardan cerca de un minuto en aparecer. Si el segundo comando no encuentra nada, repítelo.

**Qué deberías ver.** Una tabla con los spans de la última consulta:

- `invoke_agent agente_obs`: el turno completo.
- `generate_content gemini-3.8-flash`: cada llamada al modelo, con sus tokens de entrada y salida.
- `execute_tool ...`: cada herramienta, del lado del agente.
- `tools/call ...`: el mismo llamado visto desde el servidor MCP de Google. Ese span lo emite Google, sin que hagas nada.

Y el total de tokens de la consulta.

## 2 · Míralo en la consola (2 min)

Abre el enlace que imprime el script (**Trace Explorer**) y elige la traza más reciente. La cascada muestra dónde se va el tiempo: casi todo es `generate_content`. Las herramientas MCP responden en menos de medio segundo.

En **Agent Platform → Agent Runtime → tu agente** están además las métricas de solicitudes, latencia y errores, y las sesiones.

## Para tener en cuenta

- Desde ADK 2.13 la telemetría sigue las convenciones GenAI de OpenTelemetry y ya no existe el span `call_llm`. Si tienes consultas o tableros que filtran por ese nombre, cámbialos a `generate_content`.
- Los tokens de entrada son altos por las definiciones de las herramientas MCP (ver la tabla del paso 3 de la sesión IV). La mayoría entra por caché de contexto, pero es el primer lugar donde mirar el costo.
- Lo que la charla cubre y este ejemplo no: revisiones con reparto de tráfico (Preview), Agent Gateway y evaluación continua. Agent Identity sí la usa el agente de este lab (ver la sesión II): en la traza verás los spans `tools/call` de los servidores MCP, que el agente invocó con su propia identidad.
