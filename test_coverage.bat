@echo off
rem Run tests with coverage
python -m pytest --cov=orka-reasoning --cov-report=xml --cov-report=term

rem Report status
if %ERRORLEVEL% EQU 0 (
    echo Tests passed successfully!
    echo Coverage report saved to coverage.xml
) else (
    echo Tests failed!
) 