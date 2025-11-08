# 🎉 Vibe Coding Platform - Plesk Edition

## نظام برمجة ذكي متعدد المستخدمين متوافق مع Plesk

### ✨ ما تم تطويره

نظام **محسّن بالكامل** للعمل على سيرفر Plesk بدون أي مخاطر:

1. ✅ **عزل تام** عن Plesk والمواقع الموجودة
2. ✅ **API واحد مركزي** لجميع المستخدمين
3. ✅ **نظام مصادقة** بـ project_id + password
4. ✅ **تثبيت بأمر واحد** بسيط
5. ✅ **صفر مخاطر** على السيرفر

---

## 🚀 التثبيت (أمر واحد فقط!)

### على السيرفر (95.217.62.146):

```bash
curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-plesk.sh | sudo bash
```

**أو يدوياً:**

```bash
git clone https://github.com/MarketingLimited/vibe-coding-platform.git
cd vibe-coding-platform
sudo ./install-plesk.sh
```

### ماذا يفعل سكريبت التثبيت؟

```
✓ يفحص النظام (Ubuntu 24, Plesk)
✓ يثبت Docker (إن لم يكن مثبتاً)
✓ ينشئ البنية الأساسية
✓ يولّد مفاتيح أمان
✓ يكوّن Firewall (localhost only)
✓ يبني صور Docker
✓ يشغّل الخدمات
✓ ينشئ سكريبتات إدارة
```

**النتيجة:**
- API يعمل على `localhost:9000`
- آمن تماماً (لا وصول خارجي)
- معزول عن Plesk بالكامل

---

## 📋 كيف يعمل النظام

### المعمارية

```
┌─────────────────────────────────────────┐
│         Plesk Server (آمن)             │
│  ┌──────────────────────────────────┐  │
│  │  المواقع الحالية (بدون تأثير)   │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │    Docker Network (معزول)        │  │
│  │  ┌────────────────────────────┐  │  │
│  │  │  Central API (localhost)   │  │  │
│  │  │  Port: 9000                │  │  │
│  │  └────────────────────────────┘  │  │
│  │         ↓    ↓    ↓               │  │
│  │  ┌────┐ ┌────┐ ┌────┐           │  │
│  │  │Prj1│ │Prj2│ │PrjN│           │  │
│  │  └────┘ └────┘ └────┘           │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### نظام المصادقة

**كل مشروع له:**
- `project_id` فريد (username-projectname)
- `password` آمن (يُولّد تلقائياً)

**كل طلب يحتاج:**
```json
{
  "project_id": "ahmad-myapp",
  "password": "X7k2Pm9qs4Rt",
  "cmd": "python3 --version"
}
```

---

## 🎯 الاستخدام

### 1. إنشاء مشروع جديد

#### في ChatGPT:
```
User: "أريد أنشئ مشروع FastAPI جديد اسمه myapi"

GPT → API: POST /projects/create
{
  "username": "ahmad",
  "project_name": "myapi",
  "project_type": "python"
}

API Response:
{
  "project_id": "ahmad-myapi",
  "password": "X7k2Pm9qs4Rt8vLn",
  "status": "ready"
}

GPT: "✅ تم إنشاء المشروع!
المشروع: ahmad-myapi
الباسورد: X7k2Pm9qs4Rt8vLn
⚠️ احفظ الباسورد، لن يظهر مرة أخرى!"
```

### 2. العمل على المشروع

```
User: "أنشئ API بسيط"

GPT → API: POST /exec
{
  "project_id": "ahmad-myapi",  # من الذاكرة
  "password": "X7k2Pm9qs4Rt",   # من الذاكرة
  "cmd": "pip install fastapi uvicorn"
}

GPT: "✅ تم تثبيت FastAPI"
```

### 3. العودة للمشروع (جلسة جديدة)

```
User: "أريد أكمل على مشروع myapi"

GPT: "ما هو معرف مشروعك؟"
User: "ahmad-myapi"

GPT: "ما هو الباسورد؟"
User: "X7k2Pm9qs4Rt"

GPT: "✅ تم التحقق! مرحباً بعودتك"
```

---

## 🔧 إعداد GPT Action

### في ChatGPT GPT Builder:

#### 1. Actions
```yaml
# استيراد الملف
openapi-spec-multitenant.yaml

# أو الرابط المباشر
http://95.217.62.146:9000/openapi.json
```

#### 2. Authentication
```
Type: API Key
Header: X-API-Key
Value: [من /opt/vibe-coding/config/.env]
```

#### 3. Instructions
```
# نسخ محتوى
GPT-INSTRUCTIONS-MULTITENANT.md
```

#### 4. اختبار
```
"تحقق من صحة النظام"
"أنشئ مشروع Python جديد"
```

---

## 🛠️ إدارة النظام

### أوامر سريعة:

```bash
# حالة النظام
vibe-status

# السجلات
vibe-logs
vibe-logs api      # سجلات API فقط

# إعادة تشغيل
vibe-restart

# إيقاف/تشغيل
vibe-stop
vibe-start

# تحديث
vibe-update

