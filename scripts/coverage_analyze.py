import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class FileCoverage:
    filename: str
    lines_valid: int
    lines_covered: int
    line_rate: float
    branch_rate: float

    @property
    def lines_missed(self) -> int:
        return self.lines_valid - self.lines_covered


def main() -> None:
    root = ET.parse("coverage.xml").getroot()

    total_valid = int(root.attrib.get("lines-valid", "0"))
    total_covered = int(root.attrib.get("lines-covered", "0"))
    base_rate = (total_covered / total_valid) if total_valid else 0.0

    rows: list[FileCoverage] = []
    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename")
        if not filename:
            continue

        lines = cls.findall("./lines/line")
        if not lines:
            continue

        lines_valid = len(lines)
        lines_covered = sum(1 for line in lines if int(line.attrib.get("hits", "0")) > 0)
        rows.append(
            FileCoverage(
                filename=filename,
                lines_valid=lines_valid,
                lines_covered=lines_covered,
                line_rate=float(cls.attrib.get("line-rate", "0")),
                branch_rate=float(cls.attrib.get("branch-rate", "0")),
            )
        )

    rows.sort(key=lambda r: (r.lines_missed, r.lines_valid), reverse=True)

    print("Top 25 files by missed lines:")
    for r in rows[:25]:
        cov = (r.lines_covered / r.lines_valid) if r.lines_valid else 0.0
        print(
            f"{r.lines_missed:5d} missed / {r.lines_valid:5d} lines  "
            f"({cov:6.1%} covered)  br={r.branch_rate:6.1%}  {r.filename}"
        )

    print(f"\nOverall line coverage: {total_covered}/{total_valid} ({base_rate:.2%})")

    target = base_rate + 0.05
    need_lines = max(0, int((target * total_valid) - total_covered + 0.9999))
    print(f"To gain +5.00pp, need ~{need_lines} additional covered lines (assuming lines-valid unchanged).")

    for n in (5, 10, 15, 25, 50):
        miss = sum(r.lines_missed for r in rows[:n])
        new_rate = (total_covered + miss) / total_valid
        print(f"If cover ALL missed in top {n:2d}: +{miss:4d} lines => {new_rate:.2%} (delta {(new_rate - base_rate):.2%})")


if __name__ == "__main__":
    main()
