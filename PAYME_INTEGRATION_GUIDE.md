# 🚀 Payme Integration Qo'llanmasi

## 1️⃣ Setup & Installation

### Step 1: Environment Variables
`.env` faylingizga Payme credentials'ni qo'shing:

```bash
PAYME_MERCHANT_ID=67c19bd7e4b4003392f291ef
PAYME_LOGIN=Paycom
PAYME_SECRET_KEY=mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO
```

### Step 2: Database Migration
```bash
python manage.py migrate
```

Bu `payme_transactions` jadvalni yaratadi.

### Step 3: Verify Installation
```bash
python manage.py shell
from apps.payment.models import PaymeTransaction
print(PaymeTransaction.objects.count())  # Should return 0
```

---

## 2️⃣ Frontend Integration (React/Vue)

### Frontend Flow:
```
User → Checkout Button → /payment/checkout/ API
   ↓
PaymeTransaction yaratiladi
   ↓
Payme Checkout URL qaytariladi
   ↓
User Payme'da to'lov qiladi
   ↓
Payme user'ni return URL'ga yo'naltiradi
   ↓
Backend webhook bilan balansi yangilaydi
```

### Example: React Component

```jsx
import { useState } from 'react';
import axios from 'axios';

export default function PaymentWidget() {
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCheckout = async () => {
    try {
      setLoading(true);
      const response = await axios.post(
        'https://api.yourdomain.com/payment/checkout/',
        { amount: parseInt(amount) },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );

      // Payme checkout URL'ni open qilish
      window.location.href = response.data.payment_url;
    } catch (error) {
      alert('Error: ' + error.response.data.detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="payment-widget">
      <h2>Balansingizga pul qo'shing</h2>
      <input
        type="number"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="Miqdor (som'da)"
        min="1000"
      />
      <button onClick={handleCheckout} disabled={loading}>
        {loading ? 'Kutilmoqda...' : 'Payme bilan to\'lov qilish'}
      </button>
    </div>
  );
}
```

---

## 3️⃣ Backend Integration Examples

### 3.1 Course Buying (Courses App)

```python
# apps/courses/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.payment.models import PaymeTransaction
from .models import Course

class BuyCourseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = Course.objects.get(id=course_id)
        
        # Check user balance
        if request.user.balance < course.price:
            # Payme to'lov linkini create qilish
            amount_needed = course.price - request.user.balance
            tx = PaymeTransaction.objects.create(
                user=request.user,
                amount_tiyin=int(amount_needed * 100),
                state=PaymeTransaction.STATE_PENDING,
            )
            from apps.payment.services import payme_checkout_link
            url = payme_checkout_link(tx.id, tx.amount_tiyin, lang="uz")
            
            return Response({
                "status": "payment_required",
                "payment_url": url,
                "amount_needed": amount_needed
            }, status=402)
        
        # Course'ni sotib ol
        request.user.balance -= course.price
        request.user.save()
        request.user.courses.add(course)
        
        return Response({"status": "success", "message": "Course sotib olindi"})
```

### 3.2 User Balance Check View

```python
# apps/users/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class UserBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "balance": float(request.user.balance),
            "recent_transactions": list(
                request.user.payme_transactions.values(
                    'id', 'amount_tiyin', 'state', 'created_at'
                )[:5]
            )
        })
```

### 3.3 Balance Transfer Between Users (Admin)

```python
# apps/users/views.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from decimal import Decimal

class AdminTransferBalanceAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from_user_id = request.data.get("from_user_id")
        to_user_id = request.data.get("to_user_id")
        amount = Decimal(request.data.get("amount"))

        from_user = User.objects.get(id=from_user_id)
        to_user = User.objects.get(id=to_user_id)

        if from_user.balance < amount:
            return Response({"error": "Insufficient balance"}, status=400)

        from_user.balance -= amount
        to_user.balance += amount
        from_user.save()
        to_user.save()

        return Response({"status": "success"})
```

---

## 4️⃣ Admin Panel Usage

Django admin panelida `/admin/payment/paymetransaction/`:

### View All Transactions
```
Filter by:
- Status (Pending, Done, Canceled)
- Date range
- User

Search by:
- User phone number
- Transaction ID
- Payme transaction ID
```

### Monitor Real-time
```python
# Shell'da check qilish
python manage.py shell

from apps.payment.models import PaymeTransaction
from django.utils import timezone
from datetime import timedelta

# Today's payments
today = timezone.now().date()
txs = PaymeTransaction.objects.filter(
    created_at__date=today,
    state=PaymeTransaction.STATE_DONE
)
total = sum(t.amount_som() for t in txs)
print(f"Today total: {total} som, Transactions: {txs.count()}")
```

---

## 5️⃣ Webhook Debugging

### Payme Test Tool
Payme official test panel'dan webhook'larni test qilish:
https://payme.uz/pages/test-tools/

### Local Testing (ngrok)

Production'da Payme sizning webhook URL'ingizga POST requests yuboradi.