# التحقق من الصحة
curl http://localhost:9000/health
```

> **ملاحظة:** يتم ضبط هذه الأوامر تلقائياً على مسار التثبيت المحدد عبر `INSTALL_DIR` (الافتراضي `/opt/vibe-coding`).

### المجلدات الهامة:

```
/opt/vibe-coding/          # ملفات التثبيت (قيمة افتراضية يمكن تغييرها عبر `INSTALL_DIR`)
├── api/                   # كود API
├── project-manager/       # إدارة الحاويات
├── config/
│   └── .env              # المفاتيح الأمنية
└── docker-compose.yml

/var/lib/vibe-coding/      # البيانات
├── projects/             # مشاريع المستخدمين
├── databases/            # قواعد البيانات
└── logs/                 # السجلات
```

---

## 🔐 الأمان

### ما تم تطبيقه:

1. ✅ **عزل Docker كامل**
   - شبكة منفصلة تماماً
   - لا وصول للملفات الخارجية
   - Resource limits لكل مشروع

2. ✅ **API محلي فقط**
   - يعمل على 127.0.0.1
   - Firewall يمنع الوصول الخارجي
   - يحتاج master API key

3. ✅ **مصادقة لكل عملية**
   - project_id + password
   - لا exceptions
   - كل طلب مسجل

4. ✅ **حدود الموارد**
   - CPU: 2 cores لكل مشروع
   - Memory: 4GB لكل مشروع
   - Storage: 10GB لكل مشروع

### للمزيد من الأمان:

```bash
# تفعيل UFW (إن لم يكن مفعلاً)
ufw enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# السماح فقط لـ Plesk بالوصول للـ API
ufw allow from 127.0.0.1 to any port 9000
ufw deny 9000
```

---

## 📊 المراقبة

### مقاييس النظام:

```bash
# عدد المشاريع النشطة
docker ps | grep vibe-project | wc -l

# استهلاك الموارد
docker stats

# حجم البيانات
du -sh /var/lib/vibe-coding/projects

# السجلات الحديثة
tail -f /var/lib/vibe-coding/logs/api.log
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: API لا يستجيب

```bash
# فحص الحالة
vibe-status

# فحص السجلات
vibe-logs api

# إعادة التشغيل
vibe-restart
```

### المشكلة: خطأ في إنشاء مشروع

```bash
# فحص مساحة القرص
df -h

# فحص Docker
docker ps -a
docker images

# تنظيف
docker system prune -f
```

### المشكلة: بطء في التنفيذ

```bash
# فحص الموارد
docker stats

# فحص عدد المشاريع
docker ps | grep vibe-project | wc -l

# تنظيف المشاريع القديمة
# (يتم تلقائياً بعد 30 يوم)
```

---

## 📈 الترقية

### تحديث بسيط:

```bash
vibe-update
```

### تحديث يدوي:

```bash
cd /opt/vibe-coding
git pull origin main
docker compose build --no-cache
docker compose up -d
```

---

## 🎓 أمثلة عملية

### مثال 1: مشروع FastAPI كامل

```
User: "أريد أنشئ مشروع FastAPI مع PostgreSQL"

GPT:
1. إنشاء المشروع
2. تثبيت FastAPI + SQLAlchemy
3. إنشاء ملفات المشروع
4. إعداد قاعدة البيانات
5. تشغيل الخادم

النتيجة: API جاهز خلال دقائق
```

### مثال 2: مشروع React

```
User: "أنشئ تطبيق React"

GPT:
1. إنشاء مشروع Node.js
2. تثبيت Vite + React
3. إنشاء المكونات
4. تشغيل خادم التطوير

النتيجة: تطبيق React جاهز
```

### مثال 3: Laravel E-commerce

```
User: "أنشئ متجر إلكتروني بـ Laravel"

GPT:
1. إنشاء مشروع PHP + MySQL
2. تثبيت Laravel
3. إعداد قاعدة البيانات
4. إنشاء Models/Controllers
5. تشغيل الخادم

النتيجة: متجر Laravel جاهز
```

---

## 📞 الدعم

### الوثائق:
- `PLESK-DESIGN.md` - التصميم التفصيلي
- `install-plesk.sh` - سكريبت التثبيت
- `docker-compose.yml` - التكوين
- `api-main.py` - كود API
- `openapi-spec-multitenant.yaml` - مواصفات API
- `GPT-INSTRUCTIONS-MULTITENANT.md` - تعليمات GPT

### GitHub:
https://github.com/MarketingLimited/vibe-coding-platform

### المشاكل:
فتح Issue على GitHub

---

## ✅ الخلاصة

الآن لديك:

✅ نظام برمجة ذكي متكامل  
✅ عزل تام عن Plesk  
✅ أمان متعدد الطبقات  
✅ متعدد المستخدمين  
✅ تثبيت بأمر واحد  
✅ صفر مخاطر  

**جاهز للاستخدام الفوري!**

---

**تم التطوير بواسطة**: AlMoelef @ marketing.limited  
**التاريخ**: نوفمبر 2025  
**النسخة**: 2.0 - Plesk Edition  

**Happy Coding! 🚀**
