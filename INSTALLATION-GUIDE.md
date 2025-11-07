# 📘 دليل التثبيت والاستخدام - Vibe Coding Platform

يوضح هذا الدليل كيفية نشر المنصة وتشغيلها خطوة بخطوة بعد إعادة هيكلتها إلى خدمات مستقلة.

## 1. المتطلبات المسبقة
- نظام Ubuntu 24.04 مع صلاحيات `sudo`.
- Docker 24+ و Docker Compose v2 (يتم تثبيتهما تلقائياً عند استخدام السكربت).
- منفذ داخلي متاح للـ API (`9000`) ومنفذ داخلي لخدمة Project Manager (`9400`).
- مساحة تخزين لا تقل عن 20GB مع 4GB RAM على الأقل.

## 2. التثبيت الآلي
```bash
curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-plesk.sh | sudo bash
```
### ماذا يفعل السكربت؟
1. يتحقق من نظام التشغيل، Docker، و Plesk (إن وجد).
2. ينشئ المجلدات:
   - `/opt/vibe-coding` للتطبيقات.
   - `/var/lib/vibe-coding` للبيانات (`projects`, `logs`).
3. يستنسخ المستودع ويولّد ملفي `.env` (`config/.env` و `.env`).
4. ينشئ شبكة `vibe-network` إذا لم تكن موجودة.
5. يبني الصور (`api`, `project-manager`, `cleanup`) ويشغّل `docker compose up -d`.
6. يضيف أوامر مساعدة (`vibe-status`, `vibe-logs`, `vibe-update`, ...).

## 3. التثبيت اليدوي (لبيئات التطوير)
```bash
git clone https://github.com/MarketingLimited/vibe-coding-platform.git
cd vibe-coding-platform
cp config/.env.example config/.env
cp config/.env .env
# حدّث القيم المناسبة ثم شغّل
redis_password=... # إن رغبت في إعداد مخصص
API_KEY=...        # مفتاح الواجهة البرمجية
sed -i "s/change-me/${API_KEY}/" config/.env

# تشغيل الخدمات
docker compose up -d --build
```
> ملاحظة: تأكد من إنشاء شبكة `vibe-network` في حال لم تكن موجودة: `docker network create vibe-network`.

## 4. التحقق بعد التثبيت
- `curl http://localhost:9000/health` → صحة Central API.
- `curl http://localhost:9400/health` → صحة Project Manager (من نفس الخادم).
- `docker compose ps` → التأكد من أن جميع الحاويات في حالة `Up`.
- `docker compose logs -f api` → مراجعة السجلات في حال وجود مشكلة.

## 5. إنشاء مشروع تجريبي
```bash
# باستخدام واجهة API (مع مفتاح الإدارة)
curl -X POST http://localhost:9000/projects/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <MASTER_API_KEY>" \
  -d '{
        "username": "demo",
        "project_name": "sample",
        "project_type": "python"
      }'
```
الاستجابة ستحتوي على `project_id` و`password`. استخدمها للوصول للمشروع عبر `/projects/info` أو لتنفيذ الأوامر عبر `/exec`.

## 6. مسارات العمل الأساسية
1. **إنشاء مشروع** → `POST /projects/create` (يتطلب `X-API-Key`).
2. **الحصول على معلومات المشروع** → `POST /projects/info` (باستخدام `project_id` + كلمة المرور).
3. **تنفيذ أوامر** → `POST /exec` (الأمر يمر عبر Project Manager).
4. **حذف مشروع** → `DELETE /projects/delete` (إما بالمفتاح الرئيسي أو كلمة مرور المشروع).
5. **تدوير كلمة المرور** → `POST /projects/rotate-password`.

## 7. إعداد ChatGPT Action
1. افتح GPT Builder واختر Actions.
2. استورد `openapi-spec-multitenant.yaml`.
3. أدخل `X-API-Key` المخزن في `config/.env`.
4. الصق تعليمات `GPT-INSTRUCTIONS-MULTITENANT.md` في قسم التعليمات.
5. اختبر: "أنشئ مشروع Python جديد" ثم قم بتنفيذ أمر داخل المشروع عبر `/exec`.

## 8. الصيانة الدورية
- **vibe-update**: يسحب آخر التحديثات من GitHub ويعيد بناء الصور.
- **vibe-logs**: يعرض سجلات جميع الخدمات.
- **vibe-status**: يبيّن حالة الحاويات.
- **Cleanup service**: تعمل تلقائياً كل 24 ساعة. يمكن تعديل الفترة عبر `CLEANUP_INTERVAL` داخل `.env`.

## 9. استكشاف الأخطاء
| المشكلة | الفحص | الحل |
|---------|-------|------|
| API لا يستجيب | `docker compose logs api` | تأكد من صحة إعدادات Redis ووجود `API_KEY` في `.env` |
| Project Manager يفشل في إنشاء الحاوية | `docker compose logs project-manager` | تأكد من وجود صور `vibe-project-*` أو قم ببنائها من `project-manager/templates/images` |
| الأوامر لا تعمل | تحقق من `POST /projects/info` | تأكد من صحة كلمة المرور وحالة الحاوية |
| Cleanup يحذف مشروعاً نشطاً | تحقق من Redis (`project:<id>`) | عدّل قيمة `MAX_PROJECT_AGE_DAYS` أو حدّث حالة المشروع إلى `active` |

## 10. تحديث الصور أو القوالب
- لتعديل قوالب المشاريع: عدّل الملفات داخل `projects/templates/default` ثم أعد بناء صورة المشروع إذا لزم.
- لتحديث صور اللغات: حدّث Dockerfiles داخل `project-manager/templates/images` ثم شغّل `docker build -t vibe-project-python:latest project-manager/templates/images/python` (مع استبدال الاسم عند الحاجة).

باتباع هذه الخطوات يتم نشر المنصة وتشغيلها مع البنية الجديدة المتوافقة مع خطة GPT Actions.

