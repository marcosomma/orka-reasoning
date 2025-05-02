import * as d3 from "d3";
import { AgentNode } from "../../types";
import { colorsByType, descriptionsByType } from "./contants";
import { setupNodeDragHandler } from "./NodeDragHandler";
import { isDataCollectorType, isOpenAIType } from "../../utils/generic";

function createNodeShape(group: d3.Selection<SVGGElement, AgentNode, null, undefined>, d: AgentNode, selected: boolean) {
    const width = 100;
    const height = 50;
    const cornerRadius = 10;
    const strokeColor = selected ? "red" : "#fff";

    if (d.type === "router") {
        group.append("rect")
            .attr("x", -height / 3)
            .attr("y", -height / 3)
            .attr("width", height / 1.5)
            .attr("height", height / 1.5)
            .attr("transform", "rotate(45)")
            .style("cursor", "pointer")
            .attr("fill", colorsByType[d.type])
            .attr("stroke", strokeColor)
            .attr("stroke-width", 2);
    } else if (d.type === "failover") {
        group.append("circle")
            .attr("r", height / 2)
            .style("cursor", "pointer")
            .attr("fill", colorsByType[d.type])
            .attr("stroke", strokeColor)
            .attr("stroke-width", 2);
    } else if (d.type === "join" || d.type === "fork") {
        group.append("path")
            .attr("d", d3.symbol().type(d3.symbolTriangle).size(1200)())
            .style("cursor", "pointer")
            .attr("transform", d.type === "fork" ? "rotate(-90)" : "rotate(90)")
            .attr("fill", colorsByType[d.type])
            .attr("stroke", strokeColor)
            .attr("stroke-width", 2);
    } else {
        if (isOpenAIType(d.type)) {
            group.append("rect")
                .attr("x", -width / 2)
                .attr("y", -height / 4)
                .attr("width", width)
                .attr("height", height / 2)
                .attr("rx", cornerRadius)
                .attr("ry", cornerRadius)
                .style("cursor", "pointer")
                .attr("fill", colorsByType[d.type] || "#ccc")
                .attr("stroke", strokeColor)
                .attr("stroke-width", 2);
        } else if (isDataCollectorType(d.type)) {
            group.append("rect")
                .attr("x", -width / 3)
                .attr("y", -height / 4)
                .attr("width", width / 1.5)
                .attr("height", height / 2)
                .attr("rx", 0)
                .attr("ry", 0)
                .style("cursor", "pointer")
                .attr("fill", colorsByType[d.type] || "#ccc")
                .attr("stroke", strokeColor)
                .attr("stroke-width", 2);
        }
    }

    group.append("title")
        .text(descriptionsByType[d.type]);

}

function createNodeLabel(group: d3.Selection<SVGGElement, AgentNode, null, undefined>, d: AgentNode) {
    const nodeText = d.id.split("_")[0].replace(/-/g, " ");

    const textElement = group.append("text")
        .text(nodeText)
        .attr("text-anchor", "middle")
        .attr("dy", 5)
        .style("font-size", "10px")
        .style("cursor", "grabbing")
        .style("fill", "#000")
        .style("pointer-events", "none") // So clicking goes to the node not text
        .attr("text-overflow", "ellipsis")
        .attr("overflow", "hidden");

    // After rendering, measure width
    const widthLimit = 60; // You can tweak this depending on your node shape

    const bbox = (textElement.node() as SVGTextElement).getBBox();
    if (bbox.width > widthLimit) {
        let shortened = nodeText;
        while (shortened.length > 0 && (textElement.node() as SVGTextElement).getComputedTextLength() > widthLimit) {
            shortened = shortened.slice(0, -1);
            textElement.text(shortened + "...");
        }
    }
}

export default function NodeRenderer(
    g: d3.Selection<SVGGElement, unknown, null, undefined>,
    agents: AgentNode[],
    links: { source: string; target: string }[],
    setLinks: React.Dispatch<React.SetStateAction<{ source: string; target: string }[]>>,
    selectedNode: string | null,
    setSelectedNode: React.Dispatch<React.SetStateAction<string | null>>
) {
    const node = g.selectAll<SVGGElement, AgentNode>(".node")
        .data(agents)
        .enter()
        .append("g")
        .attr("class", "node")
        .attr("transform", (d) => `translate(${d.x}, ${d.y})`)
        .on("click", (event, d) => {
            event.stopPropagation();
            if (!selectedNode || selectedNode === d.id) return;

            const sourceNode = agents.find((a) => a.id === selectedNode);
            const targetNode = d;
            const outgoingFromSource = links.filter((link) => link.source === selectedNode);
            const incomingToTarget = links.filter((link) => link.target === d.id);

            // ENFORCE OUTGOING LIMIT ON SOURCE
            let maxOut = 1;
            if (sourceNode?.type === "router") maxOut = 2;
            else if (sourceNode?.type === "fork") maxOut = Infinity;
            if (outgoingFromSource.length >= maxOut && !outgoingFromSource.some(link => link.target === d.id)) {
                console.warn("Too many outgoing links from source:", sourceNode?.id);
                setSelectedNode(null);
                return;
            }
            // ENFORCE INCOMING LIMIT ON TARGET
            let maxIn = 1;
            if (targetNode.type === "join" || targetNode.type === "failover") maxIn = Infinity;
            else if (targetNode.type === "router") maxIn = 1;
            else if (targetNode.type === "fork") maxIn = 1;

            if (incomingToTarget.length >= maxIn && !incomingToTarget.some(link => link.source === selectedNode)) {
                console.warn("Too many incoming links to target:", targetNode.type, "ID:", targetNode.id);
                setSelectedNode(null);
                return;
            }
            // Prevent duplicate link
            const alreadyLinked = links.some((l) => l.source === selectedNode && l.target === d.id);
            if (alreadyLinked) {
                setSelectedNode(null);
                return;
            }
            // Remove oldest if needed
            const newLinks = [...links];
            if (outgoingFromSource.length >= maxOut) {
                const oldest = outgoingFromSource[0];
                const index = newLinks.findIndex((l) => l.source === selectedNode && l.target === oldest.target);
                if (index !== -1) newLinks.splice(index, 1);
            }

            // ✅ Add the new link with `depends_on` param if the link is within a forked path
            console.log("depends_on Checking if link is within forked path...");
            console.log("depends_on Agents:", agents);
            const isWithinForkBranch = agents.some(
                (agent, i) => {
                    console.log("depends_on Checking if link is within forked path...");
                    return agent.type === "fork" && agents.slice(i + 1).some(
                        (otherAgent) => otherAgent.type === "join"
                    );
                }
            );

            const newLink = {
                source: selectedNode,
                target: d.id,
                ...(isWithinForkBranch ? { depends_on: true } : {})
            };

            newLinks.push(newLink);
            setLinks(newLinks);
            setSelectedNode(null);
        })
        .on("dblclick", (event, d) => {
            event.stopPropagation();
            setSelectedNode(d.id);
        })
        .call(setupNodeDragHandler(g, agents, links));


    node.each(function (d) {
        const group = d3.select<SVGGElement, AgentNode>(this);

        createNodeShape(group, d, d.id === selectedNode);
        createNodeLabel(group, d);
    });
}
