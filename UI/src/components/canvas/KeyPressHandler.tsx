import * as d3 from "d3";
import { AgentNode } from "../../types";
import { colorsByType } from "./contants";

export function setupKeyPressHandler(
  agents: AgentNode[],
  setAgents: React.Dispatch<React.SetStateAction<AgentNode[]>>,
  links: { source: string; target: string }[],
  setLinks: React.Dispatch<React.SetStateAction<{ source: string; target: string }[]>>,
  selectedNode: string | null,
  selectedLinkRef: React.MutableRefObject<{ source: string; target: string } | null>,
  setSelectedNode: React.Dispatch<React.SetStateAction<string | null>>,
  ref: React.RefObject<SVGSVGElement>
) {
  d3.select(window).on("keydown", (event) => {
    const activeElement = document.activeElement;
    if (activeElement && activeElement.tagName !== "BODY") return;

    if (event.key === "Backspace") {
      if (selectedNode) {
        setAgents(agents.filter((agent) => agent.id !== selectedNode));
        setLinks(
          links.filter(
            (link) => link.source !== selectedNode && link.target !== selectedNode
          )
        );
        setSelectedNode(null);
      } else if (selectedLinkRef.current) {
        setLinks(
          links.filter(
            (l) =>
              !(
                l.source === selectedLinkRef.current!.source &&
                l.target === selectedLinkRef.current!.target
              )
          )
        );
        selectedLinkRef.current = null;

        // Reset link stroke colors after deletion
        d3.select(ref.current)
          ?.selectAll(".link")
          .attr("stroke", (l: any) => colorsByType[l.source.split("_")[0]] || "#555")
          .attr("stroke-width", 4);
      }
    }
  });
}
