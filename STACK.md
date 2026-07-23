# Stack

- Django 6.0.7 + PostgreSQL 16 (Docker)
- BD ya es Postgres (no SQLite) — en producción (Render/Railway/etc.) solo cambian las env vars de conexión
- Tailwind vía django-tailwind
- Auth custom: `accounts.Usuario`

## Arrancar / parar

```
./dev.sh
```

Levanta Postgres (Docker), aplica migraciones y arranca el server. Enter para parar todo.
