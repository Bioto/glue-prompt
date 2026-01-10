# Glue-Prompt

Git-based prompt versioning system using branches to manage prompt templates.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Glue-Prompt provides a simple yet powerful way to version and manage prompts using git branches. Prompts are stored as YAML files in a git repository, and you can switch between versions by checking out different branches or tags. Perfect for managing LLM prompts, system instructions, and template-based content with full version control.

## Features

- **Git-based versioning**: Use branches and tags to version your prompts with full git history
- **YAML-based prompts**: Simple, readable prompt definitions with metadata
- **Jinja2 templating**: Powerful template rendering with variables, conditionals, and loops
- **Validation**: Built-in prompt validation and error checking before rendering
- **Diffing**: Compare prompts across versions to track changes
- **CLI tools**: Comprehensive command-line interface for prompt management
- **REST API**: FastAPI server for serving prompts in production environments
- **Caching**: In-memory caching for improved performance
- **Multi-repo support**: Manage multiple prompt repositories simultaneously
- **Worktree support**: Access multiple versions concurrently without conflicts

## Installation

### From PyPI

```bash
pip install glue-prompt
```

### From Source

```bash
git clone https://github.com/Bioto/glue-prompt.git
cd glue-prompt
pip install -e ".[dev]"
```

### Requirements

- Python 3.12 or higher
- Git (for versioning features)

## Quick Start

### Option A: Clone an existing prompts repo (Recommended)

```bash
# Add a remote prompts repository
glueprompt repo add https://github.com/your-org/prompts.git

# List your repos
glueprompt repo list

# Use prompts from the repo
glueprompt prompt -r prompts get assistants/helpful-bot
glueprompt prompt -r prompts render assistants/helpful-bot --var name=Claude
```

### Option B: Create your own prompts repository

```bash
mkdir my-prompts && cd my-prompts
git init
```

### 2. Create a prompt

Create a YAML file for your prompt:

```yaml
# assistants/helpful-bot.yaml
name: helpful-bot
version: 1.0.0
description: A friendly assistant prompt
author: your-name
tags: [assistant, general]

template: |
  You are a helpful assistant named {{ name }}.
  {{ extra_instructions }}

variables:
  name:
    type: string
    required: true
    description: The assistant's name
  extra_instructions:
    type: string
    required: false
    default: ""
    description: Additional instructions
```

### 3. Use in your code

```python
from glueprompt import PromptRegistry, RepoManager

# Option A: Use a cached repo (added via CLI)
manager = RepoManager()
registry = PromptRegistry(manager.get_path("prompts"))

# Option B: Use a local path directly
registry = PromptRegistry("./my-prompts")

# Get and render a prompt
rendered = registry.render(
    "assistants/helpful-bot",
    name="Claude",
    extra_instructions="Be concise."
)

print(rendered)
```

### 4. Version your prompts

```bash
# Create a new version branch
cd my-prompts
git checkout -b v2.0
# Edit your prompts...
git commit -am "Update prompts for v2.0"

# Switch versions in code
registry.checkout("v2.0")
```

## Usage

### Python API

#### Basic Usage

```python
from glueprompt import PromptRegistry, RepoManager

# Initialize registry with a prompts directory
registry = PromptRegistry("./prompts")

# Get a prompt (returns Prompt object with metadata)
prompt = registry.get("assistants/helpful-bot")
print(prompt.metadata.name)
print(prompt.metadata.version)
print(prompt.template)

# Render with variables (returns rendered string)
rendered = registry.render(
    "assistants/helpful-bot",
    name="Claude",
    extra_instructions="Be helpful and concise"
)
print(rendered)
```

#### Working with Multiple Repositories

```python
from glueprompt import RepoManager, PromptRegistry

# Manage multiple repositories
manager = RepoManager()

# Clone a repository
manager.clone("https://github.com/your-org/prompts.git", name="company-prompts")

# List all repositories
repos = manager.list_repos()
for repo in repos:
    print(f"{repo['name']}: {repo['path']}")

# Use a specific repository
repo_path = manager.get_path("company-prompts")
registry = PromptRegistry(repo_path)

# Set default repository
manager.set_default_repo("company-prompts")
```

#### Version Management

```python
# Checkout a version (branch or tag)
registry.checkout("v1.0")

# List available versions
versions = registry.list_versions()
print("Branches:", [b.name for b in versions["branches"]])
print("Tags:", [t.branch_or_tag for t in versions["tags"]])

# Get current version information
current = registry.current_version()
print(f"Current: {current.branch_or_tag}")
print(f"Commit: {current.commit_hash}")
print(f"Date: {current.commit_date}")

# Diff between versions
diff = registry.diff("assistants/helpful-bot", version1="v1.0", version2="v2.0")
print(diff)

# Rollback to previous version
registry.rollback("v1.0")
```

