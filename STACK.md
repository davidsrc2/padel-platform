# Stack

- Django 6.0.7 + PostgreSQL 16 (Docker en local, gestionado en Render en producción)
- Tailwind vía CDN (Play CDN) + htmx 2.0.4 para reservar/cancelar sin recargar página
- Email: Brevo vía django-anymail (SMTP saliente bloqueado en Render free — por eso API HTTPS, no SMTP). Resend disponible como alternativa.
- Push notifications: pywebpush + VAPID, service worker en `static/sw.js`
- PWA instalable (manifest, iconos, meta tags iOS/Android)
- whitenoise + gunicorn para producción
- Auth custom: `accounts.Usuario` (roles: `vecino`, `admin_urb`, `superadmin`)
- Observabilidad: Sentry (`sentry-sdk[django]`), activado solo si `SENTRY_DSN` está definida (igual que VAPID — sin la variable, no hace nada)
- Rate limiting en login/registro/reset de contraseña: `django-ratelimit` + la caché en memoria por defecto de Django (sin coste, sin Redis). `LoginRateLimitView`/`PasswordResetRateLimitView` en `accounts/views.py` — 10 intentos/min en login, 5/hora en registro y en solicitar reset de contraseña, por IP. Con `block=False`: en vez de un 403 crudo, se muestra un mensaje normal vía `messages.error`

## Apps

- `accounts` — usuarios, roles, perfil, push subscriptions, emails de aprobación
- `urbanizaciones` — el modelo `Urbanizacion` (tenant), sus ajustes (horarios, límites de reserva)
- `viviendas` — `Portal` y `Vivienda`, jerarquía urbanización → portal → vivienda
- `pistas` — `Pista` y `BloqueoPista` (bloqueos de mantenimiento)
- `reservas` — el núcleo: reservas, calendario, franjas, recordatorios, resultados de partidos (`ResultadoPartido`/`SetResultado`/`Participante`) y estadísticas por jugador
- `panel` — panel de gestión para `admin_urb`/`superadmin` (no usan el admin de Django)
- `social` — capa social mínima: seguir vecinos (`Seguimiento`) y un feed con los resultados confirmados de a quién sigues. Solo se puede seguir dentro de la misma urbanización (mismo límite de tenant que el resto de la app)

## Partidos: jugadores con y sin perfil

`ResultadoPartido` no usa M2M a `Usuario` para los equipos — usa un modelo `Participante` (FK a `ResultadoPartido` + equipo A/B + o bien `usuario` o bien `nombre_invitado`, nunca ambos, constraint a nivel de BD). Así se puede registrar un partido contra alguien sin cuenta en la app. Consecuencia: si el rival es solo un invitado, nadie puede confirmar/disputar ese resultado desde la UI (el permiso exige un `Usuario` en el equipo rival) — se queda "pendiente" hasta que lo autoconfirma el comando `autoconfirmar_resultados` a las 48h, igual que cualquier otro resultado sin respuesta.

## Multi-tenencia (cómo está montado ahora)

`Urbanizacion` es el límite de tenant. Todo lo demás cuelga de ahí (`Portal → Vivienda → Usuario`, `Pista → Reserva`). El aislamiento es a nivel de aplicación, no de base de datos:

- `panel/permisos.py`: `resolver_urbanizacion(request)` decide qué urbanización gestiona el usuario (fija para `admin_urb`, seleccionable por `?urbanizacion=` para `superadmin`), y `limitar_a_urbanizacion(request, queryset, campo=...)` filtra cualquier queryset a esa urbanización si el usuario es `admin_urb`.
- Cada vista de `reservas`/`panel` usa uno de esos dos helpers — es el patrón a seguir para cualquier vista nueva que toque datos de una urbanización.
- Verificado con tests (`panel/tests.py`, `reservas/tests.py`): un `admin_urb` no puede ver ni tocar datos de otra urbanización; un vecino no puede acceder al panel.

Alta de comunidades (decisión: gestionada, no autoservicio público — David prefirió que pase por él):
- `panel:urbanizacion_crear` — superadmin crea solo la `Urbanizacion` (sin portal/vivienda/admin), pensado para dejar el hueco listo.
- `accounts:crear_comunidad` (`/accounts/crear-comunidad/`) — superadmin crea Urbanizacion + Portal + Vivienda + admin_urb aprobado en un paso. Ambas requieren login de superadmin (`@login_required` + check de rol); no hijackea la sesión del superadmin (no hace login automático como el admin recién creado).

## Arrancar / parar (local)

```
./dev.sh
```

Levanta Postgres (Docker), aplica migraciones, corre `seed_demo` (usuarios de prueba: `superadmin`/`admin_urb`/`vecino`, password `Test1234`) y arranca el server. Enter para parar todo.

## Despliegue

Render (staging: `padel-staging.onrender.com`). `build.sh` hace `pip install` + `collectstatic` + `migrate` + `ensure_superadmin` (crea el superadmin desde `DJANGO_SUPERUSER_*` si no existe). Variables de entorno: ver `.env.example`.

CI en GitHub Actions (`.github/workflows/tests.yml`): corre el test suite completo contra Postgres real en cada push/PR a `master`.

## Roadmap — hacia mayor escala

Objetivo: pasar de "una comunidad de prueba" a una plataforma que dé de alta comunidades reales sin intervención manual. Por prioridad:

1. ~~**Alta de comunidades.**~~ ✅ Hecho — pero gestionada por superadmin, no autoservicio público (decisión explícita, ver sección de Multi-tenencia arriba).
2. **Cola de tareas en background** (Celery/RQ + Redis) para email/push — ahora mismo se envían de forma síncrona dentro del ciclo request-response. A más volumen de reservas simultáneas, esto empieza a notarse en latencia.
3. **Facturación** si el modelo pasa a ser de pago: Stripe, planes por urbanización (límites de pistas/vecinos atados al plan).
4. **Panel de superadmin para gestionar muchas urbanizaciones**: listado con búsqueda/filtro/estado, no solo el selector desplegable actual (pensado para pocas).
5. **Observabilidad**: Sentry (o similar) para errores en producción — ahora mismo solo hay logs en Render, nadie se entera de un fallo salvo que un vecino se queje.
6. **Rate limiting** en login/registro público (django-ratelimit) antes de exponerlo a desconocidos a gran escala.
7. **Endurecer aislamiento de datos**: el filtrado actual es a nivel de aplicación (correcto y testeado), pero si esto maneja datos de muchas comunidades reales, plantearse Row-Level Security en Postgres como defensa adicional.
8. **Legal**: política de privacidad y términos de servicio si se gestionan datos personales (nombre, teléfono, email) de vecinos de varias comunidades distintas.

Con el punto 1 hecho, ya no hay bloqueo técnico para dar de alta comunidades reales. El resto (2-8) importa progresivamente según crezca el número de comunidades activas — ninguno es urgente con una o pocas.
