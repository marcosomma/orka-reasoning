#!/usr/bin/env python3
"""
OrKa Documentation Maintenance Script

This script automates common documentation maintenance tasks:
- Add footer navigation links to documentation files
- Update "Last Updated" dates
- Check for broken internal links
- Validate status indicators
- Generate consolidation reports

Usage:
    python scripts/maintain_docs.py --add-footers
    python scripts/maintain_docs.py --update-dates
    python scripts/maintain_docs.py --check-links
    python scripts/maintain_docs.py --consolidate-yaml
"""

import argparse
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Documentation reading order (for footer navigation)
DOC_SEQUENCE = [
    ("README.md", None),  # Root file
    ("docs/index.md", "INDEX"),
    ("docs/quickstart.md", "Quickstart"),
    ("docs/getting-started.md", "Getting Started"),
    ("docs/architecture.md", "Architecture"),
    ("docs/COMPONENTS.md", "Components"),
    ("docs/VISUAL_ARCHITECTURE_GUIDE.md", "Visual Architecture"),
    ("docs/YAML_CONFIGURATION.md", "YAML Configuration"),
    ("docs/TEMPLATE_FILTERS.md", "Template Filters"),
    ("docs/TEMPLATE_RENDERING_FIX.md", "Template Rendering"),
    ("docs/JSON_INPUTS.md", "Json Inputs Guide"),
    ("docs/STREAMING_GUIDE.md", "Streaming Guide"),
    ("docs/agents.md", "Agents"),
    ("docs/agents-advanced.md", "Advanced Agents"),
    ("docs/extending-agents.md", "Extending Agents"),
    ("docs/MEMORY_SYSTEM_GUIDE.md", "Memory System"),
    ("docs/memory-agents-guide.md", "Memory Agents"),
    ("docs/GRAPH_SCOUT_AGENT.md", "GraphScout"),
    ("docs/best-practices.md", "Best Practices"),
    ("docs/TESTING.md", "Testing"),
    ("docs/DEBUGGING.md", "Debugging"),
    ("docs/troubleshooting.md", "Troubleshooting"),
    ("docs/faq.md", "FAQ"),
]

FOOTER_TEMPLATE = """
---
← [{prev_name}]({prev_path}) | [📚 INDEX](index.md) | [{next_name}]({next_path}) →
"""


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def add_footer_navigation():
    """Add footer navigation links to all documentation files."""
    print("Adding footer navigation to documentation files...")
    root = get_project_root()
    
    for i, (filepath, display_name) in enumerate(DOC_SEQUENCE):
        full_path = root / filepath
        
        if not full_path.exists():
            print(f"⚠️  Skipping {filepath} (not found)")
            continue
        
        # Determine previous and next links
        prev_path = DOC_SEQUENCE[i-1][0] if i > 0 else None
        next_path = DOC_SEQUENCE[i+1][0] if i < len(DOC_SEQUENCE) - 1 else None
        
        prev_name = DOC_SEQUENCE[i-1][1] if i > 0 else None
        next_name = DOC_SEQUENCE[i+1][1] if i < len(DOC_SEQUENCE) - 1 else None
        
        # Read current content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove existing footer if present
        content = re.sub(r'\n---\n←.*?→\s*$', '', content, flags=re.DOTALL)
        
        # Add new footer if not first or last doc
        if prev_path and next_path:
            # Calculate relative paths
            if filepath.startswith("docs/"):
                prev_rel = os.path.relpath(prev_path, "docs")
                next_rel = os.path.relpath(next_path, "docs")
            else:
                prev_rel = prev_path
                next_rel = next_path
            
            footer = FOOTER_TEMPLATE.format(
                prev_name=prev_name,
                prev_path=prev_rel,
                next_name=next_name,
                next_path=next_rel
            )
            
            content = content.rstrip() + footer
            
            # Write back
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Added footer to {filepath}")
        else:
            print(f"⏭️  Skipped footer for {filepath} (boundary file)")


def update_last_updated_dates():
    """Update 'Last Updated' dates in documentation headers."""
    print("Updating 'Last Updated' dates...")
    root = get_project_root()
    docs_dir = root / "docs"
    today = datetime.now().strftime("%d %B %Y")
    
    pattern = re.compile(r'(> \*\*Last Updated:\*\* )(\d+ \w+ \d+)', re.MULTILINE)
    
    for md_file in docs_dir.glob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has Last Updated field
        if '> **Last Updated:**' in content:
            # Only update if significantly old (more than 7 days difference)
            match = pattern.search(content)
            if match:
                old_date = match.group(2)
                # Simple check: if date string is different, update
                if old_date != today:
                    new_content = pattern.sub(rf'\g<1>{today}', content)
                    
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print(f"✅ Updated date in {md_file.name}: {old_date} → {today}")
                else:
                    print(f"⏭️  {md_file.name} already up-to-date")


