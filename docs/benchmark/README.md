![chart](https://raw.githubusercontent.com/marcosomma/orka-reasoning/refs/heads/master/docs/benchmark/GSM8K_Model_Accuracies.png)


## Usage

1. Activate your Orka environment:
```bash
conda activate orka
```

2. Run the benchmark:
```bash
python run_benchmark.py ../examples/benchmark_comparison.yml ../PRIVATE/test.jsonl
```

## Output Files

The script generates several output files:

- `benchmark_results_TIMESTAMP.log`: Detailed logging of the benchmark run
- `benchmark_report_TIMESTAMP.csv`: Detailed results for each test case
- `benchmark_report_TIMESTAMP_summary.json`: Summary statistics

## Report Format

The CSV report includes:
- Question
- Reference Answer
- Orka Answer
- Similarity Score (0.0-1.0)
- Analysis
- Success/Error Status

The JSON summary includes:
- Total test cases
- Success/failure counts
- Average similarity score
- Timestamp

## Error Handling

- Failed test cases are logged but don't stop the benchmark
- Each failure is documented with the specific error message
- The final report includes both successful and failed cases
