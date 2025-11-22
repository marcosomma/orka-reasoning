"""
Generate all 3 theme CSS files from the original template,
preserving the complete structure but changing only colors.
"""
import re

# Read original template (UTF-16LE with BOM from git show)
try:
    with open('orka/tui/textual_styles_original.tcss', encoding='utf-16-le') as f:
        template = f.read()
except:
    # Fallback to UTF-8
    with open('orka/tui/textual_styles_original.tcss', encoding='utf-8', errors='ignore') as f:
        template = f.read()

# Color schemes for each theme
themes = {
    'default': {
        '$text-muted': '#8b949e',
        '$background': '#0d1117',
        '$text': '#c9d1d9',
        '$primary': '#58a6ff',
        '$panel': '#161b22',
        '$surface': '#0d1117',
        '$accent': '#79c0ff',
        '$success': '#3fb950',
        '$secondary': '#bc8cff',
        '$warning': '#d29922',
        '$error': '#f85149',
    },
    'vintage': {
        '$text-muted': '#00aa00',
        '$background': '#000000',
        '$text': '#aaffaa',
        '$primary': '#00ff00',
        '$panel': '#001100',
        '$surface': '#000000',
        '$accent': '#ccffcc',
        '$success': '#00ff00',
        '$secondary': '#00ff00',
        '$warning': '#ffaa00',
        '$error': '#ff3333',
    },
    'dark': {
        '$text-muted': '#8b949e',
        '$background': '#0d1117',
        '$text': '#c9d1d9',
        '$primary': '#58a6ff',
        '$panel': '#161b22',
        '$surface': '#0d1117',
        '$accent': '#79c0ff',
        '$success': '#3fb950',
        '$secondary': '#bc8cff',
        '$warning': '#d29922',
        '$error': '#f85149',
    }
}

def generate_theme(template_content, color_map, theme_name):
    """Generate CSS by replacing variables with theme colors."""
    content = template_content
    
    # Replace variables (order matters - longer names first)
    for var_name in sorted(color_map.keys(), key=len, reverse=True):
        color = color_map[var_name]
        # Use word boundary to avoid partial replacements
        pattern = re.escape(var_name) + r'(?![a-z-])'
        content = re.sub(pattern, color, content)
    
    # Remove opacity percentages (not supported by Textual)
    content = re.sub(r'(#[0-9a-fA-F]{6})\s+\d+%', r'\1', content)
    
    # Update header comment
    if theme_name == 'vintage':
        header = """/* ╔═══════════════════════════════════════════════════════════════════════╗
   ║                    ORKA VINTAGE THEME - CRT AESTHETIC                 ║
   ║         Classic Green Phosphor Terminal Style (Full Layout)           ║
   ╚═══════════════════════════════════════════════════════════════════════╝ */"""
    elif theme_name == 'dark':
        header = """/* ╔═══════════════════════════════════════════════════════════════════════╗
   ║                     ORKA DARK THEME - MODERN AESTHETIC                ║
   ║          Sleek Dark Mode with Cyan Accents (Full Layout)              ║
   ╚═══════════════════════════════════════════════════════════════════════╝ */"""
    else:
        header = "/* OrKa Textual Application Styles - Default Theme (Full Layout) */"
    
    content = re.sub(r'/\*.*?\*/', header, content, count=1, flags=re.DOTALL)
    
    return content

# Generate all three themes
for theme_name, colors in themes.items():
    css_content = generate_theme(template, colors, theme_name)
    
    # Determine output filename
    if theme_name == 'default':
        filename = 'orka/tui/textual_styles.tcss'
    else:
        filename = f'orka/tui/textual_styles_{theme_name}.tcss'
    
    # Write file (UTF-8 without BOM)
    with open(filename, 'w', encoding='utf-8') as f:
        # Strip BOM if present from template
        content_clean = css_content.lstrip('\ufeff')
        f.write(content_clean)
    
    print(f'✓ Generated {theme_name} theme: {len(css_content)} chars')

print('\n✅ All themes generated with complete layout structure!')
