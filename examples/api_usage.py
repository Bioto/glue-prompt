"""Example usage of APIPromptRegistry to connect to FastAPI server."""

import asyncio

from glueprompt import APIPromptRegistry


async def main():
    """Demonstrate API client usage."""
    # Initialize API client
    # Make sure the FastAPI server is running: glueprompt serve
    client = APIPromptRegistry(
        base_url="http://localhost:8000",
        repo="my-prompts",  # Replace with your repo name
    )

    try:
        # Check server health
        health = await client.health_check()
        print(f"Server health: {health}")

        # List available repositories
        repos = await client.list_repos()
        print(f"\nAvailable repositories: {len(repos)}")
        for repo in repos:
            print(f"  - {repo.name} ({repo.url})")

        # List versions (branches and tags)
        versions = await client.list_versions()
        print(f"\nVersions:")
        print(f"  Branches: {len(versions['branches'])}")
        for branch in versions["branches"]:
            current = " (current)" if hasattr(branch, "is_current") and branch.is_current else ""
            print(f"    - {branch.name}{current}")
        print(f"  Tags: {len(versions['tags'])}")
        for tag in versions["tags"]:
            print(f"    - {tag.branch_or_tag}")

        # Get current version
        current = await client.current_version()
        print(f"\nCurrent version: {current.branch_or_tag}")

        # List prompts
        prompts = await client.list_prompts()
        print(f"\nAvailable prompts: {len(prompts)}")
        for prompt_path in prompts[:5]:  # Show first 5
            print(f"  - {prompt_path}")

        # Get a prompt
        prompt = await client.get("assistants/helpful-bot")
        print(f"\nLoaded prompt: {prompt.metadata.name} v{prompt.metadata.version}")
        print(f"Description: {prompt.metadata.description}")
        print(f"Variables: {list(prompt.variables.keys())}")

        # Render the prompt with variables
        rendered = await client.render(
            "assistants/helpful-bot",
            name="Claude",
            extra_instructions="Be concise and helpful.",
        )

        print("\nRendered Prompt:")
        print("=" * 50)
        print(rendered)
        print("=" * 50)

        # Get a specific version
        if versions["tags"]:
            tag_name = versions["tags"][0].branch_or_tag
            print(f"\nFetching prompt at version: {tag_name}")
            prompt_v1 = await client.get("assistants/helpful-bot", version="1.0.0")
            print(f"Version {tag_name}: {prompt_v1.metadata.version}")

        # Validate a prompt
        errors = await client.validate("assistants/helpful-bot")
        if errors:
            print(f"\nValidation errors: {errors}")
        else:
            print("\nPrompt validation passed!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the HTTP client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

