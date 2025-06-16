@echo off
echo Building OrKa Documentation...
python -m pip install sphinx sphinx-rtd-theme
python docs/sphinx/build_docs.py
echo Done!
pause