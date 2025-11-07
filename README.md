# Vibe Coding Platform

منصة تطوير متعددة المستأجرين تعتمد على Docker وتتكامل مع ChatGPT Actions لتوفير بيئات تطوير معزولة يتم التحكم بها بالكامل من خلال واجهة برمجية واحدة.

## 🎯 أبرز المزايا
- **API مركزي** مبني على FastAPI لإدارة المشاريع والمصادقة وتنفيذ الأوامر.
- **خدمة Project Manager** تدير الحاويات، قوالب المشاريع، وحدود الموارد.
- **خدمة Cleanup** للحفاظ على نظافة المسارات وإدارة السجلات القديمة بشكل دوري.
- **قوالب جاهزة** للغات Python وNode.js وPHP وبيئة كاملة متعددة الأدوات.
- **سكربت تثبيت واحد** يقوم بإعداد الشبكات، بناء الصور، وتشغيل الخدمات بالاعتماد على Docker Compose.

## 🏗️ نظرة على المعمارية
```
workspace/
├── api/                 # التطبيق المركزي (FastAPI)
│   └── app/
├── project-manager/     # خدمة إدارة الحاويات والقوالب
│   └── templates/
├── cleanup/             # خدمة التنظيف الدوري
├── projects/
│   └── templates/       # قوالب المشاريع الجاهزة
├── infra/               # ملفات البنية التحتية الإضافية
├── tools/               # سكربتات وأدوات مساعدة
├── docker-compose.yml   # تعريف الخدمات
└── install-plesk.sh     # سكربت التثبيت بنقرة واحدة
```
الخدمات تتصل ببعضها البعض عبر شبكة `vibe-network` وتخزن بياناتها المشتركة ضمن مجلدات `/projects` و`/logs` على المضيف.

## 🚀 التثبيت السريع
### المتطلبات
- نظام Ubuntu 24.04 مع وصول root.
- Docker 24+ و Docker Compose v2.
- منفذ داخلي متاح للـ API (افتراضي 9000).
- مساحة قرص لا تقل عن 20GB.

### التثبيت الآلي
```bash
curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-plesk.sh | sudo bash
```
يقوم السكربت بالمهام التالية:
1. التحقق من النظام وإعداد Docker.
2. إنشاء مجلد التثبيت `/opt/vibe-coding` ومجلد البيانات `/var/lib/vibe-coding`.
3. تنزيل المستودع، توليد مفاتيح الوصول، وإنشاء ملف `.env`.
4. بناء صور الخدمات (API، Project Manager، Cleanup، Redis).
5. تشغيل الخدمات عبر `docker compose up -d`.
6. إنشاء أوامر مساعدة مثل `vibe-status`, `vibe-logs`, `vibe-update`.

### التثبيت اليدوي (لبيئات التطوير)
```bash
git clone https://github.com/MarketingLimited/vibe-coding-platform.git
cd vibe-coding-platform
cp config/.env.example config/.env
cp config/.env .env
# عدّل القيم المناسبة داخل ملفات env ثم شغّل
docker compose up -d --build
```

## 🧩 مكونات النظام
### 1. Central API (`api/`)
- FastAPI مع هيكلية وحدات (`config`, `routers`, `services`).
- مصادقة عبر `X-API-Key` مع دعم تدوير كلمات مرور المشاريع.
- يعتمد على Redis لتخزين بيانات المشاريع وحالة الحاويات.
- يستدعي خدمة Project Manager لإنشاء/حذف الحاويات وتنفيذ الأوامر.

### 2. Project Manager (`project-manager/`)
- FastAPI داخلي يعمل على المنفذ 9400.
- يستخدم Docker SDK لإنشاء الحاويات بالاعتماد على صور `vibe-project-<type>`.
- ينسخ قالب المشروع الافتراضي من `projects/templates/default` عند إنشاء مشروع جديد.
- يوفر نقطة تنفيذ أوامر مع تحديد مسار العمل وحدود المخرجات.

### 3. Cleanup Service (`cleanup/`)
- سكربت Python دوري يفحص المجلدات والمسارات كل فترة (افتراضياً 24 ساعة).
- يحذف المشاريع غير النشطة استناداً إلى Redis وعمر الملفات.
- يحدد حجم ملفات السجلات لضمان عدم تضخمها.

### 4. Redis
- مخزن جلسات وبيانات مركزية للمشاريع والحالة التشغيلية.

## 🔌 تكامل ChatGPT Actions
1. استورد ملف `openapi-spec-multitenant.yaml` إلى GPT Builder.
2. استخدم `X-API-Key` المولد ضمن ملف `config/.env` للمصادقة.
3. مرر معرف المشروع وكلمة المرور عبر حقول الطلب لتنفيذ الأوامر.
4. راجع ملف `GPT-INSTRUCTIONS-MULTITENANT.md` للحصول على أفضل الممارسات حول إدارة الذاكرة وسير العمل.

## 📁 القوالب والصور
- مجلد `project-manager/templates/images` يحتوي Dockerfiles لبناء صور المشاريع (Python، Node.js، PHP، Full Stack).
- مجلد `projects/templates/default` يحتوي على `setup.sh` وملفات تعريفية يتم نسخها لكل مشروع جديد.

## 🛠️ أدوات المراقبة والإدارة
- `/var/lib/vibe-coding/logs` يجمع سجلات الخدمات الثلاثة.
- أوامر الإدارة التي ينشئها السكربت (`vibe-status`, `vibe-logs`, ...).
- نقطة `/health` في كل خدمة لمراقبة الحالة، بالإضافة إلى `/metadata` في الـ API للحصول على الحدود الحالية.

## ✅ الاختبارات الموصى بها بعد التثبيت
1. `curl http://localhost:9000/health` للتأكد من جاهزية الـ API.
2. إنشاء مشروع تجريبي عبر `POST /projects/create` ثم تنفيذ أمر عبر `/exec`.
3. التحقق من أن خدمة Project Manager تعيد الحالة عبر `curl http://localhost:9400/health` من داخل المضيف.

## 🤝 المساهمة
- افتح تذكرة جديدة لأي تحسين أو مشكلة.
- تأكد من تشغيل `docker compose build` بعد أي تعديل على الصور أو متطلبات الخدمات.
- أضف اختبارات أو لقطات من السجلات عند المساهمة في منطق إدارة المشاريع أو التنظيف.

