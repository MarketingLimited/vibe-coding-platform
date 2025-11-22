# OpenAPI Specification Tools

Tools for generating and rendering OpenAPI specifications for the VIBE Coding Platform API.

## Overview

This directory contains:
- OpenAPI specification templates
- Rendering scripts to generate final specs
- Tools for multi-tenant API documentation

## Files

- `openapi-spec-multitenant.yaml` - OpenAPI spec template with placeholders
- `render-multitenant-spec.sh` - Script to render spec with actual server URL
- `validate-spec.sh` - Validate OpenAPI specification

## OpenAPI Specification

The platform provides a complete OpenAPI 3.0 specification documenting:
- All API endpoints
- Request/response schemas
- Authentication requirements
- Error responses
- Rate limiting behavior

## Usage

### Render Specification

Replace template placeholders with actual server URL:

```bash
cd tools/openapi
./render-multitenant-spec.sh
```

This generates `openapi-spec-multitenant.rendered.yaml` at the project root.

### Validate Specification

Check if the OpenAPI spec is valid:

```bash
./validate-spec.sh
```

### View Documentation

Use Swagger UI or Redoc to view the documentation:

```bash
# Using Swagger UI (requires npm)
npx swagger-ui-watcher openapi-spec-multitenant.rendered.yaml

# Using Redoc (requires npm)
npx redoc-cli serve openapi-spec-multitenant.rendered.yaml
```

### Generate API Clients

Use the OpenAPI spec to generate client libraries:

```bash
# Generate Python client
openapi-generator-cli generate \
  -i openapi-spec-multitenant.rendered.yaml \
  -g python \
  -o clients/python

# Generate TypeScript client
openapi-generator-cli generate \
  -i openapi-spec-multitenant.rendered.yaml \
  -g typescript-fetch \
  -o clients/typescript

# Generate Go client
openapi-generator-cli generate \
  -i openapi-spec-multitenant.rendered.yaml \
  -g go \
  -o clients/go
```

## Specification Structure

```yaml
openapi: 3.0.0
info:
  title: VIBE Coding Platform API
  version: 1.0.0
  description: Multi-tenant coding platform API

servers:
  - url: ${API_PUBLIC_BASE_URL}  # Replaced during rendering

paths:
  /projects/create:
    post:
      summary: Create new project
      security:
        - ApiKeyAuth: []
      requestBody: ...
      responses: ...

  /exec:
    post:
      summary: Execute command
      security:
        - PasswordAuth: []
      requestBody: ...
      responses: ...

components:
  schemas:
    ProjectCreate: ...
    ExecRequest: ...
    ErrorResponse: ...

  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

    PasswordAuth:
      type: http
      scheme: bearer
```

## Environment Variables

The render script uses these environment variables:

- `API_PUBLIC_BASE_URL` - Public API URL (default: http://localhost:9000)
- `DOMAIN` - Platform domain (default: localhost)

Set them before rendering:

```bash
export API_PUBLIC_BASE_URL=https://api.example.com
export DOMAIN=example.com
./render-multitenant-spec.sh
```

## Updating the Specification

When adding new endpoints:

1. Edit `openapi-spec-multitenant.yaml`
2. Add path definition under `paths:`
3. Add request/response schemas under `components/schemas:`
4. Add security requirements if needed
5. Validate the spec: `./validate-spec.sh`
6. Render the final spec: `./render-multitenant-spec.sh`
7. Commit both template and rendered files

## Integration with API

The Central API automatically serves OpenAPI documentation:

```bash
# Get OpenAPI spec
curl http://localhost:9000/openapi.json

# View Swagger UI
open http://localhost:9000/docs

# View Redoc
open http://localhost:9000/redoc
```

## Validation Tools

### Using openapi-spec-validator

```bash
pip install openapi-spec-validator
openapi-spec-validator openapi-spec-multitenant.rendered.yaml
```

### Using Swagger Editor

```bash
# Online validator
# Visit: https://editor.swagger.io
# Paste the spec content
```

### Using spectral

```bash
npm install -g @stoplight/spectral-cli
spectral lint openapi-spec-multitenant.rendered.yaml
```

## Best Practices

1. **Keep template DRY** - Use `$ref` for reusable schemas
2. **Document all fields** - Include descriptions and examples
3. **Specify constraints** - Min/max lengths, patterns, enums
4. **Include examples** - Add example requests and responses
5. **Version the spec** - Update version when making breaking changes
6. **Validate regularly** - Run validation after each change

## Example: Adding New Endpoint

```yaml
paths:
  /projects/{project_id}/stats:
    get:
      summary: Get project statistics
      tags:
        - Projects
      security:
        - PasswordAuth: []
      parameters:
        - name: project_id
          in: path
          required: true
          schema:
            type: string
          description: Project identifier
      responses:
        '200':
          description: Project statistics
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProjectStats'
        '401':
          description: Unauthorized
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    ProjectStats:
      type: object
      properties:
        total_executions:
          type: integer
          description: Total number of command executions
        total_commits:
          type: integer
          description: Total number of git commits
        last_activity:
          type: string
          format: date-time
          description: Last activity timestamp
```

## Troubleshooting

### Validation Errors

Check for:
- Missing required fields
- Invalid $ref paths
- Type mismatches
- Invalid OpenAPI syntax

### Rendering Fails

Ensure:
- Environment variables are set
- Template file exists
- Write permissions to output directory

### Generated Clients Don't Work

Verify:
- OpenAPI spec is valid
- Server URL is correct
- Authentication is properly configured
- Response schemas match actual API

## Documentation

For more information about the API, see the [Central API README](../../api/README.md)
