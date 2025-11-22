import re

# Read file
with open('orka/tui/textual_styles.tcss', encoding='utf-8') as f:
    content = f.read()

# Replace CSS variables with concrete colors (order matters!)
replacements = [
    (r'\$text-muted\b', '#8b949e'),
    (r'\$background\b', '#0d1117'),
    (r'\$text\b', '#c9d1d9'),
    (r'\$primary\b', '#58a6ff'),
    (r'\$panel\b', '#161b22'),
    (r'\$surface\b', '#0d1117'),
    (r'\$accent\b', '#58a6ff'),
    (r'\$success\b', '#3fb950'),
    (r'\$secondary\b', '#bc8cff'),
    (r'\$warning\b', '#d29922'),
    (r'\$error\b', '#f85149'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Write back
with open('orka/tui/textual_styles.tcss', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ CSS variables replaced")
