# Project Templates

Default templates and scaffolding for new projects on the VIBE Coding Platform.

## Overview

Templates provide a starting point for new projects, including:
- Project documentation
- Git configuration
- Setup scripts
- Development tools
- Best practices

## Available Templates

### Default Template

The `default/` template is used for all new projects regardless of project type (Python, Node.js, PHP, etc.).

**Location**: `/projects/templates/default/`

**Files included**:
- `README.md` - Project documentation template
- `.gitignore` - Git ignore patterns
- `setup.sh` - Project setup script
- `.env.example` - Environment variables template (optional)
- `tools/dev-notes.md` - Development notes and guidelines
- `tools/run.sh` - Quick start script (optional)

## Template Structure

```
default/
├── README.md           # Project overview and documentation
├── .gitignore          # Git ignore patterns
├── setup.sh            # Setup and initialization script
├── .env.example        # Environment variables example
└── tools/
    ├── dev-notes.md    # Development guidelines and notes
    └── run.sh          # Quick run/start script
```

## File Descriptions

### README.md

Project documentation template that includes:
- Project name and description
- Getting started instructions
- Available commands
- Project structure
- Contributing guidelines

### .gitignore

Common ignore patterns for:
- Python (*.pyc, __pycache__, .venv)
- Node.js (node_modules/, .npm)
- PHP (vendor/, composer.lock)
- Environment files (.env)
- IDE files (.vscode/, .idea/)
- System files (.DS_Store)

### setup.sh

Project initialization script:
- Install dependencies
- Setup virtual environment
- Initialize git repository
- Configure environment

### .env.example

Template for environment variables:
- Database configuration
- API keys placeholders
- Service URLs
- Feature flags

### tools/dev-notes.md

Development guidelines:
- Code style and conventions
- Testing instructions
- Deployment procedures
- Common tasks and commands

### tools/run.sh

Quick start script:
- Start development server
- Run application
- Common development commands

## Using Templates

### Automatic Usage

Templates are automatically applied when creating a new project:

```bash
# Create project (template applied automatically)
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: your-key" \
  -d '{"username": "alice", "project_name": "my-app", "project_type": "python"}'
```

The Project Manager:
1. Creates workspace directory
2. Copies all files from `templates/default/`
3. Initializes git repository
4. Mounts workspace to container

### Manual Template Application

Apply template to existing directory:

```bash
# Copy template files
cp -r /projects/templates/default/* /projects/alice-my-app/

# Initialize git (if not already initialized)
cd /projects/alice-my-app/
git init
```

## Customizing Templates

### Modifying Default Template

Edit files in `templates/default/`:

```bash
# Edit README template
nano /projects/templates/default/README.md

# Add new template file
echo "#!/bin/bash" > /projects/templates/default/deploy.sh
chmod +x /projects/templates/default/deploy.sh
```

All new projects will include these changes.

### Adding Variables

Use placeholders in templates:

```markdown
# {{PROJECT_NAME}}

Welcome to {{PROJECT_NAME}}!

Created by: {{USERNAME}}
```

Then replace in Project Manager:

```python
def _apply_template(self, workspace_path: str, vars: dict):
    """Apply template with variable substitution"""
    for file in template_files:
        content = open(file).read()
        for key, value in vars.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        write_file(content)
```

### Project-Type-Specific Templates

Create type-specific templates:

```bash
# Create Python-specific template
mkdir -p templates/python/
cp -r templates/default/* templates/python/

# Add Python-specific files
echo "requirements.txt" > templates/python/requirements.txt
echo "pytest.ini" > templates/python/pytest.ini
```

Update Project Manager to use:

```python
def _get_template_dir(self, project_type: str) -> str:
    """Select template based on project type"""
    type_templates = {
        'python': '/projects/templates/python/',
        'nodejs': '/projects/templates/nodejs/',
    }
    return type_templates.get(project_type, '/projects/templates/default/')
```

## Template Best Practices

### 1. Keep It Simple

Include only essential files:
- ✅ README, .gitignore, setup script
- ❌ Large dependencies, frameworks, boilerplate code

### 2. Document Everything

Every template file should:
- Explain its purpose
- Include usage examples
- Provide clear instructions

### 3. Use Comments

Add comments in template files:

```bash
#!/bin/bash
# Setup script for VIBE project
# This script installs dependencies and configures the environment

# Install Python dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
```

### 4. Include Sensible Defaults

Provide working defaults:
- Safe .gitignore patterns
- Common environment variables
- Standard project structure

### 5. Make It Customizable

Allow easy customization:
- Use placeholders for project-specific values
- Provide examples and alternatives
- Include optional features

## Examples

### Python Project Template

```
default/
├── README.md
├── .gitignore          # Python-specific ignores
├── setup.sh            # pip install, venv setup
├── .env.example        # DATABASE_URL, API_KEY
├── requirements.txt    # Empty or common packages
└── tools/
    ├── dev-notes.md    # Python style guide
    └── run.sh          # python app.py
```

### Node.js Project Template

```
default/
├── README.md
├── .gitignore          # node_modules/, .npm
├── setup.sh            # npm install
├── .env.example        # PORT, NODE_ENV
├── package.json        # Minimal package.json
└── tools/
    ├── dev-notes.md    # JavaScript conventions
    └── run.sh          # npm start
```

### Full-Stack Template

```
default/
├── README.md
├── .gitignore          # Combined ignores
├── setup.sh            # Setup backend + frontend
├── .env.example        # All service configs
├── docker-compose.yml  # Local development stack
└── tools/
    ├── dev-notes.md    # Architecture overview
    └── run.sh          # Start all services
```

## Version Control

### Tracking Changes

Template changes should be version controlled:

```bash
git add projects/templates/default/
git commit -m "Update default template with new setup script"
git push
```

### Template Versioning

Consider versioning templates:

```
templates/
├── default/           # Latest version
├── v1.0/             # Stable v1.0
└── v2.0/             # Beta v2.0
```

## Testing Templates

### Manual Testing

```bash
# Create test project
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: key" \
  -d '{"username": "test", "project_name": "template-test"}'

# Verify template files
ls -la /projects/test-template-test/

# Test setup script
docker exec vibe-test-template-test bash /workspace/setup.sh

# Cleanup
curl -X DELETE http://localhost:9000/projects/delete \
  -d '{"project_id": "test-template-test", "password": "..."}'
```

### Automated Testing

Add template tests:

```python
def test_default_template_files():
    """Test all expected template files are present"""
    template_dir = "/projects/templates/default/"
    expected_files = [
        "README.md",
        ".gitignore",
        "setup.sh",
        ".env.example",
        "tools/dev-notes.md",
        "tools/run.sh"
    ]

    for file in expected_files:
        assert os.path.exists(os.path.join(template_dir, file))
```

## Troubleshooting

### Template Files Not Copied

Check:
- Template directory exists
- Files have read permissions
- Project Manager has access
- No errors in logs

### Setup Script Fails

Debug setup script:

```bash
# Run script manually
docker exec -it vibe-{project-id} bash
cd /workspace
bash -x setup.sh  # Debug mode
```

### Git Not Initialized

The `.git/` directory is created at runtime, not in the template. If missing:

```bash
cd /workspace
git init
git config user.name "User"
git config user.email "user@example.com"
```

## Documentation

For more information:
- [Projects README](../README.md)
- [Project Manager README](../../project-manager/README.md)