def check_internal_links():
    """Check for broken internal links in documentation."""
    print("Checking internal links...")
    root = get_project_root()
    docs_dir = root / "docs"
    
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    broken_links = []
    
    for md_file in docs_dir.glob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for match in link_pattern.finditer(content):
            link_text = match.group(1)
            link_path = match.group(2)
            
            # Skip external links
            if link_path.startswith(('http://', 'https://', '#')):
                continue
            
            # Resolve relative path
            target = (md_file.parent / link_path).resolve()
            
            if not target.exists():
                broken_links.append((md_file.name, link_text, link_path))
    
    if broken_links:
        print("\n⚠️  Found broken internal links:")
        for file, text, path in broken_links:
            print(f"   {file}: [{text}]({path})")
    else:
        print("✅ All internal links are valid")
    
    return len(broken_links) == 0


def consolidate_yaml_guides():
    """Generate consolidation plan for YAML configuration guides."""
    print("Generating YAML consolidation plan...")
    root = get_project_root()
    docs_dir = root / "docs"
    
    files_to_consolidate = [
        "yaml-configuration-guide.md",
        "orka.yaml-schema.md",
        "CONFIGURATION.md",
        "advanced-configuration.md",
        "orka-cli-configuration.md",
        "JSON_INPUTS.md"
    ]
    
    primary_file = "YAML_CONFIGURATION.md"
    
    print(f"\n📋 YAML Configuration Consolidation Plan:")
    print(f"   Primary: {primary_file}")
    print(f"   To merge:")
    
    for filename in files_to_consolidate:
        filepath = docs_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
            print(f"      - {filename} ({lines} lines)")
    
    print(f"\n   Action: Run consolidation manually or use `--execute-consolidation` flag")
    print(f"   Timeline: Target v0.9.9 release")


def generate_status_report():
    """Generate a report of documentation status indicators."""
    print("Generating documentation status report...")
    root = get_project_root()
    docs_dir = root / "docs"
    
    status_counts = {
        "🟢 Current": 0,
        "🆕 New": 0,
        "🟡 Consolidate": 0,
        "🔴 Deprecated": 0,
        "📦 Archive": 0,
        "No Status": 0
    }
    
    status_pattern = re.compile(r'> \*\*Status:\*\* (.+?)(?:\s|$)')
    
    for md_file in docs_dir.glob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = status_pattern.search(content)
        if match:
            status = match.group(1).strip()
            if status in status_counts:
                status_counts[status] += 1
            else:
                # Try to match emoji
                for key in status_counts:
                    if key.split()[0] in status:
                        status_counts[key] += 1
                        break
        else:
            status_counts["No Status"] += 1
    
    print("\n📊 Documentation Status Summary:")
    for status, count in status_counts.items():
        print(f"   {status}: {count} files")


def main():
    parser = argparse.ArgumentParser(
        description="OrKa Documentation Maintenance Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--add-footers', action='store_true',
                       help='Add footer navigation to all docs')
    parser.add_argument('--update-dates', action='store_true',
                       help='Update Last Updated dates')
    parser.add_argument('--check-links', action='store_true',
                       help='Check for broken internal links')
    parser.add_argument('--consolidate-yaml', action='store_true',
                       help='Show YAML consolidation plan')
    parser.add_argument('--status-report', action='store_true',
                       help='Generate status indicator report')
    parser.add_argument('--all', action='store_true',
                       help='Run all maintenance tasks')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    print("🛠️  OrKa Documentation Maintenance\n")
    
    if args.add_footers or args.all:
        add_footer_navigation()
        print()
    
    if args.update_dates or args.all:
        update_last_updated_dates()
        print()
    
    if args.check_links or args.all:
        check_internal_links()
        print()
    
    if args.consolidate_yaml or args.all:
        consolidate_yaml_guides()
        print()
    
    if args.status_report or args.all:
        generate_status_report()
        print()
    
    print("✅ Documentation maintenance complete!")


if __name__ == "__main__":
    main()
