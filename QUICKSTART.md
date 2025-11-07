# دليل البدء السريع - Vibe Coding Platform

## 🚀 التثبيت في 5 دقائق

### المتطلبات الأساسية
```bash
# تأكد من توفر Docker و Docker Compose
docker --version  # يجب 24.0+
docker compose version  # يجب v2.20+
```

### الخطوة 1: التثبيت الأولي
```bash
# استنسخ المشروع (أو فك الضغط)
cd vibe-coding-platform

# تشغيل سكريبت التثبيت
sudo ./setup.sh --domain kazaaz.com --email admin@kazaaz.com
```

### الخطوة 2: إنشاء أول مشروع
```bash
# مشروع بسيط بدون قواعد بيانات
./tools/new-project.sh demo 22221

# مشروع مع PostgreSQL و Redis
./tools/new-project.sh myapp 22230 --with-postgres --with-redis

# مشروع Laravel مع MySQL
./tools/new-project.sh shop 22240 --with-mysql
```

### الخطوة 3: الوصول للمشروع

**Via Web:**
- Code Server: `https://kazaaz.com/code/demo`
- API Docs: `https://kazaaz.com/api/demo/docs`

**Via SSH:**
```bash
ssh dev@your-server -p 22221
# كلمة المرور في: projects/demo/.env
```

## 🔧 إعداد GPT Action

### 1. في ChatGPT GPT Builder

**قسم Actions:**
1. انسخ محتوى `openapi-spec.yaml`
2. استبدل `{domain}` و `{project}` بقيمك
3. احفظ

**قسم Authentication:**
- Type: `API Key`
- Header: `X-API-Key`
- Value: (من ملف `.env` للمشروع)

**قسم Instructions:**
- انسخ محتوى `gpt-instructions.md`

### 2. اختبار الاتصال

في ChatGPT، جرّب:
```
"تحقق من البيئة وعرض الأدوات المتاحة"
"أنشئ مشروع Python بسيط واختبره"
```

## 📚 الأوامر الأساسية

### إدارة المشاريع

```bash
# عرض المشاريع
docker ps --filter "label=project"

# سجلات مشروع معين
docker compose -f projects/myapp/docker-compose.yml logs -f

# إيقاف مشروع
docker compose -f projects/myapp/docker-compose.yml stop

# إعادة تشغيل
docker compose -f projects/myapp/docker-compose.yml restart

# حذف مشروع (حذر!)
docker compose -f projects/myapp/docker-compose.yml down -v
rm -rf projects/myapp
```

### الدخول للحاوية

```bash
# دخول shell
docker exec -it myapp_devbox bash

# تنفيذ أمر واحد
docker exec myapp_devbox python3 --version
```

### النسخ الاحتياطي

```bash
# نسخ احتياطي لمشروع
tar -czf myapp-backup-$(date +%Y%m%d).tar.gz projects/myapp/workspace

# استعادة
tar -xzf myapp-backup-20241107.tar.gz -C projects/myapp/
```

## 🔍 استكشاف الأخطاء

### المشروع لا يبدأ

```bash
# فحص السجلات
docker compose -f projects/myapp/docker-compose.yml logs

# فحص حالة الحاويات
docker compose -f projects/myapp/docker-compose.yml ps

# إعادة البناء
docker compose -f projects/myapp/docker-compose.yml up --build -d
```

### خطأ في المنفذ

```bash
# تحقق من المنافذ المستخدمة
ss -tlnp | grep :22221

# غيّر المنفذ في .env
nano projects/myapp/.env
# SSH_PORT=22222

# أعد التشغيل
docker compose -f projects/myapp/docker-compose.yml up -d
```

### نفاد المساحة

```bash
# تنظيف Docker
docker system prune -af --volumes

# حذف الصور غير المستخدمة
docker image prune -a

# فحص المساحة
df -h
du -sh projects/*/workspace
```

### مشاكل SSL/TLS

```bash
# التحقق من Traefik
docker logs traefik

# إعادة توليد الشهادات
rm infra/traefik/letsencrypt/acme.json
docker compose -f infra/traefik/docker-compose.yml restart
```

## 🎯 أمثلة عملية

### مشروع FastAPI

```bash
# إنشاء المشروع
./tools/new-project.sh api-demo 22221 --with-postgres

# دخول الحاوية
docker exec -it api-demo_devbox bash

# إنشاء التطبيق
cd /workspace
cat > main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
EOF

# تشغيل
uvicorn main:app --host 0.0.0.0 --port 8080
```

### مشروع React

```bash
# إنشاء المشروع
./tools/new-project.sh frontend 22230

# دخول الحاوية
docker exec -it frontend_devbox bash

# إنشاء React app
cd /workspace
pnpm create vite my-app --template react
cd my-app
pnpm install
pnpm dev
```

### مشروع Laravel

```bash
# إنشاء المشروع
./tools/new-project.sh webapp 22240 --with-mysql

# دخول الحاوية
docker exec -it webapp_devbox bash

# إنشاء Laravel
cd /workspace
composer create-project laravel/laravel .
php artisan key:generate

# تهيئة قاعدة البيانات
php artisan migrate
php artisan serve --host 0.0.0.0 --port 8080
```

## 📊 المراقبة

### الوصول لـ Grafana
```
URL: https://kazaaz.com/grafana
كلمة المرور: في infra/monitoring/.env
```

### المقاييس المتاحة
- استخدام CPU/Memory لكل مشروع
- عدد الطلبات والأخطاء
- أوقات الاستجابة
- حالة الحاويات

## 🔐 الأمان

### أفضل الممارسات

1. **غيّر كلمات المرور الافتراضية**
```bash
# لكل مشروع
nano projects/myapp/.env
# غيّر API_KEY, CODE_SERVER_PASSWORD, SSH_PASSWORD
```

2. **فعّل Firewall**
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

3. **استخدم SSH Keys بدل كلمات المرور**
```bash
# في الحاوية
cat ~/.ssh/id_rsa.pub >> /home/dev/.ssh/authorized_keys

# في sshd_config
PasswordAuthentication no
```

4. **راجع السجلات بانتظام**
```bash
# سجلات Traefik
tail -f infra/traefik/logs/traefik.log

# سجلات المشاريع
tail -f projects/*/workspace/.logs/*.log
```

## 📞 الدعم

- **الوثائق**: `docs/` folder
- **الأمثلة**: `examples/` folder
- **Issues**: GitHub Issues
- **Email**: admin@kazaaz.com

## ⚡ نصائح سريعة

```bash
# عرض جميع المشاريع النشطة
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# استهلاك الموارد
docker stats

# تحديث صورة مشروع
docker compose -f projects/myapp/docker-compose.yml pull
docker compose -f projects/myapp/docker-compose.yml up -d

# إنشاء alias مفيد
alias vibe-logs='docker compose -f projects/$(basename $PWD)/docker-compose.yml logs -f'
alias vibe-shell='docker exec -it $(basename $PWD)_devbox bash'
```

---

**مبروك! أنت الآن جاهز لاستخدام Vibe Coding Platform 🎉**
