# Projects Directory

Default project workspaces and templates for the VIBE Coding Platform.

## Overview

This directory serves two purposes:
1. **Templates**: Default project scaffolding for new projects
2. **Runtime Workspaces**: Active project directories (when running)

## Directory Structure

```
projects/
├── templates/           # Project templates
│   └── default/        # Default template for all projects
│       ├── README.md
│       ├── .gitignore
│       ├── setup.sh
│       ├── .env.example
│       └── tools/
│           ├── dev-notes.md
│           └── run.sh
│
└── {username-project}/  # Runtime project workspaces (created dynamically)
    ├── README.md        # From template
    ├── .gitignore       # From template
    ├── setup.sh         # From template
    ├── .git/            # Initialized by Project Manager
    └── ...              # User's project files
```

## Templates

### Default Template

The `templates/default/` directory contains files that are copied to every new project workspace:

- **README.md**: Project documentation template
- **.gitignore**: Common ignore patterns
- **setup.sh**: Project setup script
- **.env.example**: Environment variables template
- **tools/dev-notes.md**: Development notes
- **tools/run.sh**: Quick run script

### Customizing Templates

To add files to the default template:

```bash
# Add file to template
echo "Your content" > templates/default/newfile.txt

# All new projects will include this file
```

### Creating Custom Templates

To create project-type-specific templates:

```bash
# Create template directory
mkdir -p templates/python-flask/

# Add template files
cp templates/default/* templates/python-flask/
echo "Flask specific config" > templates/python-flask/flask-config.py

# Update Project Manager to use custom template
# Edit: project-manager/app/services/__init__.py
```

## Runtime Workspaces

### Workspace Creation

When a project is created:
1. Project Manager creates directory: `/projects/{username}-{project-name}/`
2. Template files are copied from `templates/default/`
3. Git repository is initialized
4. Directory is mounted to project container at `/workspace`

### Workspace Structure

Each project workspace contains:

```
alice-my-app/
├── .git/               # Git repository
├── .gitignore          # From template
├── README.md           # From template
├── setup.sh            # From template
├── .env.example        # From template
├── tools/
│   ├── dev-notes.md    # From template
│   └── run.sh          # From template
└── ...                 # User's files created during development
```

### Workspace Permissions

Workspaces are created with:
- **Permissions**: 755 (rwxr-xr-x)
- **Owner**: Container user (uid=1000, coder)
- **Mount**: Read-write to container at `/workspace`

### Workspace Lifecycle

1. **Creation**: Directory created, template copied
2. **Active**: Mounted to running container
3. **Inactive**: Container stopped, workspace preserved
4. **Cleanup**: After `MAX_PROJECT_AGE_DAYS`, removed by Cleanup Service

## Storage

### Default Location

- **Development**: `/srv/vibe/projects/`
- **Docker**: Mounted as volume

### Disk Usage

Monitor workspace disk usage:

```bash
# Check total size
du -sh /srv/vibe/projects/

# Check per-project size
du -sh /srv/vibe/projects/*

# Find large projects
du -sh /srv/vibe/projects/* | sort -hr | head -10
```

### Storage Quotas

Project storage limits:
- **Default**: 10GB per project
- **Enforced by**: Docker storage driver quotas
- **Configuration**: `PROJECT_STORAGE_LIMIT` in config

## Backup

### Manual Backup

```bash
# Backup single project
tar -czf alice-my-app-backup.tar.gz /srv/vibe/projects/alice-my-app/

# Backup all projects
tar -czf projects-backup.tar.gz /srv/vibe/projects/
```

### Automated Backups

Project Manager creates automatic backups before destructive operations:
- Git reset --hard
- Project deletion (optional)

Backups stored at:
```
/srv/vibe/projects/{project_id}.backup.{timestamp}.tar.gz
```

### Restore from Backup

```bash
# Extract backup
tar -xzf alice-my-app-backup.tar.gz -C /srv/vibe/projects/

# Fix permissions
chmod -R 755 /srv/vibe/projects/alice-my-app/
```

## Cleanup

### Manual Cleanup

Remove inactive project workspace:

```bash
# Check if project is active
docker ps | grep alice-my-app

# Remove workspace
rm -rf /srv/vibe/projects/alice-my-app/
```

### Automatic Cleanup

The Cleanup Service removes workspaces for:
- Projects inactive for > `MAX_PROJECT_AGE_DAYS`
- Orphaned workspaces (no Redis entry)

See [Cleanup Service README](../cleanup/README.md) for details.

## Best Practices

### Template Design

1. **Keep templates minimal** - Only include essential files
2. **Document clearly** - README should explain project structure
3. **Include .gitignore** - Prevent committing sensitive files
4. **Add setup scripts** - Make onboarding easy
5. **Provide examples** - Show how to use the template

### Workspace Management

1. **Regular cleanup** - Remove old projects
2. **Monitor disk usage** - Prevent storage exhaustion
3. **Backup important projects** - Before destructive operations
4. **Set appropriate permissions** - Ensure container can write
5. **Version control** - Encourage users to commit regularly

## Troubleshooting

### Template Not Copied

Check:
- Template directory exists: `ls -la templates/default/`
- Project Manager has read access
- No file copy errors in logs

### Permission Denied in Container

Fix workspace permissions:

```bash
chmod -R 755 /srv/vibe/projects/{project_id}/
chown -R 1000:1000 /srv/vibe/projects/{project_id}/
```

### Workspace Not Found

Check:
- Project created successfully
- Workspace directory exists
- Correct path in configuration

### Git Not Initialized

Manually initialize:

```bash
cd /srv/vibe/projects/{project_id}/
git init
git config user.name "User"
git config user.email "user@example.com"
```

## Advanced Usage

### Custom Template Selection

Modify Project Manager to support multiple templates:

```python
# In project-manager/app/services/__init__.py

def _get_template_dir(self, project_type: str) -> str:
    """Get template directory based on project type"""
    templates = {
        'python': '/templates/python-flask/',
        'nodejs': '/templates/nodejs-express/',
        'default': '/templates/default/'
    }
    return templates.get(project_type, templates['default'])
```

### Dynamic Template Generation

Generate templates programmatically:

```python
def _generate_template(self, project_type: str, options: dict):
    """Generate custom template based on options"""
    template_dir = self._prepare_workspace(...)

    # Create files based on options
    if options.get('use_docker'):
        self._create_dockerfile(template_dir)

    if options.get('use_ci'):
        self._create_github_actions(template_dir)
```

## Documentation

For more information:
- [Default Template README](./templates/README.md)
- [Project Manager README](../project-manager/README.md)
- [Cleanup Service README](../cleanup/README.md)
