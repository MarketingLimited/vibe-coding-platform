# البنية التقنية - Vibe Coding Platform

## نظرة عامة
تعتمد المنصة على معمارية خدمات مصغرة (Microservices) واضحة الحدود، وتدار بالكامل عبر Docker Compose. يتم عزل كل طبقة وظيفية داخل حاوية مستقلة مع تبادل بيانات محدود عبر Redis ومجلدات مشتركة.

## المكونات الرئيسية
### 1. Central API (FastAPI)
- مسؤول عن المصادقة باستخدام `X-API-Key` وبيانات اعتماد المشاريع.
- يوفر مسارات `/projects/*` لإدارة المشاريع و`/exec` لتنفيذ الأوامر عبر Project Manager.
- يعتمد على Redis لتخزين بيانات المشاريع، كلمات المرور المجمعة، وحالة الحاويات.
- يحتفظ بطبقة إعدادات (`app/config.py`) تقرأ جميع المتغيرات من `.env`.
- يسجل جميع الطلبات مع معرف `request_id` لتسهيل التتبع عبر السجلات.

### 2. Project Manager
- خدمة FastAPI داخلية تعمل على المنفذ 9400 داخل الشبكة المغلقة.
- تبني الحاويات من صور `vibe-project-<type>` وتربطها بالشبكة `vibe-network`.
- تنسخ قالب المشروع الافتراضي من `projects/templates/default` عند إنشاء مشروع جديد لضمان توفر هيكل أساسي.
- تتعامل مع Docker SDK مباشرةً مع إسقاط الامتيازات في الحاوية (بدون `--privileged`).
- تعرّف واجهات داخلية فقط (`/internal/projects`, `/internal/projects/{id}/exec`).

### 3. Cleanup Service
- سكربت Python دوري يقوم بـ:
  - حذف المشاريع غير النشطة بناءً على حالة Redis وعمر المجلد.
  - تقليص ملفات السجلات التي تتجاوز الحجم المحدد.
  - تعديل صلاحيات المجلدات الحساسة لضمان الأمان.
- يتحكم به المتغير `CLEANUP_INTERVAL` (بالثواني) ويعمل ضمن نفس شبكة الخدمات.

### 4. Redis
- خادم Redis 7 يعمل كذاكرة مركزية.
- يحتفظ بمفاتيح على شكل `project:<project_id>` لتخزين بيانات المشروع، و`user:<username>:projects` لقوائم المشاريع.
- يستخدم من قبل كلٍ من Central API وCleanup service.

## تدفق إنشاء مشروع جديد
1. يرسل العميل طلب `POST /projects/create` مع `X-API-Key`.
2. يقوم Central API بالتحقق من الحد الأعلى للمشاريع لكل مستخدم وتوليد كلمة مرور جديدة.
3. يستدعي API خدمة Project Manager (`POST /internal/projects`).
4. Project Manager ينشئ المجلد، ينسخ القالب، ينشئ الحاوية، ويعيد `container_id`.
5. يتم تخزين بيانات المشروع في Redis مع حالة "active" وإرجاع كلمة المرور لمرة واحدة للعميل.

## تدفق تنفيذ أمر
1. العميل يرسل `POST /exec` مع `project_id` و`password`.
2. API يتحقق من صحة كلمة المرور عبر Redis.
3. يتم تمرير الأمر لخدمة Project Manager (`/internal/projects/{id}/exec`).
4. Project Manager ينفذ الأمر داخل الحاوية عبر `docker exec` مع `bash -lc`، ويعيد الناتج بعد تطبيق حدود الحجم.
5. API يعيد الاستجابة للعميل على شكل `ExecResponse` موحد.

## المجلدات المشتركة والقيود الأمنية
- `/projects`: يحتوي جميع مساحات العمل. يتم ربطه بنمط قراءة/كتابة للحاويات الخاصة بالمشاريع فقط.
- `/logs`: مجلد مركزي لسجلات الخدمات؛ يمكن مراقبته من المضيف أو عبر أدوات خارجية.
- جميع الحاويات تعمل مع `no-new-privileges` وتستخدم شبكة Docker خاصة (`vibe-network`) مع عدم نشر المنافذ للخارج باستثناء الـ API (المقيد على `127.0.0.1`).

## مراقبة الصحة
- `/health` في Central API: يتحقق من Redis وDocker.
- `/health` في Project Manager: يتحقق من اتصال Docker.
- Cleanup لا يملك HTTP API، لكنه يسجل دورة التشغيل في `/logs/cleanup.log` (عبر docker logs).

## خريطة البيانات في Redis
```
project:<id> → {
  project_id,
  username,
  project_name,
  project_type,
  database,
  redis,
  password_hash,
  container_id,
  created_at,
  status
}
user:<username>:projects → Set(project_id, ...)
```

## الشبكات والحاويات في Docker Compose
- **vibe-network**: شبكة خارجية يتم إنشاؤها مسبقاً عبر السكربت.
- **الحاويات**:
  - `vibe-api`: التطبيق المركزي.
  - `vibe-project-manager`: إدارة الحاويات.
  - `vibe-cleanup`: خدمة التنظيف الخلفية.
  - `vibe-redis`: التخزين المركزي.

## اعتبارات الأمان المستقبلية
- دمج Proxy أمام الـ API (Traefik أو Nginx) لمراقبة معدلات الطلب وتقديم TLS.
- إضافة نظام مراقبة (Prometheus/Grafana) داخل مجلد `infra/` لاستكمال الصورة التشغيلية.
- توحيد سجلات JSON ودمجها مع منصة SIEM خارجية عند الحاجة.

