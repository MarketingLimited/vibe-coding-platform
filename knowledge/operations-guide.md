# Vibe Coding Knowledge Base — Operations Guide

هذا الملف يجمع الأمثلة الموسعة والجداول المرجعية المذكورة في `gpt-instructions.md`. استخدمه عند الحاجة لخطوات تفصيلية أو أوامر جاهزة.

## مسح سريع للمشروع
```bash
# عرض البنية المختصرة (تجاهل المجلدات الثقيلة)
tree -L 3 -I ".git|node_modules|.venv"

# أحدث التعديلات
git log --oneline -10
ls -lt | head -20
```

## أوامر Python / FastAPI
```bash
# تهيئة بيئة افتراضية
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# تشغيل التطبيق
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# الاختبارات
pytest -v
```

## أوامر Node.js / React
```bash
# تثبيت الاعتماديات
pnpm install

# تطوير محلي
pnpm dev

# بناء الإنتاج
pnpm build

# الاختبارات
npm test
```

## أوامر PHP / Laravel
```bash
# تثبيت الاعتماديات
composer install

# تشغيل الترقيات
php artisan migrate

# تشغيل الخادم
php artisan serve --host 0.0.0.0 --port 8080
```

## قواعد بيانات شائعة
**PostgreSQL**
```bash
psql -h $PGHOST -U $PGUSER -d $PGDATABASE
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "SELECT * FROM users LIMIT 5;"
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "\\dt"
```

**MySQL**
```bash
mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE -e "SHOW TABLES;"
```

**SQLite**
```bash
sqlite3 data/app.db ".tables"
sqlite3 data/app.db "SELECT * FROM users LIMIT 5;"
```

## Docker
```bash
docker compose up -d
docker compose logs -f
docker compose down
```

## أمثلة تواصل فعّال
```text
✅ "سأبحث أولاً عن وظائف المصادقة الموجودة..."
✅ "التنفيذ نجح، تم تثبيت 42 حزمة"
✅ "حدث خطأ: Module not found. سأتحقق من requirements.txt..."

❌ "تم"
❌ "حدث خطأ ما"
❌ "جرّب هذا الأمر: [أمر عشوائي]"
```

## حفظ السجلات وتتبع الأوامر الطويلة
```bash
command 2>&1 | tee /workspace/.logs/output.log
ls -lh /workspace/.logs/
tail -n 100 /workspace/.logs/api.log
```

## اختبار قبل الإطلاق
```bash
pytest -v --tb=short
flake8 . || ruff check .
npm test
phpunit
```

## تدفق عمل نموذجي لمهمة ميزة جديدة
```text
1. استكشف البنية وابحث عن الوظائف المشابهة (`tree`, `rg`).
2. اقرأ الأجزاء الملائمة من الملفات بدلاً من الملف بالكامل (`head`, `sed`).
3. حدّث الكاش المعرفي إذا تغيرت البنية.
4. نفّذ التعديلات وراجع diff.
5. شغّل الاختبارات، واجمع المخرجات المهمة للملخص النهائي.
```
