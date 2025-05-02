import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { AgentNode } from "../../types";
import NodeRenderer from "./NodeRenderer";
import LinkRenderer from "./LinkRenderer";
import { setupZoomHandler } from "./ZoomHandler";
import { setupKeyPressHandler } from "./KeyPressHandler";
import { setupNodeDragHandler } from "./NodeDragHandler";

interface CanvasSVGProps {
    agents: AgentNode[];
    setAgents: React.Dispatch<React.SetStateAction<AgentNode[]>>;
    links: { source: string; target: string }[];
    setLinks: React.Dispatch<React.SetStateAction<{ source: string; target: string }[]>>;
    selectedNode: string | null;
    setSelectedNode: React.Dispatch<React.SetStateAction<string | null>>;
    selectedLinkRef: React.MutableRefObject<{ source: string; target: string } | null>;
}

const CanvasSVG: React.FC<CanvasSVGProps> = ({
    agents,
    setAgents,
    links,
    setLinks,
    selectedNode,
    setSelectedNode,
    selectedLinkRef
}) => {
    const ref = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!ref.current) return;

        const svg = d3.select(ref.current);
        svg.selectAll("*").remove();
        const g = svg.append<SVGGElement>("g");

        setupZoomHandler(svg, g);

        LinkRenderer(g, links, agents, setLinks, selectedLinkRef);

        setupKeyPressHandler(agents, setAgents, links, setLinks, selectedNode, selectedLinkRef, setSelectedNode, ref);
        setupNodeDragHandler(g, agents, links);
        NodeRenderer(g, agents, links, setLinks, selectedNode, setSelectedNode);

        svg.on("click", (event) => {
            const target = event.target as HTMLElement;
            if (!target.closest(".node")) {   // If double clicked on empty canvas
                setSelectedNode(null);
            }
        });

    }, [agents, links, selectedNode]);

    return <svg ref={ref} style={{ flexGrow: 1 }} />;
};

export default CanvasSVG;
