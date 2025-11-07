# Vibe Coding Platform - Plesk Compatible Version

## 🎯 التصميم الجديد

### المشاكل المحلولة
1. ✅ عزل تام عن Plesk والمواقع
2. ✅ API واحد مشترك لجميع المشاريع
3. ✅ نظام مصادقة بـ project_id + password
4. ✅ تثبيت بأمر واحد بسيط
5. ✅ أمان كامل للسيرفر

## 📐 المعمارية الجديدة

```
┌─────────────────────────────────────────────────────┐
│                   Plesk Server                      │
│  ┌──────────────────────────────────────────────┐  │
│  │          Existing Websites & Apps            │  │
│  └──────────────────────────────────────────────┘  │
│                        ↕                            │
│  ┌──────────────────────────────────────────────┐  │
│  │         Docker Network (isolated)            │  │
│  │  ┌────────────────────────────────────────┐  │  │
│  │  │    Vibe Coding Central API             │  │  │
│  │  │    Port: 9000 (internal only)          │  │  │
│  │  │    Endpoint: /api/exec                 │  │  │
│  │  └────────────────────────────────────────┘  │  │
│  │                    ↕                          │  │
│  │  ┌─────────┬─────────┬─────────┬─────────┐  │  │
│  │  │Project 1│Project 2│Project 3│Project N│  │  │
│  │  │ (user1) │ (user2) │ (user3) │ (userN) │  │  │
│  │  └─────────┴─────────┴─────────┴─────────┘  │  │
│  └──────────────────────────────────────────────┘  │
│                        ↕                            │
│            Traefik/Nginx (Plesk)                   │
└─────────────────────────────────────────────────────┘
                         ↕
                    Internet
              (only via Plesk proxy)
```

## 🔑 نظام المصادقة الجديد

### كل طلب يحتاج:
```json
{
  "project_id": "user123-myproject",
  "password": "secure_project_password",
  "cmd": "python3 --version",
  "cwd": "/workspace"
}
```

### GPT يحفظ في الذاكرة:
- project_id الخاص بالمستخدم
- password للمشروع
- يستخدمهم في كل طلب تلقائياً

## 🚀 التثبيت بأمر واحد

```bash
curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-plesk.sh | sudo bash
```

أو يدوياً:
```bash
git clone https://github.com/MarketingLimited/vibe-coding-platform.git
cd vibe-coding-platform
sudo ./install-plesk.sh
```

## 📝 ملفات النظام الجديد

```
vibe-coding-platform/
├── install-plesk.sh          # تثبيت بأمر واحد
├── docker-compose.yml        # API مركزي + مدير المشاريع
├── api/
│   ├── main.py              # FastAPI مع multi-tenant
│   ├── auth.py              # نظام المصادقة
│   ├── projects.py          # إدارة المشاريع
│   └── requirements.txt
├── project-manager/
│   ├── manager.py           # إدارة حاويات المشاريع
│   └── templates/           # قوالب المشاريع
└── config/
    ├── projects.db          # قاعدة بيانات المشاريع
    └── traefik.yml          # تكوين Traefik (إن لزم)
```

## 🔒 الأمان

### العزل
1. شبكة Docker منفصلة تماماً
2. لا وصول مباشر للإنترنت (داخلي فقط)
3. API يعمل على localhost:9000
4. Plesk يعمل كـ reverse proxy

### الصلاحيات
- كل مشروع له مستخدم منفصل
- Read-only filesystem
- Resource limits صارمة
- No access to host system

## 📊 تدفق العمل

### 1. المستخدم الجديد
```
User → ChatGPT
  ↓
"أريد إنشاء مشروع جديد"
  ↓
GPT → API: POST /projects/create
  Body: {
    "username": "ahmad",
    "project_name": "myapp",
    "type": "python",  // python/nodejs/php
    "database": "postgres"  // optional
  }
  ↓
Response: {
    "project_id": "ahmad-myapp",
    "password": "auto_generated_secure_pass",
    "status": "ready",
    "workspace": "/projects/ahmad-myapp"
}
  ↓
GPT saves to memory:
  - project_id
  - password
```

### 2. العمل على المشروع
```
User → ChatGPT
  ↓
"شغّل خادم FastAPI"
  ↓
GPT → API: POST /exec
  Body: {
    "project_id": "ahmad-myapp",
    "password": "saved_password",
    "cmd": "uvicorn main:app --host 0.0.0.0"
  }
  ↓
Executes in project container
```

### 3. العودة للمشروع
```
User → ChatGPT (new session)
  ↓
"أريد أكمل على مشروعي ahmad-myapp"
  ↓
GPT: "ما هو الباسورد؟"
  ↓
User: "secure_password"
  ↓
GPT verifies → API: POST /auth/verify
  ↓
If valid → continues work
```

## 🛠️ API Endpoints

```
POST /projects/create
  - إنشاء مشروع جديد
  - يولد password تلقائياً
  - ينشئ حاوية معزولة

POST /projects/list
  - عرض مشاريع المستخدم
  - يحتاج username فقط

POST /auth/verify
  - التحقق من project_id + password

POST /exec
  - تنفيذ أمر في المشروع
  - يحتاج project_id + password

POST /projects/delete
  - حذف مشروع
  - يحتاج project_id + password

GET /health
  - حالة النظام
```

## 📋 مثال استخدام كامل

### في ChatGPT:

```
User: "أريد أنشئ مشروع FastAPI جديد اسمه blog"

GPT: سأنشئ لك المشروع الآن...
[يستدعي POST /projects/create]

GPT: ✅ تم إنشاء المشروع بنجاح!
- المشروع: yourusername-blog
- الباسورد: X7k2Pm9qs4Rt
- احفظ الباسورد لاستخدامه لاحقاً

User: "أنشئ API بسيط"

GPT: [ينفذ الأوامر في المشروع]
✅ تم إنشاء main.py
✅ تم تثبيت FastAPI
✅ الخادم يعمل على المنفذ 8000

User: [جلسة جديدة في اليوم التالي]
"أريد أكمل على مشروع blog"

GPT: "من فضلك أدخل باسورد المشروع"

User: "X7k2Pm9qs4Rt"

GPT: ✅ تم التحقق، يمكنك المتابعة
```

## ⚙️ التكوين في Plesk

### إضافة Reverse Proxy (اختياري)
في Plesk → Apache & Nginx Settings:

```nginx
location /vibe-api {
    proxy_pass http://127.0.0.1:9000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### أو استخدام مباشر من GPT
```
Server: http://95.217.62.146:9000
(يجب تأمين المنفذ بـ firewall)
```

## 🔥 Firewall Rules

```bash
# السماح فقط لـ Cloudflare/Specific IPs
ufw allow from 95.217.62.146 to any port 9000
ufw allow from your_office_ip to any port 9000
ufw deny 9000
```

## 🎯 المميزات

1. ✅ **عزل تام**: Docker منفصل تماماً عن Plesk
2. ✅ **API واحد**: سهولة الإدارة
3. ✅ **Multi-tenant**: آلاف المستخدمين
4. ✅ **آمن**: password لكل مشروع
5. ✅ **بسيط**: تثبيت بأمر واحد
6. ✅ **لا مخاطر**: صفر تأثير على Plesk

## 📈 Scalability

- يدعم مئات المشاريع
- Auto-cleanup للمشاريع القديمة
- Resource quotas لكل مشروع
- Monitoring مدمج

---

الآن سأبدأ بإنشاء الملفات المطلوبة...
