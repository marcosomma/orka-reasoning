@echo off
rem Generate comprehensive coverage reports

echo Running tests with coverage reporting...
python -m pytest --cov=orka --cov-report=xml:coverage.xml --cov-report=term --cov-report=html:coverage_html

rem Verify coverage file exists
if exist coverage.xml (
    echo ✅ Coverage XML report generated successfully
    for %%F in (coverage.xml) do echo File size: %%~zF bytes
) else (
    echo ❌ Failed to generate coverage.xml
    exit /b 1
)

echo Coverage report generated successfully! 