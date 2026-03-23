# myrobobk — Production Deployment Guide

## Tezkor ishga tushirish

### 1. `.env` fayl tayyorlash
```bash
cp .env.example .env
```
`.env` faylini oching va quyidagilarni **albatta** o'zgartiring:
- `SECRET_KEY` — uzun tasodifiy string (masalan: `openssl rand -hex 50`)
- `POSTGRES_PASSWORD` — kuchli parol
- `BOT_OTP_SECRET` — Telegram bot secret
- `BOT_TOKEN` — Telegram bot tokeni
- `ALLOWED_HOSTS` — serveringizning domenini yozing

### 2. Judge sandbox image build
```bash
cd backend
docker build -t judge-sandbox:latest apps/courses/judgenew/
cd ..
```

### 3. Production deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

Yoki qo'lda:
```bash
docker compose -f deploy/docker/production/docker-compose.yml up -d
docker compose -f deploy/docker/production/docker-compose.yml exec web python manage.py migrate
docker compose -f deploy/docker/production/docker-compose.yml exec web python manage.py collectstatic --noinput
docker compose -f deploy/docker/production/docker-compose.yml exec web python manage.py createsuperuser
```

### 4. SSL sertifikat (Let's Encrypt)
```bash
certbot certonly --webroot -w /var/www/certbot -d api.myrobo.uz
```

---

## Lokal ishlab chiqish

```bash
cp .env.example .env
# .env da DJANGO_SETTINGS_MODULE=config.settings.local qiling

docker compose -f deploy/docker/local/docker-compose.yml up -d
docker compose -f deploy/docker/local/docker-compose.yml exec web python manage.py migrate
docker compose -f deploy/docker/local/docker-compose.yml exec web python manage.py createsuperuser
```

---

## Muhim eslatmalar

### Xavfsizlik
- `.env` faylini **hech qachon** git-ga qo'shmang
- `SECRET_KEY` ni production va local uchun **alohida** ishlating
- `DEBUG=0` production-da har doim

### Obuna hisob-kitob (cron)
Har kuni bir marta muddati tugagan obunalarni qayta hisoblash:
```bash
# crontab -e
0 2 * * * docker compose -f /path/to/deploy/docker/production/docker-compose.yml \
  exec -T web python manage.py bill_subscriptions >> /var/log/bill.log 2>&1
```

### Loglarni ko'rish
```bash
docker compose -f deploy/docker/production/docker-compose.yml logs -f web
docker compose -f deploy/docker/production/docker-compose.yml logs -f nginx
```

### Ma'lumotlar bazasi backup
```bash
docker compose -f deploy/docker/production/docker-compose.yml \
  exec db pg_dump -U myapp myapp > backup_$(date +%F).sql
```

---

## Loyiha tuzilmasi

```
myrobobk_prod/
├── .env.example          ← Namuna (haqiqiy .env EMAS)
├── .gitignore
├── deploy.sh             ← Avtomatik deploy
├── backend/
│   ├── Dockerfile        ← Multi-stage build
│   ├── manage.py
│   ├── requirements/
│   │   └── base.txt
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py       ← Asosiy sozlamalar
│   │   │   ├── production.py ← Production sozlamalari
│   │   │   └── local.py      ← Lokal dev
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── apps/
│       ├── common/       ← BaseModel, exception handler
│       ├── users/        ← JWT auth, OTP login
│       ├── courses/      ← Kurslar, judge, subscription
│       ├── blog/         ← Blog, comment
│       └── teachers/     ← O'qituvchilar
└── deploy/
    ├── docker/
    │   ├── local/
    │   │   └── docker-compose.yml
    │   └── production/
    │       └── docker-compose.yml  ← Redis, health checks
    └── nginx/
        └── production.conf         ← HTTPS, rate limit, gzip
```