#### Advanced Features

```python
# Validate a prompt before using it
errors = registry.validate("assistants/helpful-bot")
if errors:
    print("Validation errors:", errors)
else:
    print("Prompt is valid!")

# Cache management
registry.clear_cache()  # Clear all cached prompts
registry.invalidate_cache("assistants/helpful-bot")  # Invalidate specific prompt

# Check if versioning is available
if registry.has_versioning:
    print("Git versioning is enabled")
    current = registry.current_version()
else:
    print("No git repository - versioning disabled")
```

#### Working with Prompt Objects

```python
from glueprompt import PromptRegistry

registry = PromptRegistry("./prompts")
prompt = registry.get("assistants/helpful-bot")

# Access metadata
print(prompt.metadata.name)
print(prompt.metadata.version)
print(prompt.metadata.description)
print(prompt.metadata.tags)

# Access variables
for var_name, var_def in prompt.variables.items():
    print(f"{var_name}: {var_def.type} (required: {var_def.required})")

# Get required variables
required = prompt.get_required_variables()
print("Required:", required)

# Get default values
defaults = prompt.get_variable_defaults()
print("Defaults:", defaults)
```

### CLI Usage

#### Repository Management

```bash
# Add a remote prompts repository (clones to ~/.cache/glueprompt/repos/)
glueprompt repo add https://github.com/your-org/prompts.git
glueprompt repo add git@github.com:your-org/prompts.git --name my-prompts
glueprompt repo add https://github.com/your-org/prompts.git --branch main --name my-prompts

# List cached repos
glueprompt repo list

# Update a repo (git pull)
glueprompt repo update my-prompts
glueprompt repo update my-prompts --branch feature-branch

# Remove a cached repo
glueprompt repo remove my-prompts

# Set/get default repository
glueprompt repo default my-prompts  # Set default
glueprompt repo default             # Show current default
```

#### Working with Prompts

```bash
# Use -r/--repo to specify which cached repo to use
glueprompt prompt -r my-prompts get assistants/helpful-bot
glueprompt prompt -r my-prompts render assistants/helpful-bot --var name=Claude --var style=formal
glueprompt prompt -r my-prompts validate assistants/helpful-bot
glueprompt prompt -r my-prompts list

# Or use a local path directly
glueprompt prompt -d ./my-prompts get assistants/helpful-bot

# Create a new prompt
glueprompt prompt -r my-prompts add assistants/new-bot \
  --name "New Bot" \
  --description "A new assistant" \
  --template "You are {{ name }}." \
  --edit  # Opens in editor

# Edit an existing prompt (auto-bumps version)
glueprompt prompt -r my-prompts edit assistants/helpful-bot
glueprompt prompt -r my-prompts edit assistants/helpful-bot --bump minor

# Remove a prompt
glueprompt prompt -r my-prompts remove assistants/old-bot
```

#### Version Management

```bash
# List versions (branches and tags)
glueprompt version -r my-prompts list

# Checkout a version
glueprompt version -r my-prompts checkout v2.0
glueprompt version -r my-prompts checkout feature-branch --create  # Create if doesn't exist

# Show diff between versions
glueprompt version -r my-prompts diff assistants/helpful-bot --v1 v1.0 --v2 v2.0
glueprompt version -r my-prompts diff assistants/helpful-bot --v1 HEAD~1  # Compare with previous commit
```

#### Server Mode

```bash
# Start the FastAPI server
glueprompt serve
glueprompt serve --host 0.0.0.0 --port 8080
glueprompt serve --reload  # Development mode with auto-reload

# Server will be available at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

## Prompt Format

Prompts are defined in YAML files with the following structure:

```yaml
name: prompt-name          # Required: Prompt identifier
version: 1.0.0             # Optional: Semantic version (default: 1.0.0)
description: Description    # Optional: Human-readable description
author: Author Name        # Optional: Author name
tags: [tag1, tag2]        # Optional: List of tags

template: |               # Required: Jinja2 template string
  Your prompt template here.
  Use {{ variable }} for variables.
  {% if condition %}Conditional content{% endif %}
  {% for item in items %}{{ item }}{% endfor %}

variables:                 # Optional: Variable definitions
  variable_name:
    type: string          # Variable type (string, int, float, bool, list, dict, any)
    required: true        # Whether variable is required
    default: null         # Default value if not required
    description: "..."     # Variable description
```

### Jinja2 Template Features

Glue-Prompt supports full Jinja2 templating capabilities:

```yaml
template: |
  {% if role == "admin" %}
  You are an administrator with full access.
  {% elif role == "user" %}
  You are a regular user.
  {% endif %}
  
  {% for instruction in instructions %}
  - {{ instruction }}
  {% endfor %}
  
  Current user: {{ user.name }} ({{ user.email }})
  
  {% set greeting = "Hello, " + name %}
  {{ greeting }}
