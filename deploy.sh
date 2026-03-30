#!/usr/bin/env bash
# =============================================================
#  myrobobk — Production Deploy Scripti
#  Ishlatish: ./deploy.sh
# =============================================================
set -euo pipefail

COMPOSE="docker compose -f deploy/docker/production/docker-compose.yml"

echo "▶ [1/6] Eng so'nggi kodlarni olamiz..."
git pull origin main

echo "▶ [2/6] Judge sandbox image build..."
$COMPOSE build judge_image || true
# judge image build qilish (alohida)
cd backend
docker build -t judge-sandbox:latest apps/courses/judgenew/
cd ..

echo "▶ [3/6] Web image build..."
$COMPOSE build web

echo "▶ [4/6] Containerlari ishga tushiramiz..."
$COMPOSE up -d db redis dind
sleep 5

echo "▶ [5/6] Migratsiyalar..."
$COMPOSE run --rm web python manage.py migrate --noinput

echo "▶ [6/6] Static fayllarni yig'amiz..."
$COMPOSE run --rm web python manage.py collectstatic --noinput

echo "▶ Barcha xizmatlarni qayta ishga tushiramiz..."
$COMPOSE up -d --remove-orphans

echo ""
echo "✅ Deploy muvaffaqiyatli yakunlandi!"
echo "   Loglarni ko'rish: docker compose -f deploy/docker/production/docker-compose.yml logs -f web"
