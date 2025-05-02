import * as d3 from "d3";
import { AgentNode } from "../../types";
import { colorsByType } from "./contants";

export default function LinkRenderer(
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  links: { source: string; target: string }[],
  agents: AgentNode[],
  setLinks: React.Dispatch<React.SetStateAction<{ source: string; target: string }[]>>,
  selectedLinkRef: React.MutableRefObject<{ source: string; target: string } | null>
) {
  g.selectAll(".link")
    .data(links)
    .enter()
    .append("line")
    .attr("class", "link")
    .attr("stroke-width", 4)
    .attr(
      "stroke",
      (d) => colorsByType[(d as any).source.split("_")[0] as string] || "#555"
    )
    .attr("x1", (d) => agents.find((n) => n.id === d.source)?.x || 0)
    .attr("y1", (d) => agents.find((n) => n.id === d.source)?.y || 0)
    .attr("x2", (d) => agents.find((n) => n.id === d.target)?.x || 0)
    .attr("y2", (d) => agents.find((n) => n.id === d.target)?.y || 0)
    .on("click", function (event, d) {
      event.stopPropagation();
      selectedLinkRef.current = d as { source: string; target: string };

      // Highlight selected link
      g.selectAll(".link")
        .attr("stroke", (l) =>
          l === selectedLinkRef.current
            ? "red"
            : colorsByType[(l as any).source.split("_")[0] as string] || "#555"
        )
        .attr("stroke-width", (l) =>
          l === selectedLinkRef.current ? 6 : 4
        );
    });
}
