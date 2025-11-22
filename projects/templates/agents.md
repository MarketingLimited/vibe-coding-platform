# Project Templates - دليل الـAgent

## Purpose

مجلد **projects/templates/** يحتوي على:
- **Default Template**: القالب الافتراضي الذي يُنسخ لكل مشروع جديد
- **Workspace Initialization**: الملفات والإعدادات الأساسية لبيئة التطوير
- **Git Repository Setup**: هيكل Git repository جاهز
- **Development Tools**: أدوات وscripts مساعدة للمطورين

عند إنشاء مشروع جديد، يقوم **Project Manager** بنسخ محتويات `/templates/default` إلى workspace المشروع.

---

## Owned Scope

### Default Template Directory
- `/projects/templates/default/` - القالب الافتراضي
  - `.git/` - Git repository initialized
  - `.gitignore` - Git ignore rules
  - `README.md` - Project documentation template
  - `.env.example` - Environment variables template
  - `tools/` - Helper scripts for developers
  - (Additional files based on project type)

### Runtime Workspaces
- `/projects/{project_id}/` - Project workspaces (created at runtime)
  - كل مشروع يحصل على نسخة من default template
  - تُربط كـvolume mount إلى container بـ`/workspace`

---

## Key Files & Entry Points

### Default Template Structure

```
/projects/templates/default/
│
├── .git/                       # Initialized Git repository
│   ├── config
│   ├── HEAD
│   └── ...
│
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
├── .env.example                # Environment variables template
│
├── tools/                      # Development helper scripts
│   ├── run.sh                  # Quick start script
│   ├── test.sh                 # Run tests
│   └── deploy.sh               # Deployment script
│
└── docs/                       # Additional documentation
    └── GETTING_STARTED.md
```

### .gitignore Template

```gitignore
# /projects/templates/default/.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Environment
.env
.env.local
*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Build artifacts
dist/
build/
*.egg-info/
```

### README.md Template

```markdown
# /projects/templates/default/README.md

# Project Name

> Created with Vibe Coding Platform

## 📋 Description

[Add your project description here]

## 🚀 Quick Start

```bash
# Install dependencies
npm install  # or: pip install -r requirements.txt

# Run development server
npm run dev  # or: python app.py
```

## 🧪 Testing

```bash
# Run tests
bash tools/test.sh
```

## 📦 Project Structure

```
.
├── src/           # Source code
├── tests/         # Test files
├── tools/         # Helper scripts
└── docs/          # Documentation
```

## 🔧 Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

## 📝 License

[Your license here]
```

### .env.example Template

```bash
# /projects/templates/default/.env.example

# Application
APP_NAME=my-project
APP_ENV=development
DEBUG=true

# Server
PORT=8000
HOST=0.0.0.0

# Database (if enabled)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Redis (if enabled)
REDIS_URL=redis://localhost:6379/0

# API Keys
# Add your API keys here
```

### Helper Scripts

```bash
# /projects/templates/default/tools/run.sh
#!/bin/bash

echo "🚀 Starting development server..."

# Detect project type and run appropriate command
if [ -f "package.json" ]; then
    npm run dev
elif [ -f "requirements.txt" ]; then
    python app.py
elif [ -f "composer.json" ]; then
    php -S localhost:8000
else
    echo "❌ Unknown project type"
    exit 1
fi
```

```bash
# /projects/templates/default/tools/test.sh
#!/bin/bash

echo "🧪 Running tests..."

if [ -f "package.json" ]; then
    npm test
elif [ -f "requirements.txt" ]; then
    pytest
elif [ -f "composer.json" ]; then
    ./vendor/bin/phpunit
else
    echo "❌ No tests configured"
    exit 1
fi
```

---

## Dependencies & Interfaces

### Template Usage Flow

```
Project Creation Request
    ↓
Project Manager receives request
    ↓
1. Create workspace directory
   /projects/{username}-{project_name}/
    ↓
2. Copy default template
   cp -r /templates/default/* /projects/{project_id}/
    ↓
3. Initialize Git (if not already)
   git init /projects/{project_id}/
    ↓
4. Create Docker container
   Mount: /projects/{project_id} → /workspace (in container)
    ↓
5. Developer accesses files via:
   - Container shell: /workspace/
   - Host filesystem: /projects/{project_id}/
```

**Files**:
- Template source: `/projects/templates/default/`
- Copy logic: `/project-manager/app/services/__init__.py:_copy_template()`

### Container Integration

```
Container Filesystem
    │
    ├─ /workspace/              # Mount point (from host)
    │   ├─ .git/                # Version control
    │   ├─ .gitignore
    │   ├─ README.md
    │   ├─ .env (created by user)
    │   ├─ tools/
    │   └─ (user code)
    │
    └─ /home/coder/             # Container user home
        └─ .config/gh/          # GitHub CLI config (synced by SecretSync)
```

---

## Local Rules / Patterns

### 1. Template Copying Pattern

```python
# /project-manager/app/services/__init__.py
def _copy_template(self, workspace_path: str):
    """
    Copy default template to new project workspace
    """
    template_dir = settings.TEMPLATES_DIR  # /templates/default

    if os.path.exists(template_dir):
        shutil.copytree(
            template_dir,
            workspace_path,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                '*.pyc',
                '__pycache__',
                '.DS_Store',
                'node_modules'
            )
        )

        # Set permissions
        os.chmod(workspace_path, 0o755)
```

### 2. Git Initialization

```python
def _initialize_git(self, workspace_path: str):
    """
    Initialize git repository if not already initialized
    """
    git_dir = os.path.join(workspace_path, '.git')

    if not os.path.exists(git_dir):
        # Initialize repo
        subprocess.run(['git', 'init'], cwd=workspace_path, check=True)

        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=workspace_path)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit from Vibe template'],
            cwd=workspace_path
        )
```

### 3. Project Type-Specific Files

يمكن إضافة ملفات خاصة بنوع المشروع:

```python
def _add_project_type_files(self, workspace_path: str, project_type: str):
    """
    Add type-specific starter files
    """
    if project_type == 'python':
        # Create requirements.txt
        with open(f"{workspace_path}/requirements.txt", 'w') as f:
            f.write("# Python dependencies\n")
            f.write("fastapi==0.110.0\n")
            f.write("uvicorn[standard]==0.29.0\n")

        # Create main.py
        with open(f"{workspace_path}/app.py", 'w') as f:
            f.write("from fastapi import FastAPI\n\n")
            f.write("app = FastAPI()\n\n")
            f.write("@app.get('/')\n")
            f.write("def read_root():\n")
            f.write("    return {'message': 'Hello from Vibe!'}\n")

    elif project_type == 'nodejs':
        # Create package.json
        with open(f"{workspace_path}/package.json", 'w') as f:
            json.dump({
                "name": "vibe-project",
                "version": "1.0.0",
                "scripts": {
                    "dev": "node index.js"
                }
            }, f, indent=2)

        # Create index.js
        with open(f"{workspace_path}/index.js", 'w') as f:
            f.write("console.log('Hello from Vibe!');\n")
```

---

## How to Run / Test

### Viewing Default Template

```bash
# List template contents
ls -la /home/user/vibe-coding-platform/projects/templates/default/

# View specific file
cat /home/user/vibe-coding-platform/projects/templates/default/README.md
```

### Testing Template Copy

```bash
# Manual test
mkdir -p /tmp/test-workspace
cp -r /home/user/vibe-coding-platform/projects/templates/default/* /tmp/test-workspace/

# Verify
ls -la /tmp/test-workspace/
```

### Creating Test Project

```bash
# Create project via API
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "project_name": "template-test",
    "project_type": "python",
    "github_api_key": "ghp_test",
    "database": "none",
    "redis": false
  }'

# Verify workspace created
ls -la /srv/vibe/projects/testuser-template-test/

# Should contain:
# - .git/
# - .gitignore
# - README.md
# - .env.example
# - tools/
```

### Testing Helper Scripts

```bash
# Enter project container
docker exec -it vibe-testuser-template-test /bin/bash

# Inside container
cd /workspace

# Test run script
bash tools/run.sh

# Test test script
bash tools/test.sh
```

---

## Common Tasks for Agents

### مهمة: تعديل Default Template

**Example**: Add Docker support files to template

1. **Create Dockerfile** في `/projects/templates/default/`:
```dockerfile
# /projects/templates/default/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Create docker-compose.yml**:
```yaml
# /projects/templates/default/docker-compose.yml
version: '3.9'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DEBUG=true
```

3. **Update .gitignore**:
```gitignore
# Docker
docker-compose.override.yml
```

4. **Test**: Create new project و verify files copied

### مهمة: Add project type-specific templates

**Approach 1**: Separate template directories

```
/projects/templates/
├── default/          # Base template
├── python/           # Python-specific additions
├── nodejs/           # Node.js-specific additions
└── php/              # PHP-specific additions
```

**Copy logic**:
```python
def _copy_template(self, workspace_path: str, project_type: str):
    # Copy base template
    shutil.copytree('/templates/default', workspace_path, dirs_exist_ok=True)

    # Copy type-specific files (if exist)
    type_template = f'/templates/{project_type}'
    if os.path.exists(type_template):
        shutil.copytree(type_template, workspace_path, dirs_exist_ok=True)
```

**Approach 2**: Dynamic file generation (current approach)

في `_add_project_type_files()` method

### مهمة: Add .editorconfig

```ini
# /projects/templates/default/.editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{py,js,ts,json}]
indent_style = space
indent_size = 4

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
```

### مهمة: Add Makefile للـcommon tasks

```makefile
# /projects/templates/default/Makefile
.PHONY: install run test clean

install:
	@echo "Installing dependencies..."
	@if [ -f "package.json" ]; then npm install; fi
	@if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi

run:
	@bash tools/run.sh

test:
	@bash tools/test.sh

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf __pycache__ node_modules dist build *.egg-info
```

### مهمة: Debug template not copying

**Checklist**:

1. **Check template directory exists**:
```bash
ls -la /home/user/vibe-coding-platform/projects/templates/default/
```

2. **Check Project Manager config**:
```bash
docker exec vibe-project-manager env | grep TEMPLATES_DIR
# Should be: TEMPLATES_DIR=/templates/default
```

3. **Check volume mount** في docker-compose.yml:
```yaml
project-manager:
  volumes:
    - ./projects:/projects
    - ./projects/templates:/templates  # ← Must be mounted
```

4. **Check permissions**:
```bash
ls -la /home/user/vibe-coding-platform/projects/templates/
# Should be readable by docker user
```

5. **Manual test**:
```bash
docker exec vibe-project-manager ls -la /templates/default/
# Should show template files
```

6. **Check copy logic** في logs:
```bash
docker logs vibe-project-manager | grep -i template
```

---

## Notes / Gotchas

### ⚠️ Template Updates Don't Affect Existing Projects

- تعديلات على `/templates/default` تؤثر فقط على **المشاريع الجديدة**
- المشاريع الموجودة **لا تتحدث** تلقائياً
- للupdate: يجب manual copy أو migration script

### ⚠️ Git Initialization Timing

- `.git/` directory في template قد يُسبب مشاكل
- **Best practice**: Initialize Git **بعد** copy template
- Remove `.git/` من template و initialize في `_prepare_workspace()`

### ⚠️ File Permissions

- Template files يجب أن تكون readable (644)
- Scripts في `tools/` يجب أن تكون executable (755)
- Set permissions:
  ```bash
  chmod 644 /projects/templates/default/*
  chmod 755 /projects/templates/default/tools/*.sh
  ```

### ⚠️ Hidden Files

- `shutil.copytree` **ينسخ** hidden files (مثل `.gitignore`)
- لتخطي معين: use `ignore` parameter
  ```python
  shutil.copytree(
      src, dst,
      ignore=shutil.ignore_patterns('.git', '.env')
  )
  ```

### ⚠️ Large Template Size

- Template كبير = slower project creation
- Keep template **minimal**
- Avoid:
  - `node_modules/`
  - Large binaries
  - Generated files

### ⚠️ .env vs .env.example

- **Never** commit `.env` (contains secrets)
- Template يحتوي `.env.example` فقط
- Users ينشئون `.env` بنفسهم:
  ```bash
  cp .env.example .env
  ```

### ⚠️ Cross-Platform Compatibility

- Line endings: use LF (Unix), not CRLF (Windows)
- Set في `.gitattributes`:
  ```
  * text=auto eol=lf
  *.sh text eol=lf
  ```

### ⚠️ Template Versioning

- لا يوجد version control للtemplates حالياً
- Recommendation: Add `TEMPLATE_VERSION` file:
  ```
  # /projects/templates/default/TEMPLATE_VERSION
  1.0.0
  ```

- Track changes:
  ```bash
  git log -- projects/templates/default/
  ```

### ⚠️ Container User Ownership

- Files copied من template owned by root في container
- Fix ownership:
  ```python
  def _fix_ownership(self, workspace_path: str, container_id: str):
      """Change ownership to container user (coder:1000)"""
      container = self.docker_client.containers.get(container_id)
      container.exec_run(['chown', '-R', 'coder:coder', '/workspace'])
  ```

### ⚠️ Symlinks in Template

- `shutil.copytree` بشكل افتراضي **لا ينسخ** symlinks (يحولها لملفات)
- للحفاظ على symlinks:
  ```python
  shutil.copytree(src, dst, symlinks=True)
  ```

### ⚠️ Template Conflicts with Project Type

- Python project قد لا يحتاج `package.json`
- Node.js project قد لا يحتاج `requirements.txt`
- **Solution**: Keep template generic، add type-specific files dynamically
