#!/usr/bin/env python3
"""
Simple script to organize experiment logs based on loop counts and execution order

Logic:
1. Each output file has a 'loops' field indicating how many trace logs it used
2. Experiments run sequentially, so trace logs are in chronological order
3. Simply assign the next N trace logs to each experiment where N = loops
"""

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path


def parse_timestamp_from_filename(filename: str) -> datetime | None:
    """Extract datetime from trace log filename"""
    match = re.search(r"orka_trace_(\d{8})_(\d{6})\.json", filename)
    if match:
        date_str, time_str = match.groups()
        datetime_str = f"{date_str}_{time_str}"
        return datetime.strptime(datetime_str, "%Y%m%d_%H%M%S").replace(tzinfo=UTC)
    return None


def sanitize_folder_name(text: str, max_length: int = 50) -> str:
    """Convert question text to a safe folder name"""
    # Remove problematic characters and truncate
    sanitized = re.sub(r'[<>:"/\\|?*]', "", text)
    sanitized = re.sub(r"[^\w\s-]", "", sanitized)
    sanitized = re.sub(r"[-\s]+", "_", sanitized)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("_")
    return sanitized.lower()


def load_json_file(filepath: str) -> dict | None:
    """Load and parse a JSON file"""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return None


def main():
    """Main function to organize experiment logs"""

    print("🚀 Organizing experiment logs by loop count and execution order...")

    # Define paths
    current_dir = Path.cwd()
    logs_dir = current_dir / "logs"
    output_dir = logs_dir / "100_run_output"
    trace_dir = logs_dir / "100_run_logs"
    organized_dir = logs_dir / "100_run_organized"

    # Verify directories exist
    if not output_dir.exists() or not trace_dir.exists():
        print("❌ Required directories not found!")
        print(f"   Output dir: {output_dir}")
        print(f"   Trace dir: {trace_dir}")
        return

    # Create organized directory
    organized_dir.mkdir(exist_ok=True)

    # Load and sort output files by experiment number
    print("\n📄 Loading output files...")
    output_files = []
    for file_path in sorted(output_dir.glob("orka-reasoning-output_100_*.json")):
        data = load_json_file(file_path)
        if data:
            output_files.append(
                {
                    "filepath": file_path,
                    "run": data["run"],
                    "topic": data["topic"],
                    "loops": data["loops"],
                    "data": data,
                },
            )

    # Sort by run number to ensure correct order
    output_files.sort(key=lambda x: x["run"])
    print(f"   ✅ Loaded {len(output_files)} output files")

    # Load and sort trace files by timestamp (chronological order)
    print("\n📄 Loading trace log files...")
    trace_files = []
    for file_path in sorted(trace_dir.glob("orka_trace_*.json")):
        timestamp = parse_timestamp_from_filename(file_path.name)
        if timestamp:
            trace_files.append(
                {
                    "filepath": file_path,
                    "timestamp": timestamp,
                    "filename": file_path.name,
                },
            )

    # Sort by timestamp to get execution order
    trace_files.sort(key=lambda x: x["timestamp"])
    print(f"   ✅ Loaded {len(trace_files)} trace files")

    # Assign trace files to experiments based on loop counts
    print("\n🔗 Assigning trace files to experiments...")

    trace_index = 0
    total_assigned = 0

    summary_data = {
        "organization_date": datetime.now(UTC).isoformat(),
        "total_experiments": len(output_files),
        "total_trace_files": len(trace_files),
        "experiments": [],
    }

    for output in output_files:
        run_num = output["run"]
        topic = output["topic"]
        loops = output["loops"]

        print(f"\n📂 Experiment {run_num:03d}: {topic[:60]}...")
        print(f"   Expected loops: {loops}")

        # Create experiment folder
        folder_name = f"experiment_{run_num:03d}_{sanitize_folder_name(topic)}"
        exp_folder = organized_dir / folder_name
        exp_folder.mkdir(exist_ok=True)

        # Copy final result file
        result_dest = exp_folder / "final_result.json"
        shutil.copy2(output["filepath"], result_dest)

        # Assign the next N trace files where N = loops
        assigned_traces = []
        for i in range(loops):
            if trace_index < len(trace_files):
                trace = trace_files[trace_index]

                # Copy trace file
                trace_dest = exp_folder / f"trace_loop_{i + 1:02d}.json"
                shutil.copy2(trace["filepath"], trace_dest)

                assigned_traces.append(
                    {
                        "original_file": trace["filename"],
                        "new_file": f"trace_loop_{i + 1:02d}.json",
                        "timestamp": trace["timestamp"].isoformat(),
                    },
                )

                trace_index += 1
                total_assigned += 1
            else:
                print(f"   ⚠️  Missing trace file for loop {i + 1}")

        print(f"   ✅ Assigned {len(assigned_traces)}/{loops} trace files")

        # Create experiment metadata
        metadata = {
            "experiment_number": run_num,
            "topic": topic,
            "expected_loops": loops,
            "assigned_trace_files": len(assigned_traces),
            "timestamp_range": {
                "first": assigned_traces[0]["timestamp"] if assigned_traces else None,
                "last": assigned_traces[-1]["timestamp"] if assigned_traces else None,
            },
            "files": {
                "final_result": "final_result.json",
                "traces": assigned_traces,
            },
        }

        metadata_file = exp_folder / "experiment_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

        # Add to summary
        summary_data["experiments"].append(
            {
                "number": run_num,
                "folder": folder_name,
                "topic": topic,
                "expected_loops": loops,
                "assigned_traces": len(assigned_traces),
                "timestamp_range": metadata["timestamp_range"],
            },
        )

    # Create overall summary
    summary_file = organized_dir / "organization_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, default=str)

    # Final statistics
    unassigned_traces = len(trace_files) - total_assigned

    print("\n✅ Organization completed!")
    print("\n📊 Final Statistics:")
    print(f"   • Experiments organized: {len(output_files)}")
    print(f"   • Total trace files: {len(trace_files)}")
    print(f"   • Trace files assigned: {total_assigned}")
    print(f"   • Unassigned trace files: {unassigned_traces}")
    print(f"   • Success rate: {(total_assigned / len(trace_files) * 100):.1f}%")
    print(f"\n📁 Organized structure created in: {organized_dir}")
    print(f"📄 Summary report: {summary_file}")

    if unassigned_traces > 0:
        print(f"\n⚠️  Note: {unassigned_traces} trace files were not assigned.")
        print("   This might be due to experiments that didn't complete or extra log files.")


if __name__ == "__main__":
    main()