```

### Variable Types

Supported variable types:
- `string`: Text values
- `int`: Integer numbers
- `float`: Decimal numbers
- `bool`: Boolean (true/false)
- `list`: Array of values
- `dict`: Object/mapping
- `any`: Any type (no validation)

### Example Prompt Files

**Simple prompt:**
```yaml
name: greeting
version: 1.0.0
template: "Hello, {{ name }}!"
variables:
  name:
    type: string
    required: true
```

**Complex prompt:**
```yaml
name: code-reviewer
version: 2.1.0
description: AI code reviewer with configurable strictness
author: dev-team
tags: [code, review, ai]

template: |
  You are an expert code reviewer.
  
  Review the following code with {{ strictness }} strictness:
  {{ code }}
  
  {% if focus_areas %}
  Pay special attention to:
  {% for area in focus_areas %}
  - {{ area }}
  {% endfor %}
  {% endif %}
  
  Provide feedback in {{ format }} format.

variables:
  code:
    type: string
    required: true
    description: Code to review
  strictness:
    type: string
    required: false
    default: "medium"
    description: Strictness level (low, medium, high)
  focus_areas:
    type: list
    required: false
    default: []
    description: Areas to focus on
  format:
    type: string
    required: false
    default: "markdown"
    description: Output format
```

## REST API Server

Glue-Prompt includes a FastAPI server for serving prompts in production environments.

### Starting the Server

```bash
glueprompt serve --host 0.0.0.0 --port 8000
```

### API Endpoints

#### List Repositories
```http
GET /repos
```

Response:
```json
{
  "repos": [
    {
      "name": "my-prompts",
      "url": "https://github.com/user/prompts.git",
      "path": "/path/to/repo",
      "current_branch": "main"
    }
  ]
}
```

#### List Versions
```http
GET /repos/{repo}/versions
```

Response:
```json
{
  "branches": [
    {
      "name": "main",
      "commit_hash": "abc123",
      "is_branch": true,
      "is_current": true
    }
  ],
  "tags": [
    {
      "name": "v1.0.0",
      "commit_hash": "def456",
      "is_branch": false
    }
  ],
  "current": "main"
}
```

#### List Prompts
```http
GET /repos/{repo}/prompts?version=v1.0
```

Response:
```json
{
  "prompts": [
    "assistants/helper",
    "tools/summarizer"
  ]
}
```

#### Get Prompt
```http
GET /repos/{repo}/prompts/{prompt_path}?version=1.0.5
```

Response:
```json
{
  "metadata": {
    "name": "helper",
    "version": "1.0.5",
    "description": "A helpful assistant",
    "author": "team",
    "tags": ["assistant"]
  },
  "template": "You are {{ name }}...",
  "variables": {
    "name": {
      "type": "string",
      "required": true,
      "default": null,
      "description": "Assistant name"
    }
  }
}
```

#### Render Prompt
```http
POST /repos/{repo}/prompts/{prompt_path}/render?version=1.0.5
Content-Type: application/json

{
  "variables": {
    "name": "Claude",
    "style": "formal"
  }
}
```

Response:
```json
{
  "rendered": "You are Claude...",
  "version": "1.0.5"
}
```

#### Health Check
```http
GET /health
```

### API Documentation

When the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Architecture

### Core Components

- **RepoManager**: Clones and caches prompt repositories from remote URLs
- **PromptRegistry**: Main entry point for prompt management and orchestration
- **PromptLoader**: Loads and caches prompts from YAML files with TTL support
- **TemplateRenderer**: Renders Jinja2 templates with variable substitution
- **VersionManager**: Manages git branches and tags for versioning
- **PromptValidator**: Validates prompt structure, syntax, and variable definitions
- **WorktreeManager**: Manages git worktrees for concurrent version access (server mode)

### Data Flow

```
User Request
    ↓
PromptRegistry
    ↓
PromptLoader → Cache Check → YAML Parse → Prompt Object
    ↓
TemplateRenderer → Variable Merge → Jinja2 Render → Rendered String
    ↓
Response
```

### Version Management Flow

```
Checkout Request
    ↓
VersionManager
    ↓
Git Operations → Branch/Tag Checkout → Cache Invalidation
    ↓
Updated Prompt Files
```

## Configuration

### File Locations

- **Repository cache**: `~/.cache/glueprompt/repos/`
- **Worktrees**: `~/.cache/glueprompt/worktrees/`
- **Config file**: `~/.config/glueprompt/repos.json`
- **Default repo**: `~/.config/glueprompt/default_repo.txt`

### Environment Variables

```bash
# Default path for prompts directory
export GLUEPROMPT_DEFAULT_PROMPTS_PATH=./prompts

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export GLUEPROMPT_LOG_LEVEL=INFO