Local development uchun ngrok ishlatish:

```bash
# 1. Ngrok'ni o'rnatish
brew install ngrok  # Mac
apt install ngrok   # Ubuntu

# 2. Local server'ni expose qilish
ngrok http 8000

# 3. Output: https://xxxx-xxxx-xxxx.ngrok.io

# 4. Payme'da webhook URL'ni o'rnatish
https://xxxx-xxxx-xxxx.ngrok.io/payment/payme/webhook/
```

### Webhook Testing Script

```python
# test_payme_webhook.py

import requests
import base64
import json

WEBHOOK_URL = "http://localhost:8000/payment/payme/webhook/"
LOGIN = "Paycom"
PASSWORD = "mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO"

# Basic auth header
credentials = base64.b64encode(f"{LOGIN}:{PASSWORD}".encode()).decode()
headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json"
}

# Test data
transaction_id = "test-tx-123"
amount = 100000  # 1000 som

# Test CheckPerformTransaction
response = requests.post(
    WEBHOOK_URL,
    json={
        "jsonrpc": "2.0",
        "method": "CheckPerformTransaction",
        "params": {
            "account": {"user_id": transaction_id},
            "amount": amount
        },
        "id": 1
    },
    headers=headers
)
print("CheckPerform:", response.json())
```

---

## 6️⃣ Security Best Practices

### ✅ DO:
- [x] Payme credentials'ni `.env` fayliga saqlang
- [x] HTTPS'ni production'da ishlatish (Payme talabi)
- [x] Basic auth'ni o'g'lik tekshirish
- [x] Amount validation'ni har safar qilish
- [x] Database lock'dan foydalanish (select_for_update)
- [x] Webhook'larni logging qilish
- [x] Rate limiting qo'llash

### ❌ DON'T:
- [ ] Credentials'ni code'da hardcode qilmang
- [ ] Webhook'ning CSRF protection'sini o'chirg'aning
- [ ] Amount validation'ni skip qilmang
- [ ] Webhook'larni log'iga saqlashda sensitive data qo'llanmang
- [ ] Concurrent request'larni lock'siz handle qilmang

---

## 7️⃣ Monitoring & Analytics

### Daily Report Script

```python
# management/commands/payment_report.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.payment.models import PaymeTransaction
from apps.users.models import User

class Command(BaseCommand):
    def handle(self, *args, **options):
        today = timezone.now().date()
        
        done_txs = PaymeTransaction.objects.filter(
            created_at__date=today,
            state=PaymeTransaction.STATE_DONE
        )
        
        total_income = sum(t.amount_som() for t in done_txs)
        total_count = done_txs.count()
        
        print(f"📊 Daily Report - {today}")
        print(f"✅ Completed: {total_count} transactions")
        print(f"💰 Total Income: {total_income:,.2f} som")
        
        # Pending transactions
        pending = PaymeTransaction.objects.filter(
            created_at__date=today,
            state=PaymeTransaction.STATE_PENDING
        ).count()
        print(f"⏳ Pending: {pending} transactions")
```

Qo'llanish:
```bash
python manage.py payment_report
```

---

## 8️⃣ Common Issues & Solutions

### Issue 1: "Method not found" Error
```
Error: {"code": -32601, "message": "Method topilmadi"}
```
**Solution:** Webhook URL to'g'ri configured ekanligini tekshiring

### Issue 2: "Account not found"
```
Error: {"code": -31050, "message": "Hisob topilmadi"}
```
**Solution:** Transaction ID to'g'ri ekanligini tekshiring

### Issue 3: "Invalid amount"
```
Error: {"code": -31008, "message": "Noto'g'ri summa"}
```
**Solution:** Frontend'dan yuborilgan miqdor = database'dagi miqdor ekanligini tekshiring

### Issue 4: Balance yangilnmadi
**Solution:**
```python
# Direct SQL'da tekshiresh
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT balance FROM users_user WHERE id=%s", [user_id])
    print(cursor.fetchone())
```

---

## 9️⃣ Future Enhancements

- [ ] SMS notification when payment successful
- [ ] Email receipt generation
- [ ] Refund mechanism
- [ ] Multiple payment providers (Click, Apelsin)
- [ ] Payment analytics dashboard
- [ ] Subscription/recurring billing
- [ ] Invoice system

---

## ✅ Deployment Checklist

- [ ] Payme contract olish va credentials'ni olish
- [ ] `.env`'da credentials'ni o'rnatish
- [ ] `python manage.py migrate` ishlatish
- [ ] `python manage.py createsuperuser` admin users yaratish
- [ ] Payme'da webhook URL'ni ro'yxatdan o'tkazish
- [ ] Django admin'da test transaction yaratish
- [ ] Frontend'dan to'lov linkini test qilish
- [ ] Payme test tool'dan webhook test qilish
- [ ] Production server'da logs'ni monitoring qilish

---

**Version:** 1.0  
**Last Updated:** 2026-05-08  
**Support:** Payme API Docs - https://payme.uz/merchantmanual/
