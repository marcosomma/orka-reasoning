import * as d3 from "d3";
import { AgentNode } from "../../types";

export function setupNodeDragHandler(
  g: d3.Selection<SVGGElement, unknown, null, undefined>,
  agents: AgentNode[],
  links: { source: string; target: string }[]
) {
  return d3.drag<SVGGElement, AgentNode>()
    .on("drag", function (event, d) {
      d.x = event.x;
      d.y = event.y;
      d3.select(this).attr("transform", `translate(${d.x}, ${d.y})`);

      g.selectAll(".link")
        .attr("x1", (l) => agents.find((n) => n.id === (l as any).source)?.x || 0)
        .attr("y1", (l) => agents.find((n) => n.id === (l as any).source)?.y || 0)
        .attr("x2", (l) => agents.find((n) => n.id === (l as any).target)?.x || 0)
        .attr("y2", (l) => agents.find((n) => n.id === (l as any).target)?.y || 0);
    });
}
