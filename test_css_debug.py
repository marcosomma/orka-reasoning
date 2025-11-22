from textual.css.stylesheet import Stylesheet
from pathlib import Path

print("Testing vintage CSS in detail...\n")

css_file = 'orka/tui/textual_styles_vintage.tcss'
try:
    s = Stylesheet()
    result = s.read(css_file)
    print(f'Success! Rules: {len(s.rules)}')
except Exception as e:
    print(f'Exception: {type(e).__name__}')
    if hasattr(e, 'errors') and hasattr(e.errors, 'errors'):
        print(f'\nTotal errors: {len(e.errors.errors)}\n')
        for i, err in enumerate(e.errors.errors[:10], 1):  # First 10 errors
            print(f'{i}. {err}')



