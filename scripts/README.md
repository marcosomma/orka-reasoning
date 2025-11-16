# Documentation Maintenance Scripts

This directory contains automation scripts for maintaining OrKa's documentation.

## Available Scripts

### `maintain_docs.py`

Automated documentation maintenance tool with multiple functions:

#### Features

1. **Add Footer Navigation** (`--add-footers`)
   - Adds "← Previous | INDEX | Next →" navigation to all documentation files
   - Follows predefined reading order in `DOC_SEQUENCE`
   - Automatically calculates relative paths

2. **Update Last Updated Dates** (`--update-dates`)
   - Updates `> **Last Updated:** [DATE]` metadata in all docs
   - Only updates dates that differ from current date
   - Preserves existing metadata structure

3. **Check Internal Links** (`--check-links`)
   - Validates all internal markdown links
   - Reports broken links with file location
   - Skips external URLs and anchor links

4. **YAML Consolidation Plan** (`--consolidate-yaml`)
   - Shows consolidation recommendations for duplicate YAML guides
   - Lists files to be merged into primary `YAML_CONFIGURATION.md`
   - Provides timeline and action items

5. **Status Report** (`--status-report`)
   - Generates documentation health report
   - Counts files by status indicator (🟢🟡🔴🆕📦)
   - Identifies files missing status metadata

#### Usage

```powershell
# Run all maintenance tasks
python scripts/maintain_docs.py --all

# Run specific task
python scripts/maintain_docs.py --add-footers
python scripts/maintain_docs.py --update-dates
python scripts/maintain_docs.py --check-links
python scripts/maintain_docs.py --consolidate-yaml
python scripts/maintain_docs.py --status-report
```

#### Configuration

Edit `DOC_SEQUENCE` in the script to modify navigation order:

```python
DOC_SEQUENCE = [
    ("README.md", None),
    ("docs/index.md", "INDEX"),
    ("docs/quickstart.md", "Quickstart"),
    # ... add more files
]
```

#### Maintenance Schedule

Recommended usage:

- **Weekly:** Run `--check-links` to catch broken references
- **Monthly:** Run `--update-dates` before releases
- **Per Release:** Run `--all` to ensure full documentation health
- **As Needed:** Run `--consolidate-yaml` when planning doc reorganization

## Future Scripts (Planned)

### `generate_sitemap.py`
- Auto-generate sitemap XML for documentation website
- Update INDEX.md from actual file structure
- Detect new/removed files

### `validate_examples.py`
- Test all YAML examples in `examples/` directory
- Ensure examples match current API
- Generate example test report

### `check_api_docs.py`
- Validate docstrings against actual implementation
- Detect missing/outdated API documentation
- Generate API coverage report

## Contributing

When adding new maintenance scripts:

1. Follow existing naming convention (`verb_noun.py`)
2. Add comprehensive docstring and `--help` text
3. Include script documentation here in README
4. Add to CI/CD pipeline if appropriate
5. Test on Windows PowerShell and Unix shells

## Requirements

All scripts should:
- Work cross-platform (Windows/Linux/macOS)
- Use only standard library or documented dependencies
- Provide clear error messages
- Support dry-run mode for safety
- Log actions for auditability

## Contact

Questions or suggestions for new maintenance scripts?
- Open issue: [GitHub Issues](https://github.com/marcosomma/orka-core/issues)
- Tag with `documentation` and `tooling`
