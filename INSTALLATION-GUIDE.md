# 📘 دليل استخدام Vibe Coding Platform - النسخة الاحترافية

## 🎉 ما تم إنجازه

تم بناء منصة **Vibe Coding Platform v2.0** بشكل احترافي ومتكامل مع التحسينات التالية:

### ✨ التحسينات الرئيسية

#### 1. **معمارية محسّنة**
- Multi-stage Dockerfile لتقليل حجم الصورة
- Docker Compose محسّن مع profiles
- شبكات معزولة لكل مشروع
- Socket proxy للأمان

#### 2. **أمان متقدم**
- مصادقة متعددة الطبقات (API Key + Rate Limiting)
- قوائم بيضاء للأوامر المسموحة
- اكتشاف الأنماط الخطرة
- نظام ملفات للقراءة فقط
- إسقاط جميع الـ capabilities

#### 3. **مراقبة شاملة**
- Prometheus + Grafana
- Health checks تلقائية
- سجلات منظمة
- مقاييس الأداء

#### 4. **أتمتة كاملة**
- سكريبت setup.sh للتثبيت الأولي
- سكريبت new-project.sh لإنشاء المشاريع
- توليد أسرار تلقائي
- تهيئة خدمات اختيارية (PostgreSQL/MySQL/Redis)

## 📦 محتويات الأرشيف

```
vibe-coding-platform/
├── README.md                  # نظرة عامة شاملة
├── QUICKSTART.md             # دليل البدء السريع
├── SUMMARY.md                # الخلاصة التنفيذية
├── setup.sh                  # سكريبت التثبيت الأولي
├── openapi-spec.yaml         # OpenAPI spec لـ GPT Action
├── gpt-instructions.md       # تعليمات GPT
│
├── projects/
│   └── template/             # قالب المشروع
│       ├── Dockerfile        # صورة محسّنة متعددة المراحل
│       ├── docker-compose.yml # تكوين شامل مع profiles
│       ├── entrypoint.sh     # إدارة متقدمة للخدمات
│       ├── runner/
│       │   ├── app.py        # FastAPI محسّن
│       │   └── requirements.txt
│       └── tools/
│           └── (knowledge cache scripts)
│
└── tools/
    └── new-project.sh        # سكريبت إنشاء المشاريع
```

## 🚀 خطوات التشغيل

### 1. فك الضغط والإعداد

```bash
# فك ضغط الأرشيف
tar -xzf vibe-coding-platform.tar.gz
cd vibe-coding-platform

# جعل السكريبتات قابلة للتنفيذ (تم بالفعل)
chmod +x setup.sh tools/*.sh projects/template/entrypoint.sh
```

### 2. التثبيت على السيرفر

```bash
# تثبيت أساسي
sudo ./setup.sh

# أو تثبيت متقدم
sudo ./setup.sh \
  --domain kazaaz.com \
  --email admin@kazaaz.com \
  --with-registry
```

**ملاحظة**: سيقوم السكريبت بـ:
- ✅ فحص المتطلبات (Docker, Docker Compose)
- ✅ إنشاء البنية الأساسية
- ✅ تكوين Traefik مع Let's Encrypt
- ✅ إعداد نظام المراقبة (اختياري)
- ✅ إنشاء الشبكات والـvolumes
- ✅ بدء الخدمات الأساسية

### 3. إنشاء أول مشروع

```bash
# مشروع بسيط
./tools/new-project.sh demo 22221

# مشروع مع PostgreSQL و Redis
./tools/new-project.sh myapp 22230 --with-postgres --with-redis

# مشروع Laravel مع MySQL
./tools/new-project.sh shop 22240 --with-mysql --domain kazaaz.com
```

**النتيجة**: المشروع جاهز مع:
- ✅ حاوية DevBox كاملة
- ✅ VS Code في المتصفح
- ✅ Exec API للأوامر
- ✅ SSH معزول
- ✅ قواعد بيانات (إن طُلبت)
- ✅ أسرار مولّدة تلقائيًا

### 4. الوصول للمشروع

**عبر المتصفح:**
```
Code Server: https://kazaaz.com/code/demo
API Docs:    https://kazaaz.com/api/demo/docs
Monitoring:  https://kazaaz.com/grafana
```

**عبر SSH:**
```bash
ssh dev@your-server-ip -p 22221
# كلمة المرور في: projects/demo/.credentials
```

### 5. إعداد GPT Action

#### في ChatGPT GPT Builder:

**A. قسم Actions:**
1. افتح ملف `openapi-spec.yaml`
2. استبدل المتغيرات:
   - `{domain}` → `kazaaz.com`
   - `{project}` → `demo` (أو اسم مشروعك)
3. انسخ والصق في GPT Builder
4. احفظ

**B. قسم Authentication:**
```
Type: API Key
Auth Type: Custom
Header Name: X-API-Key
Value: [من ملف .env أو .credentials]
```

**C. قسم Instructions:**
1. افتح `gpt-instructions.md`
2. انسخ المحتوى بالكامل
3. الصق في Instructions
4. احفظ

**D. اختبار:**
في ChatGPT، جرّب:
```
"تحقق من البيئة وعرض الأدوات المتاحة"
"أنشئ مشروع Python بسيط مع FastAPI"
"شغّل خادم تطوير وعرض معلوماته"
```

