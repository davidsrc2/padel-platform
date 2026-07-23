#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

docker compose up -d db

echo "Esperando a Postgres..."
until docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; do
    sleep 1
done

source venv/bin/activate
python manage.py migrate

python manage.py runserver &
SERVER_PID=$!

echo ""
echo "Servidor arriba en http://localhost:8000 — pulsa Enter para parar"
read -r

kill "$SERVER_PID" 2>/dev/null
docker compose down
