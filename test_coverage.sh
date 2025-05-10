#!/bin/bash
# Run tests with coverage
python -m pytest --cov=orka-reasoning --cov-report=xml --cov-report=term

# Report status
if [ $? -eq 0 ]; then
    echo "Tests passed successfully!"
    echo "Coverage report saved to coverage.xml"
else
    echo "Tests failed!"
fi 