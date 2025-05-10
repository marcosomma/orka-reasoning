#!/bin/bash
# Generate comprehensive coverage reports

echo "Running tests with coverage reporting..."
python -m pytest --cov=orka --cov-report=xml:coverage.xml --cov-report=term --cov-report=html:coverage_html

# Verify coverage file exists
if [ -f "coverage.xml" ]; then
    echo "✅ Coverage XML report generated successfully"
    echo "File size: $(stat -c%s coverage.xml) bytes"
else 
    echo "❌ Failed to generate coverage.xml"
    exit 1
fi

echo "Coverage report generated successfully!" 