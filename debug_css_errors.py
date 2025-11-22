from textual.css.stylesheet import Stylesheet, StylesheetParseError
from pathlib import Path

print("Detailed CSS validation...\n")

for theme_name, theme_file in [
    ("default", "textual_styles.tcss"),
    ("vintage", "textual_styles_vintage.tcss"),
    ("dark", "textual_styles_dark.tcss")
]:
    css_path = f'orka/tui/{theme_file}'
    print(f"Testing {theme_name} ({theme_file}):")
    
    try:
        s = Stylesheet()
        s.read(css_path)
        print(f"  ✓ SUCCESS - {len(s.rules)} rules loaded\n")
    except StylesheetParseError as e:
        print(f"  ✗ PARSE ERROR")
        if hasattr(e, 'errors'):
            errors = e.errors
            if hasattr(errors, '__iter__'):
                print(f"    Total errors: {len(list(errors))}")
                for err in list(errors)[:5]:
                    print(f"      • {err}")
            else:
                print(f"    {errors}")
        print()
    except Exception as e:
        print(f"  ✗ OTHER ERROR: {type(e).__name__}")
        print(f"    {e}\n")
