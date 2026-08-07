# Padel Platform

Plataforma web de reservas de pistas de pádel pensada para urbanizaciones y comunidades de vecinos. Cada urbanización gestiona sus propias pistas, horarios y vecinos de forma aislada (multi-tenant), con reservas sin recarga de página, notificaciones push y resultados de partidos con estadísticas.

## Stack tecnológico

- **Backend:** Django 6.0.7 + PostgreSQL 16
- **Frontend:** Tailwind CSS (Play CDN) + htmx 2.0.4 para reservar/cancelar sin recargar la página
- **PWA:** instalable, con manifest, iconos y meta tags para iOS/Android
- **Notificaciones push:** pywebpush + VAPID, service worker en `static/sw.js`
- **Email:** Brevo vía django-anymail (API HTTPS), con Resend como alternativa
- **Producción:** Gunicorn + Whitenoise, desplegado en Render
- **Observabilidad:** Sentry, opcional (se activa solo si se define `SENTRY_DSN`)
- **Seguridad:** rate limiting en login/registro/reset de contraseña con django-ratelimit
- **CI:** GitHub Actions, tests contra Postgres real en cada push/PR a `master`

## Características principales

- **Reservas de pistas:** calendario de franjas horarias, bloqueos por mantenimiento, recordatorios.
- **Multi-tenencia por urbanización:** jerarquía `Urbanizacion → Portal → Vivienda → Usuario`, con aislamiento de datos a nivel de aplicación (verificado con tests).
- **Roles:** `vecino`, `admin_urb` (gestiona su urbanización) y `superadmin` (gestiona todas), con un panel de gestión propio distinto del admin de Django.
- **Resultados de partidos:** registro de resultados con o sin rival registrado en la app (invitados), confirmación por la parte contraria y autoconfirmación automática a las 48h si nadie responde.
- **Capa social:** seguir a otros vecinos de la misma urbanización y ver un feed de resultados confirmados.
- **Alta de comunidades gestionada:** el superadmin da de alta nuevas urbanizaciones (no es autoservicio público).

## Estructura del proyecto

| App | Responsabilidad |
|---|---|
| `accounts` | Usuarios, roles, perfil, suscripciones push, emails de aprobación |
| `urbanizaciones` | Modelo `Urbanizacion` (tenant) y sus ajustes (horarios, límites de reserva) |
| `viviendas` | `Portal` y `Vivienda` |
| `pistas` | `Pista` y `BloqueoPista` (bloqueos de mantenimiento) |
| `reservas` | Núcleo: reservas, calendario, resultados de partidos y estadísticas |
| `panel` | Panel de gestión para `admin_urb` / `superadmin` |
| `social` | Seguimiento entre vecinos y feed de resultados |

## Puesta en marcha

Requiere Docker (para PostgreSQL) y Python 3.

```bash
git clone https://github.com/davidsrc2/padel-platform.git
cd padel-platform
cp .env.example .env   # y ajusta las variables necesarias
./dev.sh
```

`dev.sh` levanta PostgreSQL en Docker, aplica las migraciones, carga datos de prueba (`seed_demo`) y arranca el servidor de desarrollo.

Usuarios de prueba creados por `seed_demo` (contraseña `Test1234`):
- `superadmin`
- `admin_urb`
- `vecino`

## Despliegue

Desplegado en Render. `build.sh` ejecuta `pip install`, `collectstatic`, `migrate` y `ensure_superadmin`. Las variables de entorno necesarias están documentadas en `.env.example`.
