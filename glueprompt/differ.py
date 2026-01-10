"""Prompt diff and comparison utilities."""

from typing import Any

from difflib import unified_diff

from glueprompt.models.prompt import Prompt


class PromptDiffer:
    """Utilities for comparing and diffing prompts."""

    @staticmethod
    def diff_prompts(
        prompt1: Prompt,
        prompt2: Prompt,
        prompt_name: str = "prompt",
    ) -> str:
        """Generate a unified diff between two prompts.

        Args:
            prompt1: First prompt
            prompt2: Second prompt
            prompt_name: Name to use in diff header

        Returns:
            Unified diff string
        """
        lines1 = prompt1.template.splitlines(keepends=True)
        lines2 = prompt2.template.splitlines(keepends=True)

        diff_lines = unified_diff(
            lines1,
            lines2,
            fromfile=f"{prompt_name} (v{prompt1.metadata.version})",
            tofile=f"{prompt_name} (v{prompt2.metadata.version})",
            lineterm="",
        )

        return "\n".join(diff_lines)

    @staticmethod
    def compare_metadata(prompt1: Prompt, prompt2: Prompt) -> dict[str, Any]:
        """Compare metadata between two prompts.

        Args:
            prompt1: First prompt
            prompt2: Second prompt

        Returns:
            Dictionary with comparison results
        """
        return {
            "name_changed": prompt1.metadata.name != prompt2.metadata.name,
            "version_changed": prompt1.metadata.version != prompt2.metadata.version,
            "description_changed": prompt1.metadata.description != prompt2.metadata.description,
            "author_changed": prompt1.metadata.author != prompt2.metadata.author,
            "tags_changed": set(prompt1.metadata.tags) != set(prompt2.metadata.tags),
            "variables_added": set(prompt2.variables.keys()) - set(prompt1.variables.keys()),
            "variables_removed": set(prompt1.variables.keys()) - set(prompt2.variables.keys()),
            "variables_changed": {
                var: {
                    "old": prompt1.variables[var].model_dump() if var in prompt1.variables else None,
                    "new": prompt2.variables[var].model_dump() if var in prompt2.variables else None,
                }
                for var in set(prompt1.variables.keys()) & set(prompt2.variables.keys())
                if prompt1.variables[var] != prompt2.variables[var]
            },
        }