# Cache settings
export GLUEPROMPT_CACHE_ENABLED=true
export GLUEPROMPT_CACHE_TTL_SECONDS=300
```

### Programmatic Configuration

```python
from glueprompt.config import get_settings, reload_settings

# Get current settings
settings = get_settings()
print(settings.default_prompts_path)
print(settings.cache_enabled)

# Reload from environment
settings = reload_settings()
```

## Best Practices

### Versioning Strategy

1. **Use semantic versioning** for prompt versions in YAML files
2. **Use git tags** for stable releases (e.g., `v1.0.0`, `v2.0.0`)
3. **Use branches** for development and experimentation
4. **Tag prompt-specific versions** using format: `{prompt-path}/v{version}`

### Prompt Organization

```
prompts/
├── assistants/
│   ├── helpful-bot.yaml
│   └── coding-assistant.yaml
├── tools/
│   ├── summarizer.yaml
│   └── translator.yaml
└── system/
    └── instructions.yaml
```

### Template Design

- Keep templates readable and maintainable
- Use descriptive variable names
- Provide default values when possible
- Document variables with descriptions
- Use conditionals and loops judiciously

### Security Considerations

- **Path validation**: Glue-Prompt validates prompt paths to prevent directory traversal
- **Template sandboxing**: For untrusted templates, consider using Jinja2's `SandboxedEnvironment`
- **Repository access**: Only clone repositories from trusted sources
- **API security**: When using the server, implement proper authentication and authorization

## Troubleshooting

### Common Issues

**"Not a valid git repository"**
- Ensure the prompts directory is a git repository: `git init`
- Or use a repository cloned via `glueprompt repo add`

**"Prompt not found"**
- Check the prompt path is correct (relative to prompts directory)
- Verify the file exists with `.yaml` or `.yml` extension
- Check if you're on the correct branch/version

**"Missing required variables"**
- Check the prompt's variable definitions
- Ensure all required variables are provided when rendering
- Use `prompt.get_required_variables()` to see what's needed

**Cache issues**
- Clear cache: `registry.clear_cache()`
- Disable cache: `PromptRegistry(cache_enabled=False)`
- Check cache TTL settings

**Version checkout fails**
- Ensure the branch/tag exists: `git branch -a` or `git tag -l`
- Fetch latest: `git fetch --all --tags`
- Check repository permissions

### Debug Mode

Enable debug logging:
```bash
export GLUEPROMPT_LOG_LEVEL=DEBUG
```

Or in Python:
```python
import logging
logging.getLogger("glueprompt").setLevel(logging.DEBUG)
```

## Examples

### Example: Multi-Environment Prompts

```python
from glueprompt import PromptRegistry

registry = PromptRegistry("./prompts")

# Production prompts
registry.checkout("production")
prod_prompt = registry.render("assistants/helper", name="Claude")

# Staging prompts
registry.checkout("staging")
staging_prompt = registry.render("assistants/helper", name="Claude")
```

### Example: A/B Testing

```python
# Test different prompt versions
versions = registry.list_versions()
for tag in versions["tags"]:
    if tag.branch_or_tag.startswith("ab-test-"):
        registry.checkout(tag.branch_or_tag)
        rendered = registry.render("assistants/helper", name="Claude")
        # Test and compare results
```

### Example: Prompt Validation in CI/CD

```python
# Validate all prompts before deployment
registry = PromptRegistry("./prompts")
errors_found = False

for prompt_path in registry.list_prompts():
    errors = registry.validate(prompt_path)
    if errors:
        print(f"❌ {prompt_path}: {errors}")
        errors_found = True
    else:
        print(f"✅ {prompt_path}: Valid")

if errors_found:
    exit(1)
```

### Example: Server Integration

```python
# In your application
import requests

# Get prompt from API
response = requests.get("http://localhost:8000/repos/my-prompts/prompts/assistants/helper")
prompt_data = response.json()

# Render prompt
render_response = requests.post(
    "http://localhost:8000/repos/my-prompts/prompts/assistants/helper/render",
    json={"variables": {"name": "Claude"}}
)
rendered = render_response.json()["rendered"]
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/Bioto/glue-prompt.git
cd glue-prompt

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=glueprompt --cov-report=html

# Run specific test file
pytest tests/test_registry.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking (if using mypy)
mypy glueprompt
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Repository**: [https://github.com/Bioto/glue-prompt](https://github.com/Bioto/glue-prompt)
- **Issues**: [https://github.com/Bioto/glue-prompt/issues](https://github.com/Bioto/glue-prompt/issues)
- **Documentation**: [https://github.com/Bioto/glue-prompt#readme](https://github.com/Bioto/glue-prompt#readme)