## 🔧 الإدارة اليومية

### عرض المشاريع النشطة
```bash
docker ps --filter "label=project" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### السجلات
```bash
# سجلات مشروع معين
docker compose -f projects/demo/docker-compose.yml logs -f

# سجلات Traefik
docker logs traefik -f

# سجلات داخل الحاوية
docker exec demo_devbox tail -f /workspace/.logs/api.log
```

### إعادة التشغيل
```bash
# مشروع واحد
docker compose -f projects/demo/docker-compose.yml restart

# جميع المشاريع
for project in projects/*/docker-compose.yml; do
  docker compose -f "$project" restart
done
```

### النسخ الاحتياطي
```bash
# نسخ مشروع واحد
tar -czf backup-demo-$(date +%Y%m%d).tar.gz projects/demo/workspace

# نسخ جميع المشاريع
tar -czf backup-all-$(date +%Y%m%d).tar.gz projects/*/workspace
```

## 🎯 أمثلة عملية

### مثال 1: API بسيط مع FastAPI

```bash
# إنشاء المشروع
./tools/new-project.sh api-demo 22221 --with-postgres

# في ChatGPT GPT:
"أنشئ API بسيط باستخدام FastAPI مع endpoint للمصادقة"
"أضف PostgreSQL ORM باستخدام SQLAlchemy"
"أنشئ ملف اختبارات باستخدام pytest"
"شغّل الخادم وعرض الـ API docs"
```

### مثال 2: تطبيق React

```bash
# إنشاء المشروع
./tools/new-project.sh frontend 22230

# في ChatGPT GPT:
"أنشئ تطبيق React باستخدام Vite"
"أضف routing باستخدام React Router"
"أنشئ صفحة login بسيطة"
"شغّل خادم التطوير"
```

### مثال 3: Laravel E-commerce

```bash
# إنشاء المشروع
./tools/new-project.sh shop 22240 --with-mysql --with-redis

# في ChatGPT GPT:
"أنشئ مشروع Laravel جديد"
"أضف نظام مصادقة مع Sanctum"
"أنشئ models للمنتجات والطلبات"
"أعد ترحيلات قاعدة البيانات"
"شغّل الخادم"
```

## 🔍 استكشاف المشاكل

### المشروع لا يبدأ
```bash
# فحص الحالة
docker compose -f projects/demo/docker-compose.yml ps

# فحص السجلات
docker compose -f projects/demo/docker-compose.yml logs

# إعادة البناء
docker compose -f projects/demo/docker-compose.yml up --build -d
```

### خطأ في المنفذ
```bash
# تحقق من المنافذ المستخدمة
ss -tlnp | grep :22221

# غيّر المنفذ
nano projects/demo/.env
# SSH_PORT=22222

docker compose -f projects/demo/docker-compose.yml up -d
```

### مشاكل SSL
```bash
# تحقق من Traefik
docker logs traefik | grep -i error

# أعد توليد الشهادات
rm infra/traefik/letsencrypt/acme.json
docker compose -f infra/traefik/docker-compose.yml restart
```

### نفاد المساحة
```bash
# تنظيف Docker
docker system prune -af --volumes

# حذف السجلات القديمة
find projects/*/workspace/.logs -name "*.log" -mtime +30 -delete
```

## 📊 المراقبة

### الوصول لـ Grafana
```
URL: https://kazaaz.com/grafana
Username: admin
Password: [من infra/monitoring/.env]
```

### Dashboards الافتراضية
- نظرة عامة على النظام
- أداء المشاريع
- استخدام الموارد
- الطلبات والأخطاء

## 🔐 توصيات الأمان

1. **غيّر كلمات المرور الافتراضية فورًا**
2. **فعّل Firewall**
3. **استخدم SSH Keys بدل كلمات المرور**
4. **راجع السجلات بانتظام**
5. **حدّث الصور شهريًا**
6. **نسخ احتياطي دوري**

## 📞 الدعم والموارد

- **الوثائق الكاملة**: انظر مجلد `docs/`
- **الأمثلة**: انظر مجلد `examples/`
- **المشاكل**: GitHub Issues
- **البريد**: admin@kazaaz.com

## 🎓 موارد إضافية

### الوثائق الرسمية
- [Docker Documentation](https://docs.docker.com/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Code-Server Documentation](https://coder.com/docs/code-server/)

### دروس فيديو (قريبًا)
- التثبيت الأولي
- إنشاء أول مشروع
- التكامل مع GPT
- نصائح الأمان

---

## ✅ الخلاصة

لديك الآن منصة تطوير احترافية كاملة تمكّن GPT من العمل كمطور برمجي حقيقي مع:

✅ بيئة تطوير متكاملة  
✅ أمان متعدد الطبقات  
✅ عزل كامل بين المشاريع  
✅ مراقبة شاملة  
✅ أتمتة كاملة  
✅ سهولة في الاستخدام  

**ابدأ الآن وبناء مشاريع رائعة! 🚀**

---

**تم البناء بواسطة**: AlMoelef @ marketing.limited  
**التاريخ**: نوفمبر 2025  
**النسخة**: 2.0 Professional
