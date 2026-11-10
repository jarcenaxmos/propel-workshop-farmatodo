---
name: redactar-ticket-incidente
description: Formato y reglas de Farmalab para redactar el ticket de un incidente de produccion. Usala antes de proponer o crear un ticket.
metadata:
  version: "1.0.0"
  equipo: plataforma
---

# Redactar el ticket de un incidente

Aplica estas reglas cada vez que vayas a proponer o crear un ticket de incidente.

## Titulo

Formato: `[SEVERIDAD] servicio: sintoma en una frase`. Maximo 90 caracteres.
Ejemplo: `[ALTA] pagos-gateway: errores 504 UPSTREAM_TIMEOUT tras el despliegue 3.8.2`.

## Severidad

- alta: se incumple el SLO de un servicio de criticidad alta.
- media: se incumple el SLO de un servicio de criticidad media, o hay degradacion sin incumplir el SLO.
- baja: avisos aislados sin impacto en el SLO.

## Resumen

Tres frases, en este orden: que pasa y desde cuando (hora en UTC), a quien afecta, y la causa probable.
Escribe "causa probable", nunca "causa confirmada".

## Evidencia

De tres a cinco puntos. Cada punto lleva un valor y su origen: una metrica con su valor, o un error_code con la cantidad de entradas de log.
No pegues entradas de log completas ni identificadores de clientes o tarjetas.

## Accion sugerida

Una sola accion, tomada del runbook del servicio. Aclara quien la ejecuta. El agente nunca ejecuta la accion.
