# Vibe Coding Platform

منصة تطوير متعددة المستأجرين تعتمد على Docker وتتكامل مع ChatGPT Actions لتوفير بيئات تطوير معزولة يتم التحكم بها بالكامل من خلال واجهة برمجية واحدة.

## 🎯 أبرز المزايا
- **API مركزي** مبني على FastAPI لإدارة المشاريع والمصادقة وتنفيذ الأوامر.
- **خدمة Project Manager** تدير الحاويات، قوالب المشاريع، وحدود الموارد.
- **خدمة Cleanup** للحفاظ على نظافة المسارات وإدارة السجلات القديمة بشكل دوري.
- **طبقة بيانات دائمة** تحفظ بيانات المشاريع في SQLite مع مزامنة فورية إلى Redis.
- **مراقبة خلفية** لحاويات المشاريع وتحديث حالة الحاويات في Redis بشكل آلي.
- **سجلات تدقيق ومؤشرات مراقبة** تلتقط كل طلب عبر ملف `logs/audit.log` وتكشف `/metrics`
  لصالح Prometheus.
- **قوالب جاهزة** للغات Python وNode.js وPHP وبيئة كاملة متعددة الأدوات.
- **سكربت تثبيت واحد** يقوم بإعداد الشبكات، بناء الصور، وتشغيل الخدمات بالاعتماد على Docker Compose.
- **سكربت تفعيل تفاعلي** (`tools/setup/activate.sh`) يولّد ملفات البيئة ويشغّل الخدمات بخطوات إرشادية واضحة.
- **حماية من الإساءة** بفضل محددات معدل طلبات لكل مشروع ولكل عمليات إدارية، قابلة للضبط عبر المتغيرات البيئية.

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
├── install.sh           # سكربت التثبيت العام لأنظمة Linux
└── install-plesk.sh     # سكربت تثبيت متوافق مع خوادم Plesk
```
الخدمات تتصل ببعضها البعض عبر شبكة `vibe-network` وتخزن بياناتها المشتركة ضمن مجلدات `/projects` و`/logs` على المضيف.

## 🚀 التثبيت السريع
### المتطلبات المشتركة
- نظام Linux بواجهة سطر أوامر مع صلاحيات `root` (Debian/Ubuntu أو Rocky/AlmaLinux مدعومة رسمياً).
- اتصال إنترنت للوصول إلى GitHub وملفات Docker.
- Docker 24+ و Docker Compose v2 (يتم تثبيتهما تلقائياً إذا لم يكونا متوفرين).
- منفذ داخلي متاح للـ API (افتراضي 9000) ومساحة قرص لا تقل عن 20GB.

### المسار العام (موصى به لمعظم الخوادم)
```bash
curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install.sh | sudo bash
```
- يدعم Debian/Ubuntu و Rocky/AlmaLinux تلقائياً، ويتعرف على مدير الحزم المناسب.
- يمكن تجربة الخطوات بدون تنفيذ تغييرات عبر `--dry-run` للتحقق من التوزيعة والمتطلبات.
- خيارات إضافية: `--skip-firewall` لتعطيل ضبط UFW، و `--skip-systemd` في حال عدم توفر systemd.

### مسار Plesk الاختياري
```bash
curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-plesk.sh | sudo bash
```
- يحافظ على نفس خطوات التثبيت مع فحص اختياري لوجود Plesk.
- يمكن استخدام `--dry-run` للتأكد من توافق الخادم قبل التنفيذ.

كلا المسارين يقومان بالمهام التالية:
1. التحقق من النظام وإعداد Docker (عند الحاجة).
2. إنشاء مجلد التثبيت `/opt/vibe-coding` ومجلد البيانات `/var/lib/vibe-coding`.
3. تنزيل المستودع، توليد مفاتيح الوصول، وإنشاء ملف `.env` (يتضمن مفتاح تشفير GitHub سري يتم حفظه في `/data/github-secrets.bin`).
4. بناء صور الخدمات (API، Project Manager، Cleanup، Redis) ثم تشغيل سكربت `tools/build-project-images.sh` لبناء صور المشاريع الأساسية (`vibe-project-<type>`).
5. تشغيل الخدمات عبر `docker compose up -d`.
6. إنشاء أوامر مساعدة مثل `vibe-status`, `vibe-logs`, `vibe-update`.

### التثبيت اليدوي (لبيئات التطوير)
```bash
git clone https://github.com/MarketingLimited/vibe-coding-platform.git
cd vibe-coding-platform
bash tools/setup/activate.sh
```

سيقوم السكربت التفاعلي بتجهيز ملفات البيئة (`.env` و`config/.env`) وتوليد المفاتيح الافتراضية
بما في ذلك مفتاح تشفير أسرار GitHub، ثم ينشئ شبكة `vibe-network` إن لم تكن موجودة ويستدعي
`tools/build-project-images.sh` لضمان توفر صور المشاريع قبل تشغيل الخدمات مباشرة عبر `docker compose` بخطوة واحدة.

## 🧩 مكونات النظام
### 1. Central API (`api/`)
- FastAPI مع هيكلية وحدات (`config`, `routers`, `services`).
- مصادقة عبر `X-API-Key` مع دعم تدوير كلمات مرور المشاريع.
- يعتمد على Redis وSQLite (`/data/projects.db`) لتخزين بيانات المشاريع وحالة الحاويات.
- يستدعي خدمة Project Manager لإنشاء/حذف الحاويات وتنفيذ الأوامر.
- يتضمن نقاط `/health` و`/health/services` لرصد Redis، SQLite، Docker، وخدمة Project Manager بالإضافة إلى حدود المعدل الحالية، مع نقطة `/metrics` لالتقاط مؤشرات Prometheus.
- طبقة Rate Limiter مبنية على Redis للتحكم في إنشاء المشاريع، الاستعلام، والتشغيل لكل مشروع.
- يخزن مفاتيح GitHub الشخصية داخل ملف مشفر (`GITHUB_SECRETS_PATH`) ولا يبدأ الخدمة إذا لم يتم توليد `GITHUB_SECRETS_KEY`.

### 2. Project Manager (`project-manager/`)
- FastAPI داخلي يعمل على المنفذ 9400.
- يستخدم Docker SDK لإنشاء الحاويات بالاعتماد على صور `vibe-project-<type>`.
- ينسخ قالب المشروع الافتراضي من `projects/templates/default` عند إنشاء مشروع جديد.
- يوفر نقطة تنفيذ أوامر مع تحديد مسار العمل وحدود المخرجات.
- يدفع تحديثات الحالة إلى Redis ويشغّل حلقة مراقبة تضبط حالة كل حاوية بشكل دوري (قابلة للضبط عبر `HEALTH_POLL_INTERVAL`).
- يولّد عنوان المعاينة الحية لكل مشروع ويُخزّنه في Redis ليتم عرضه عبر الـ API.

### 3. Cleanup Service (`cleanup/`)
- سكربت Python دوري يفحص المجلدات والمسارات كل فترة (افتراضياً 24 ساعة).
- يحذف المشاريع غير النشطة بعد التحقق من الحالة في Redis وSQLite لضمان عدم حذف مشروع يعمل.
- يحدد حجم ملفات السجلات لضمان عدم تضخمها.
- يحسب استهلاك التخزين ويرسل تقرير JSON اختياري إلى Webhook عبر `NOTIFICATION_WEBHOOK`.

### 4. Redis
- مخزن جلسات وبيانات مركزية للمشاريع والحالة التشغيلية.

## 🔌 تكامل ChatGPT Actions
1. استورد ملف `openapi-spec-multitenant.yaml` إلى GPT Builder.
2. استخدم `X-API-Key` المولد ضمن ملف `config/.env` للمصادقة.
3. مرر معرف المشروع وكلمة المرور عبر حقول الطلب لتنفيذ الأوامر.
4. راجع ملف `GPT-INSTRUCTIONS-MULTITENANT.md` للحصول على أفضل الممارسات حول إدارة الذاكرة وسير العمل.

## 📁 القوالب والصور
- مجلد `project-manager/templates/images` يحتوي Dockerfiles لبناء صور المشاريع (Python، Node.js، PHP، Full Stack)، ويمكن إعادة بنائها دفعة واحدة عبر `tools/build-project-images.sh` (يدعم خيارات `--prefix` و`--tag`).
- مجلد `projects/templates/default` يحتوي على `setup.sh` وملفات تعريفية يتم نسخها لكل مشروع جديد.

## 🛠️ أدوات المراقبة والإدارة
- `/var/lib/vibe-coding/logs` يجمع سجلات الخدمات الثلاثة، ويتضمن الآن ملف `audit.log` لجميع الطلبات.
- أوامر الإدارة التي ينشئها السكربت (`vibe-status`, `vibe-logs`, ...) بالإضافة إلى سكربتات `tools/vibe-status.sh` و`tools/vibe-backup.sh` للاستخدام اليدوي.
- نقاط `/health` و`/health/services` في الـ API للاطمئنان على Redis، قاعدة البيانات، Docker، وخدمة Project Manager، بالإضافة إلى `/metadata` للحصول على الحدود الحالية، وحلقة مراقبة Project Manager لتحديث الحالة كل بضع ثوانٍ.
- مجلد `infra/monitoring/` يحتوي حزمة Prometheus/Grafana اختيارية لمراقبة المنصة وتشغيلها بجوار الخدمات الأساسية.

## 🌐 معاينة التطبيقات (Live Preview)
- خدمة Traefik الجديدة (`edge-proxy`) تقع تحت `infra/edge/` ويتم تشغيلها تلقائياً مع بقية الخدمات عبر `docker compose`.
- لدعم TLS على النطاق الفرعي `*.kazaaz.com`، ضع ملفات الشهادة `wildcard.kazaaz.com.crt` و`wildcard.kazaaz.com.key` داخل مجلد `${DATA_DIR}/certs` قبل تشغيل المنصة.
- يقوم Project Manager بربط كل حاوية مشروع بالشبكة `vibe-proxy` ويولّد عنوان المعاينة `https://<project-id>.kazaaz.com` تلقائياً، ويمكن تغيير النطاق باستخدام المتغير `PREVIEW_DOMAIN`.
- يمكن تخصيص المنافذ ونقاط الدخول عبر المتغيرات البيئية (`PREVIEW_INTERNAL_PORT`, `PREVIEW_ENTRYPOINTS`, `PREVIEW_SERVICE_SCHEME`) بما يتناسب مع الصور الخاصة بك.
- تمت إضافة ملفات `infra/edge/traefik.yml` و`infra/edge/dynamic/certificates.yml` كبداية آمنة يمكن توسيعها لإضافة رؤوس أمان أو نطاقات إضافية عند الحاجة.
- يعرض الـ API رابط المعاينة `preview_url` ضمن ردود `/projects/create`, `/projects/info`, و`/projects/{username}` لتسهيل مشاركة الرابط مباشرة مع المستخدم أو GPT.

## ✅ الاختبارات الموصى بها بعد التثبيت
1. `curl http://localhost:9000/health` للتأكد من جاهزية الـ API.
2. `curl http://localhost:9000/health/services` للحصول على حالة المكونات الداخلية وحدود المعدل.
3. إنشاء مشروع تجريبي عبر `POST /projects/create` ثم تنفيذ أمر عبر `/exec`.
4. التحقق من أن خدمة Project Manager تعيد الحالة عبر `curl http://localhost:9400/health` من داخل المضيف.
5. تشغيل `pytest` من جذر المستودع للتحقق من محددات المعدل، مستودع المشاريع، ومنطق خدمة التنظيف.

## 🤝 المساهمة
- افتح تذكرة جديدة لأي تحسين أو مشكلة.
- تأكد من تشغيل `docker compose build` بعد أي تعديل على الصور أو متطلبات الخدمات.
- أضف اختبارات أو لقطات من السجلات عند المساهمة في منطق إدارة المشاريع أو التنظيف.

