"""Basic usage example for glue-prompt."""

from pathlib import Path

from glueprompt import PromptRegistry

# Initialize registry with path to prompts directory
# In practice, this would be a git submodule
prompts_dir = Path(__file__).parent / "prompts"
registry = PromptRegistry(prompts_dir=prompts_dir)

# Get a prompt
prompt = registry.get("assistants/helpful-bot")
print(f"Loaded prompt: {prompt.metadata.name} v{prompt.metadata.version}")
print(f"Description: {prompt.metadata.description}")
print(f"Variables: {list(prompt.variables.keys())}")

# Render the prompt with variables
rendered = registry.render(
    "assistants/helpful-bot",
    name="Claude",
    extra_instructions="Be concise and helpful.",
)

print("\nRendered Prompt:")
print("=" * 50)
print(rendered)
print("=" * 50)

# Or render using the renderer directly
from glueprompt.renderer import TemplateRenderer

renderer = TemplateRenderer()
rendered2 = renderer.render(
    prompt,
    name="GPT-4",
    extra_instructions="Use emojis sparingly.",
)

print("\nAlternative rendering:")
print(rendered2)

