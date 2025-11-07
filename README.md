# Vibe Coding Platform

## 🎯 نظرة عامة

منصة تطوير متكاملة تمكّن GPT من العمل كمطور برمجي كامل عبر بيئات Docker معزولة. كل مشروع له بيئة مستقلة مع:

- ✅ **بيئة تطوير كاملة**: Python, Node.js, PHP, Go, Rust
- ✅ **قواعد بيانات**: PostgreSQL, MySQL, SQLite
- ✅ **Docker-in-Docker** عبر socket proxy آمن
- ✅ **VS Code في المتصفح** (code-server)
- ✅ **SSH معزول** لكل مشروع
- ✅ **كاش معرفي ذكي** لتقليل استهلاك التوكنز
- ✅ **مراقبة وسجلات** شاملة
- ✅ **نظام أمان متعدد الطبقات**

## 🏗️ المعمارية

```
kazaaz.com (Traefik + Let's Encrypt)
├── /code/<project>  → VS Code (code-server)
├── /api/<project>   → Exec API (FastAPI)
└── SSH:<port>       → SSH معزول

Projects Structure:
├── infra/
│   ├── traefik/          # Reverse proxy
│   ├── monitoring/       # Prometheus + Grafana
│   └── registry/         # Docker registry محلي
├── projects/
│   ├── template/         # قالب المشروع
│   └── <project-name>/   # مشاريع الإنتاج
└── tools/
    ├── new-project.sh    # إنشاء مشروع جديد
    ├── backup.sh         # النسخ الاحتياطي
    └── cleanup.sh        # التنظيف
```

## 🚀 التثبيت السريع

### المتطلبات
- Ubuntu 22.04 LTS أو أحدث
- Docker 24+ و Docker Compose v2
- 4GB RAM على الأقل (8GB موصى به)
- 20GB مساحة قرص حرة

### الخطوات

```bash
# 1. استنساخ المشروع
git clone https://github.com/your-org/vibe-coding-platform.git
cd vibe-coding-platform

# 2. تهيئة البيئة
./setup.sh

# 3. تشغيل Traefik
cd infra/traefik
docker compose up -d

# 4. إنشاء أول مشروع
./tools/new-project.sh myapp 22221

# 5. الوصول
# Code: https://kazaaz.com/code/myapp
# API:  https://kazaaz.com/api/myapp/exec
# SSH:  ssh dev@your-server -p 22221
```

## 📦 المكونات

### 1. Traefik (البوابة العكسية)
- TLS تلقائي عبر Let's Encrypt
- توجيه ديناميكي حسب المسارات
- معدل محدود للطلبات
- ضغط وتخزين مؤقت

### 2. DevBox (بيئة التطوير)
- أدوات كاملة للتطوير
- عزل كامل بين المشاريع
- نظام ملفات للقراءة فقط
- حدود الموارد (CPU/Memory)

### 3. Socket Proxy
- وصول آمن لـ Docker API
- قائمة بيضاء للعمليات
- تسجيل كامل للأنشطة

### 4. Exec API
- تنفيذ أوامر مع حدود زمنية
- قائمة بيضاء للأوامر
- تسجيل وتدقيق شامل
- حماية من الهجمات

### 5. Knowledge Cache
- تحليل ذكي للمشروع
- استخراج الوظائف والكلاسات
- مخطط قواعد البيانات
- تقليل استهلاك التوكنز

## 🔒 الأمان

- ✅ مستخدم غير جذر في جميع الحاويات
- ✅ نظام ملفات للقراءة فقط
- ✅ إسقاط جميع القدرات الخطرة
- ✅ عزل الشبكات بين المشاريع
- ✅ قوائم بيضاء للأوامر
- ✅ معدل محدود للطلبات
- ✅ مراقبة وتنبيهات
- ✅ تشفير SSL/TLS إلزامي
- ✅ مصادقة متعددة الطبقات

## 📊 المراقبة

