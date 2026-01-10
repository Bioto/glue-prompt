# Glue-Prompt

Git-based prompt versioning system using branches to manage prompt templates.

## Overview

Glue-Prompt provides a simple yet powerful way to version and manage prompts using git branches. Prompts are stored as YAML files in a git submodule, and you can switch between versions by checking out different branches.

## Features

- **Git-based versioning**: Use branches and tags to version your prompts
- **YAML-based prompts**: Simple, readable prompt definitions
- **Jinja2 templating**: Powerful template rendering with variables
- **Validation**: Built-in prompt validation and error checking
- **Diffing**: Compare prompts across versions
- **CLI tools**: Command-line interface for prompt management

## Installation

```bash
pip install glue-prompt
```

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

### Basic API

```python
from glueprompt import PromptRegistry

registry = PromptRegistry("./prompts")

# Get a prompt
prompt = registry.get("assistants/helpful-bot")

# Render with variables using registry
rendered = registry.render("assistants/helpful-bot", name="Claude", extra_instructions="Be helpful")
```

### Version Management

```python
# Checkout a version
registry.checkout("v1.0")

# List available versions
versions = registry.list_versions()
print(versions["branches"])
print(versions["tags"])

# Get current version
current = registry.current_version()
print(f"Current: {current.branch_or_tag}")

# Diff between versions
diff = registry.diff("assistants/helpful-bot", version1="v1.0", version2="v2.0")
print(diff)
```

### CLI Usage

```bash
# --- Repository Management ---

# Add a remote prompts repository (clones to ~/.cache/glueprompt/repos/)
glueprompt repo add https://github.com/your-org/prompts.git
glueprompt repo add git@github.com:your-org/prompts.git --name my-prompts

# List cached repos
glueprompt repo list

# Update a repo (git pull)
glueprompt repo update my-prompts

# Remove a cached repo
glueprompt repo remove my-prompts

# --- Working with Prompts ---

# Use -r/--repo to specify which cached repo to use
glueprompt prompt -r my-prompts get assistants/helpful-bot
glueprompt prompt -r my-prompts render assistants/helpful-bot --var name=Claude
glueprompt prompt -r my-prompts validate assistants/helpful-bot
glueprompt prompt -r my-prompts list

# Or use -d/--prompts-dir for a local path
glueprompt prompt -d ./my-prompts get assistants/helpful-bot

# --- Version Management ---

# List versions (branches and tags)
glueprompt version -r my-prompts list

# Checkout a version
glueprompt version -r my-prompts checkout v2.0

# Show diff between versions
glueprompt version -r my-prompts diff assistants/helpful-bot --v1 v1.0 --v2 v2.0
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

variables:                 # Optional: Variable definitions
  variable_name:
    type: string          # Variable type (string, int, float, bool, etc.)
    required: true        # Whether variable is required
    default: null         # Default value if not required
    description: "..."     # Variable description
```

## Architecture

- **RepoManager**: Clones and caches prompt repositories
- **PromptRegistry**: Main entry point for prompt management
- **PromptLoader**: Loads and caches prompts from YAML files
- **TemplateRenderer**: Renders Jinja2 templates with variables
- **VersionManager**: Manages git branches and tags
- **PromptValidator**: Validates prompt structure and syntax

## Configuration

Repos are cached in `~/.cache/glueprompt/repos/` and config is stored in `~/.config/glueprompt/repos.json`.

Environment variables:
- `GLUE_PROMPT_DEFAULT_PROMPTS_PATH`: Default path for prompts directory

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .
```

## License

MIT
