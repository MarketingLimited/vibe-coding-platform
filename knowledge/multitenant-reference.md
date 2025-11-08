# Multi-Tenant Knowledge Base — Reference Flows

يوفر هذا الملف أمثلة مطولة، قوالب طلبات، وخطوات تحقق تفصيلية مكملة لـ `GPT-INSTRUCTIONS-MULTITENANT.md`.

## فحص الاتصال بالـ API
```bash
curl -fsSL "$API_PUBLIC_BASE_URL/health"
```
- إذا فشل الأمر، تحقق من أن القيم التالية مضبوطة ومنشورة: `API_PUBLISH_MODE`, `API_TRAEFIK_ENABLE`, `API_PUBLIC_BASE_URL`.
- يمكن للمشغل مراجعة إعدادات Traefik أو الجدار الناري للتأكد من السماح بالمنفذ.

## تدفق إنشاء مشروع جديد
```text
User: "أريد أنشئ مشروع FastAPI جديد"
You:
 1. ما اسم المستخدم الخاص بك؟
 2. ما اسم المشروع الذي تريده؟
 3. ما اللغة أو القالب المطلوب (project_type/project_template)؟
 4. ما هو GitHub API key الخاص بك؟
 5. هل لديك أسرار إضافية لتخزينها (key/value)؟
 6. أعيد صياغة العناصر المكتملة واطلب تأكيد المستخدم.
 7. استدعِ POST /projects/create بالبيانات المؤكدة.
 8. احفظ `project_id` و `password` في الذاكرة الآمنة.
 9. شارك النتائج مع المستخدم (بما في ذلك `preview_url`)، وذكّره بحفظ كلمة المرور.
```

### مثال طلب إنشاء مكتمل
```json
{
  "username": "user123",
  "project_name": "fastapi-blog",
  "project_type": "python",
  "project_template": "fastapi/basic",
  "github_api_key": "ghp_xxxxxxxxxxxxxxxxxxxxx",
  "additional_secrets": {
    "openai_api_key": "sk-xxxxx",
    "slack_webhook": "https://hooks.slack.com/..."
  },
  "database": "postgres",
  "redis": true
}
```

## التحقق بعد الإنشاء
1. اطلب `/projects/info` باستخدام `project_id` و`password` للتأكد من أن الحالة `running` أو `ready`.
2. إذا كانت الحالة `pending` أو `deploying`، أعلم المستخدم بانتظار عدة لحظات وأعد التحقق.
3. شارك `preview_url` حال توفره، واذكر إن كانت هناك أي خطوات إضافية مطلوبة للتنشيط.

## تشغيل الأوامر على مشروع قائم
```json
{
  "project_id": "ahmad-myapi",
  "password": "saved_in_memory",
  "cmd": "python3 --version"
}
```
- التزم بأوامر واضحة ومحددة.
- للأوامر طويلة المدى استخدم `nohup` أو عمليات بالخلفية مع حفظ السجلات ضمن `/workspace/.logs` داخل المشروع.
- إذا فشل الأمر بسبب كلمة مرور خاطئة أو فقدان الجلسة، اطلب بيانات الاعتماد مرة أخرى قبل إعادة المحاولة.

## العودة لمشروع قديم
```text
User: "أريد أكمل على مشروع myapi"
You:
 1. أتحقق من الذاكرة الحالية.
 2. إذا لم أجد `project_id`: "ما هو معرف مشروعك الكامل؟ (مثال: username-myapi)"
 3. إذا لم أجد كلمة المرور: "ما هو باسورد المشروع؟"
 4. أحفظ البيانات المحدثة فورًا للاستخدام المستقبلي.
```

## تحديث `last_cwd`
- بعد تنفيذ أوامر مثل `cd services/api`, حدّث الذاكرة لتخزين المجلد الحالي.
- عند استقبال أمر جديد من المستخدم، استخدم `last_cwd` لضمان أن الأمر يعمل في المسار الصحيح.

## معالجة الأخطاء الشائعة
- **401 Unauthorized:** تحقق من كلمة المرور؛ اطلب من المستخدم إدخالها مرة أخرى.
- **404 Not Found:** تأكد من أن `project_id` صحيح، أو استخدم `/projects/list` إذا كان متاحًا للمستخدم.
- **Timeout أو اتصال مرفوض:** أبلغ المستخدم بمراجعة حالة Traefik والجدار الناري، وأعد محاولة فحص `/health`.

## قالب ملخص جلسة جيد
```text
- المشروع: username-myapi
- آخر أمر: pip install fastapi uvicorn sqlalchemy
- النتيجة: ✅ اكتمل التثبيت، تم تحديث last_cwd إلى /workspace/services/api
- التوصيات: تشغيل pytest للتأكد من سلامة الاعتماديات الجديدة
```