```bash
# الوصول لـ Grafana
https://kazaaz.com/monitoring

# المقاييس المتوفرة:
- استخدام CPU/Memory لكل مشروع
- عدد الطلبات والأخطاء
- زمن الاستجابة
- استهلاك القرص
- سجلات الأنشطة
```

## 🔧 الإدارة

### إنشاء مشروع جديد
```bash
./tools/new-project.sh <name> <ssh-port> [options]

# مثال
./tools/new-project.sh ecommerce 22230 --with-postgres --with-redis
```

### النسخ الاحتياطي
```bash
./tools/backup.sh <project> [destination]

# نسخ احتياطي لجميع المشاريع
./tools/backup.sh --all /backup/location
```

### التنظيف
```bash
# حذف الملفات المؤقتة والحاويات القديمة
./tools/cleanup.sh

# حذف مشروع كامل
./tools/cleanup.sh --project myapp --confirm
```

## 🔌 التكامل مع GPT

### 1. إضافة Action في ChatGPT
انسخ ملف `openapi-spec.yaml` إلى إعدادات GPT Action

### 2. إضافة مفتاح المصادقة
```
Header: X-API-Key
Value: your-secure-api-key
```

### 3. تحديث Instructions
انسخ محتوى `gpt-instructions.md` إلى قسم Instructions

### 4. رفع Knowledge Base
ارفع `gpt-knowledge-base.md` في قسم Knowledge

## 📝 أمثلة الاستخدام

### مسح المشروع
```bash
curl -X POST https://kazaaz.com/api/myapp/exec \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "tree -L 2 -I \".git|node_modules\"",
    "cwd": "/workspace"
  }'
```

### تشغيل خادم تطوير React
```bash
curl -X POST https://kazaaz.com/api/myapp/exec \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "pnpm install && pnpm dev",
    "cwd": "/workspace/frontend"
  }'
```

### توليد الكاش المعرفي
```bash
curl -X POST https://kazaaz.com/api/myapp/exec \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "python3 /opt/tools/knowledge_cache.py",
    "cwd": "/workspace"
  }'
```

## 🎓 أفضل الممارسات

### للمطورين
1. استخدم الكاش المعرفي قبل أي تعديل
2. نفذ أوامر قصيرة ومحددة
3. راقب المخرجات والأخطاء
4. حدث الكاش بعد التغييرات الكبيرة

### للإدارة
1. نسخ احتياطي دوري (يومي)
2. مراقبة استهلاك الموارد
3. تحديث الصور الأساسية شهريًا
4. مراجعة السجلات أسبوعيًا

## 🐛 استكشاف الأخطاء

### المشروع لا يستجيب
```bash
# فحص حالة الحاويات
docker compose -f projects/myapp/docker-compose.yml ps

# فحص السجلات
docker compose -f projects/myapp/docker-compose.yml logs -f
```

### خطأ في المصادقة
```bash
# التحقق من مفتاح API
grep X-API-Key projects/myapp/.env

# إعادة توليد المفتاح
./tools/rotate-api-key.sh myapp
```

### نفاد المساحة
```bash
# تنظيف Docker
docker system prune -af --volumes

# تنظيف السجلات القديمة
./tools/cleanup-logs.sh --older-than 30d
```

## 📚 الوثائق الإضافية

- [دليل المطورين](docs/developer-guide.md)
- [دليل الإدارة](docs/admin-guide.md)
- [مرجع API](docs/api-reference.md)
- [أسئلة شائعة](docs/faq.md)

## 🤝 المساهمة

نرحب بالمساهمات! يرجى قراءة [دليل المساهمة](CONTRIBUTING.md)

## 📄 الترخيص

MIT License - انظر [LICENSE](LICENSE)

## 📞 الدعم

- 📧 Email: support@kazaaz.com
- 💬 Discord: [رابط الخادم]
- 📖 Wiki: [رابط الويكي]

## 🙏 شكر خاص

- Traefik لنظام التوجيه الرائع
- Code-Server لـ VS Code في المتصفح
- FastAPI لـ API السريع والموثوق
