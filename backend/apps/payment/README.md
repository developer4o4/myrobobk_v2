# Payment App - Payme Integration

## 📋 Overview

Bu app Payme tolov tizimi bilan integratsiyani ta'minlaydi. Foydalanuvchilar o'z akkauntiga pul qo'shishlari va balans ariqali kurslar sotib olishlari mumkin.

## 🏗️ Architecture

```
payment/
├── models.py          # PaymeTransaction modeli
├── views.py           # Webhook va checkout API views
├── services.py        # Payme integration funksiyalari
├── serializers.py     # DRF serializers
├── urls.py            # URL routing
├── admin.py           # Django admin configuration
└── migrations/        # Database migrations
```

## 🔧 Configuration

### Environment Variables

`.env` fayligiga quyidagi o'zgaruvchilarni qo'shing:

```bash
# Payme credentials
PAYME_MERCHANT_ID=67c19bd7e4b4003392f291ef
PAYME_LOGIN=Paycom
PAYME_SECRET_KEY=mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO
```

**⚠️ XAVF:** Payme kalitlarini public repoga yuklashang! `.env` fayliga qo'shing va `.gitignore`'da ko'rsating.

### Settings

Settings `base.py`'da allaqachon qo'shilgan:

```python
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID")
PAYME_LOGIN = os.getenv("PAYME_LOGIN")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY")
```

## 📡 API Endpoints

### 1. **Checkout Link Yaratish**
```
POST /payment/checkout/
Authorization: Bearer <token>
Content-Type: application/json

{
  "amount": 10000  // som'da
}

Response:
{
  "order_id": "transaction-id",
  "payment_url": "https://checkout.payme.uz/m=...",
  "amount_som": 10000,
  "status": "pending"
}
```

### 2. **To'lov Tarixi**
```
GET /payment/history/
Authorization: Bearer <token>

Response:
{
  "transactions": [
    {
      "id": "transaction-id",
      "amount_som": 10000,
      "amount_tiyin": 1000000,
      "state": 2,
      "state_display": "Done",
      "created_at": "2026-05-08T10:30:00Z",
      "payme_transaction_id": "..."
    }
  ]
}
```

### 3. **Payme Webhook** (Internal)
```
POST /payment/payme/webhook/
Authorization: Basic <base64(login:password)>
Content-Type: application/json

Payme tomonida chaqiriladi. API'dan chaqirish shart emas.
```

## 🔄 Payment Flow

```
User (Frontend)
    ↓
[1] POST /payment/checkout/ → Transaction yaratiladi (STATE_PENDING)
    ↓
[2] Response: Payme checkout URL
    ↓
User Payme'da to'lov qiladi
    ↓
[3] Payme → Webhook: CheckPerformTransaction (to'lovni tekshirish)
    ↓
[4] Payme → Webhook: CreateTransaction (transaction'ni belgilash)
    ↓
[5] Payme → Webhook: PerformTransaction (balansi qo'shish) ✅
    ↓
User balance yangilandi!
```

## 💾 Database Model

### PaymeTransaction

| Field | Type | Description |
|-------|------|-------------|
| `id` | CharField(36) | Unique transaction ID (PK) |
| `user` | ForeignKey | Foydalanuvchi |
| `amount_tiyin` | PositiveBigInteger | Amount in tiyin (1 som = 100 tiyin) |
| `state` | SmallInteger | 1=Pending, 2=Done, -1=Canceled |
| `payme_transaction_id` | CharField(64) | Payme'ning transaction ID'si |
| `create_time` | BigInteger | Payme timestamp |
| `perform_time` | BigInteger | Payme timestamp |
| `cancel_time` | BigInteger | Payme timestamp |
| `reason` | Integer | Cancel reason code |
| `created_at` | DateTime | Created at (UTC) |
| `updated_at` | DateTime | Updated at (UTC) |

## 🔐 Security

1. **Basic Auth**: Payme webhook'lar PAYME_LOGIN va PAYME_SECRET_KEY bilan himoyalangan
2. **CSRF Exempt**: Webhook view CSRF'dan mustasno (Payme'ning talabi)
3. **Atomic Transactions**: Perform/Cancel'larda database lock ishlatiladi (concurrent requests uchun)
4. **Amount Validation**: Miqdor har safar tekshirilib, faqat qabul qilingan summa to'lanadi

## ⚙️ Admin Panel

Django admin panelidan `/admin/payment/paymetransaction/` orqali:

- Barcha tranzaksiyalarni ko'rish
- User va summa bo'yicha qidiruv
- Tranzaksiya holatini monitoring qilish
- Timestamp'larni ko'rish (collapsed)

## 🧪 Testing

### 1. Manual Test (Development)

```bash
# Database migrations
python manage.py migrate

# Checkout link yaratish
curl -X POST http://localhost:8000/payment/checkout/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000}'

# Response'dagi URL'ni browser'da oching
```

### 2. Webhook Test (with curl)

```bash
# Basic auth header
AUTH=$(echo -n "Paycom:mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO" | base64)

# CheckPerformTransaction
curl -X POST http://localhost:8000/payment/payme/webhook/ \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "CheckPerformTransaction",
    "params": {
      "account": {"user_id": "transaction-id"},
      "amount": 1000000
    },
    "id": 1
  }'
```

## 📝 Best Practices (Senior)

### 1. **Idempotency**
- PerformTransaction va CreateTransaction'lar qayta chaqirilishi mumkin
- Shuning uchun `if tx.state == STATE_DONE: return cached_response` ishlatiladi

### 2. **Atomic Transactions**
- `select_for_update()` database lock'i ishlatib, concurrent requests uchun himoya
- Balance qo'shish va transaction state'ni bir vaqtda yangilash

### 3. **Error Handling**
- Payme error code'larini standart ishlatish
- Foydalanuvchiga o'zbekcha va ruscha xabar berish

### 4. **Logging**
- `print()` o'rniga `logging` ishlatish tavsiya qilinadi (production'da)
- Transaction states va balance changes'ni track qilish

### 5. **Rate Limiting**
- `/payment/checkout/` authentication talab qiladi
- REST_FRAMEWORK throttling qo'llaniladi

## 🚀 Production Checklist

- [ ] `.env`'da Payme credentials'ni o'rnatish
- [ ] Database migration'larini ishlatish: `python manage.py migrate`
- [ ] Settings: `DEBUG=False`, `ALLOWED_HOSTS` to'g'ri
- [ ] HTTPS'ni ishlatish (Payme talabi)
- [ ] Payme'da webhook URL'ni ro'yxatdan o'tkazish: `https://yourdomain.com/payment/payme/webhook/`
- [ ] Admin panelida tranzaksiyalarni monitoring qilish
- [ ] Error logs'ni tekshirish

## 📖 Payme API Docs

- https://payme.uz/merchantmanual/
- https://payme.uz/apicourses/

---

**Created by:** Senior Developer  
**Last Updated:** 2026-05-08
