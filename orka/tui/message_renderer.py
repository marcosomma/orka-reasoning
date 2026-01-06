# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Message Renderer - Advanced Content Formatting for OrKa TUI

This module provides sophisticated rendering capabilities for agent responses,
memory content, and structured data within the Terminal User Interface.

Features:
- Status icon rendering (Y/N/▸/⋯)
- Rich syntax highlighting for JSON/YAML
- Markdown rendering support
- Metadata box formatting
- Content type auto-detection
"""

from typing import Dict, Any, Optional, List
import json
import re
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
from rich.console import RenderableType
from rich import box


class VintageMessageRenderer:
    """
    Renders agent messages and memory content with vintage terminal aesthetics.
    
    Provides multi-format rendering including:
    - JSON/YAML syntax highlighting
    - Markdown content rendering
    - Status icons and metadata boxes
    - Intelligent content type detection
    """
    
    # Status icon mapping
    STATUS_ICONS = {
        "success": "Y",
        "error": "N",
        "pending": "⋯",
        "running": "▸",
        "unknown": "?"
    }
    
    def __init__(self, theme: str = "default"):
        """
        Initialize the message renderer.
        
        Args:
            theme: Theme name ('default', 'vintage', 'dark')
        """
        self.theme = theme
    
    def render_agent_response(
        self, 
        response: Dict[str, Any],
        max_content_length: int = 2000
    ) -> str:
        """
        Render a complete agent response with status, content, and metadata.
        
        Args:
            response: Agent response dictionary containing:
                - agent_id: Agent identifier
                - status: Response status (success/error/pending)
                - output: Response content
                - metadata: Additional metadata
                - tokens_used: Token count (optional)
            max_content_length: Maximum content length before truncation
        
        Returns:
            Formatted rich markup string
        """
        agent_id = response.get("agent_id", "Unknown")
        status = response.get("status", "unknown")
        output = response.get("output", "")
        metadata = response.get("metadata", {})
        tokens = response.get("tokens_used", 0)
        
        # Build header with status indicator
        status_icon = self._get_status_icon(status)
        status_display = self._format_status(status)
        
        header_parts = [
            f"[{status_icon}]",
            f"[cyan bold]{agent_id}[/]",
            f"▸ {status_display}"
        ]
        
        if tokens > 0:
            header_parts.append(f"▸ [dim]{tokens} tokens[/dim]")
        
        header = " ".join(header_parts)
        
        # Format content with intelligent rendering
        content = self._format_content(output, max_content_length)
        
        # Render metadata box if present
        metadata_box = ""
        if metadata:
            metadata_box = "\n\n" + self._render_metadata_box(metadata)
        
        return f"{header}\n\n{content}{metadata_box}"
    
    def render_memory_content(
        self,
        memory_data: Dict[str, Any],
        show_full_key: bool = False
    ) -> str:
        """
        Render memory content with metadata and system information.
        
        Args:
            memory_data: Memory entry dictionary
            show_full_key: Whether to show full memory key or truncated
        
        Returns:
            Formatted rich markup string
        """
        # Extract data
        memory_key = memory_data.get("memory_key", "unknown")
        content = memory_data.get("content", "")
        metadata = memory_data.get("metadata", {})
        memory_type = memory_data.get("memory_type", "unknown")
        node_id = memory_data.get("node_id", "")
        importance_score = memory_data.get("importance_score", 0.0)
        
        # Format key
        if not show_full_key and len(memory_key) > 50:
            key_display = f"{memory_key[:20]}...{memory_key[-20:]}"
        else:
            key_display = memory_key
        
        # Build output
        output_parts = [
            f"[bold blue]Memory: {key_display}[/bold blue]",
            "",
            "[bold green][FILE] CONTENT:[/bold green]",
            self._format_content(content, max_content_length=2000),
        ]
        
        # Add metadata if present
        if metadata:
            output_parts.extend([
                "",
                "[bold yellow][LIST] METADATA:[/bold yellow]",
                self._format_metadata(metadata)
            ])
        
        # Add system information
        output_parts.extend([
            "",
            "[bold cyan][TAG]️ SYSTEM INFO:[/bold cyan]",
            f"[cyan]Type:[/cyan] {memory_type}",
        ])
        
        if node_id:
            output_parts.append(f"[cyan]Node ID:[/cyan] {node_id}")
        
        if importance_score > 0:
            output_parts.append(f"[cyan]Importance:[/cyan] {importance_score:.2f}")
        
        return "\n".join(output_parts)
    
    def _get_status_icon(self, status: str) -> str:
        """Get status icon for a given status."""
        status_lower = str(status).lower()
        return self.STATUS_ICONS.get(status_lower, self.STATUS_ICONS["unknown"])
    
    def _format_status(self, status: str) -> str:
        """Format status with color coding."""
        status_lower = str(status).lower()
        
        if status_lower == "success":
            return "[bold green]SUCCESS[/bold green]"
        elif status_lower == "error":
            return "[bold red]ERROR[/bold red]"
        elif status_lower == "pending":
            return "[bold yellow]PENDING[/bold yellow]"
        elif status_lower == "running":
            return "[bold blue]RUNNING[/bold blue]"
        else:
            return f"[dim]{status.upper()}[/dim]"
    
    def _format_content(
        self, 
        content: Any, 
        max_content_length: int = 2000
    ) -> str:
        """
        Format content with intelligent rendering based on detected type.
        
        Supports:
        - JSON objects with syntax highlighting
        - YAML content
        - Markdown text
        - Plain text
        """
        # Handle None or empty
        if content is None:
            return "[dim italic]No content[/dim italic]"
        
        # Convert to string if needed
        content_str = str(content) if not isinstance(content, str) else content
        
        # Truncate if too long
        if len(content_str) > max_content_length:
            content_str = content_str[:max_content_length] + "\n[dim]...(truncated)[/dim]"
        
        # Detect content type and render appropriately
        content_type = self._detect_content_type(content_str)
        
        if content_type == "json":
            return self._render_json(content_str)
        elif content_type == "markdown":
            return self._render_markdown(content_str)
        elif content_type == "yaml":
            return self._render_yaml(content_str)
        else:
            return self._render_plain_text(content_str)
    
    def _detect_content_type(self, content: str) -> str:
        """
        Detect content type from string.
        
        Returns:
            'json', 'yaml', 'markdown', or 'plain'
        """
        content_stripped = content.strip()
        
        # Check for JSON
        if (content_stripped.startswith('{') and content_stripped.endswith('}')) or \
           (content_stripped.startswith('[') and content_stripped.endswith(']')):
            try:
                json.loads(content_stripped)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Check for markdown indicators
        markdown_patterns = [
            r'^#{1,6}\s',  # Headers
            r'\[.+\]\(.+\)',  # Links
            r'```',  # Code blocks
            r'^\*\s',  # Unordered lists
            r'^\d+\.\s'  # Ordered lists
        ]
        
        if any(re.search(pattern, content, re.MULTILINE) for pattern in markdown_patterns):
            return "markdown"
        
        # Check for YAML indicators
        if re.search(r'^\w+:\s*.+$', content, re.MULTILINE) and \
           not content_stripped.startswith('{'):
            return "yaml"
        
        return "plain"
    
    def _render_json(self, content: str) -> str:
        """Render JSON with syntax highlighting using Rich Syntax."""
        try:
            # Parse and pretty-print JSON
            parsed = json.loads(content)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            
            # Note: In TUI, we return markup string, not Syntax object
            # The calling code can use Syntax if needed
            return f"[white]{formatted}[/white]"
        except (json.JSONDecodeError, ValueError):
            # Fallback to plain text
            return f"[white]{content}[/white]"
    
    def _render_yaml(self, content: str) -> str:
        """Render YAML content with basic formatting."""
        # Add basic indentation coloring
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                formatted_lines.append(f"[cyan]{key}:[/cyan]{value}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _render_markdown(self, content: str) -> str:
        """Render markdown content with basic formatting."""
        # Simple markdown rendering using markup
        # Replace headers
        content = re.sub(r'^(#{1,6})\s*(.+)$', r'[bold]\2[/bold]', content, flags=re.MULTILINE)
        
        # Replace bold
        content = re.sub(r'\*\*(.+?)\*\*', r'[bold]\1[/bold]', content)
        
        # Replace italic
        content = re.sub(r'\*(.+?)\*', r'[italic]\1[/italic]', content)
        
        # Replace code
        content = re.sub(r'`(.+?)`', r'[cyan]\1[/cyan]', content)
        
        return content
    
    def _render_plain_text(self, content: str) -> str:
        """Render plain text with minimal formatting."""
        # Add prompt-style indentation
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            if i == 0:
                formatted_lines.append(f"  [bold green]>[/bold green] {line}")
            else:
                formatted_lines.append(f"    {line}")
        
        return '\n'.join(formatted_lines)
    
    def _render_metadata_box(self, metadata: Dict[str, Any]) -> str:
        """
        Render metadata in a classic box format.
        
        Args:
            metadata: Metadata dictionary
        
        Returns:
            Formatted metadata string with box borders
        """
        lines = ["┌─ [bold]Metadata[/bold] " + "─" * 40 + "┐"]
        
        for key, value in metadata.items():
            if isinstance(value, dict):
                lines.append(f"│ [cyan]{key}:[/cyan]")
                for sub_key, sub_value in value.items():
                    lines.append(f"│   [dim]{sub_key}:[/dim] {sub_value}")
            else:
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                lines.append(f"│ [cyan]{key}:[/cyan] {value_str}")
        
        lines.append("└" + "─" * 58 + "┘")
        
        return '\n'.join(lines)
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for inline display."""
        formatted_lines = []
        
        for key, value in metadata.items():
            if isinstance(value, dict):
                formatted_lines.append(f"[cyan]{key}:[/cyan]")
                for sub_key, sub_value in value.items():
                    formatted_lines.append(f"  [dim]{sub_key}:[/dim] {sub_value}")
            else:
                formatted_lines.append(f"[cyan]{key}:[/cyan] {value}")
        
        return '\n'.join(formatted_lines)


# Convenience function for quick rendering
def render_agent_response(response: Dict[str, Any], theme: str = "default") -> str:
    """
    Convenience function to render an agent response.
    
    Args:
        response: Agent response dictionary
        theme: Theme name
    
    Returns:
        Formatted markup string
    """
    renderer = VintageMessageRenderer(theme=theme)
    return renderer.render_agent_response(response)


def render_memory_content(memory_data: Dict[str, Any], theme: str = "default") -> str:
    """
    Convenience function to render memory content.
    
    Args:
        memory_data: Memory entry dictionary
        theme: Theme name
    
    Returns:
        Formatted markup string
    """
    renderer = VintageMessageRenderer(theme=theme)
    return renderer.render_memory_content(memory_data)
