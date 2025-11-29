# OrKa Visual Architecture Guide

> **Last Updated:** 29 November 2025  
> **Status:** 🆕 New in v0.9.6  
> **Related:** [Architecture](architecture.md) | [Components](COMPONENTS.md) | [index](index.md)

This guide provides comprehensive visual design specifications for OrKa's architecture components. Use this as a reference for creating diagrams, presentations, and visual documentation.

---

## 🎨 Design Principles

### Visual Language
- **Flat Design:** Modern, clean aesthetic without 3D effects or shadows
- **Consistent Iconography:** All icons follow the same visual weight and style
- **Color Coding:** Semantic colors that convey component types
- **Clear Hierarchy:** Visual distinction between components, nodes, and tools

### Technical Specifications
- **Icon Size:** 64x64px minimum for scalability
- **Line Weight:** 1.5-2px for outlines, 3px for emphasis
- **Corner Radius:** 6-8px for consistency
- **Spacing:** 24px minimum between components, 48px between major sections

---

## 🎨 Color Palette

### Primary Colors
| Component Type | Color | Hex Code | Usage |
|----------------|-------|----------|-------|
| **Orchestrator** | Primary Blue | `#2563EB` | Main orchestration engine |
| **ExecutionEngine** | Dark Blue | `#1E40AF` | Execution control layer |
| **Memory System** | Teal | `#06B6D4` | Memory/storage components |
| **LLM Agents** | Orange | `#F59E0B` | AI/LLM processing |
| **Nodes** | Purple | `#8B5CF6` | Control flow nodes |
| **Tools** | Green | `#10B981` | External integrations |
| **Data Flow** | Gray | `#6B7280` | Data connections |

### Status Colors
| Status | Color | Hex Code |
|--------|-------|----------|
| Active/Running | Green | `#22C55E` |
| Pending | Yellow | `#FACC15` |
| Error | Red | `#EF4444` |
| Complete | Blue | `#3B82F6` |

---

## 🧱 Component Specifications

### 1. Orchestrator
**Icon:** Circular hub with radiating connections  
**Color:** Primary Blue (#2563EB)  
**Shape:** Circle, 64x64px minimum  
**Details:**
- Central circle represents the orchestrator core
- 6-8 connection points radiating outward
- Optional gear icon overlay to indicate orchestration
- Label: "Orchestrator" below icon

**MiroAI Prompt:**
```
Create a flat design icon for an AI orchestrator: circular hub in primary blue (#2563EB) 
with 6-8 clean radiating connection lines. Modern, minimal style with 8px rounded corners. 
Include subtle gear overlay. 64x64px base size.
```

### 2. ExecutionEngine
**Icon:** Layered engine with gears  
**Color:** Dark Blue (#1E40AF)  
**Shape:** Rounded rectangle, 80x64px  
**Details:**
- Three visible layers: top, middle, bottom
- Gear mechanisms visible between layers
- Flow indicators (arrows) showing execution direction
- Label: "ExecutionEngine"

**MiroAI Prompt:**
```
Flat design execution engine icon: 3 horizontal layers in dark blue (#1E40AF) with 
visible gear mechanisms. Show execution flow with subtle arrows. Rounded rectangle 
80x64px, 6px corners, 2px stroke weight.
```

### 3. Memory System (Redis/RAG)
**Icon:** Database cylinder with brain overlay  
**Color:** Teal (#06B6D4)  
**Shape:** Cylinder, 56x64px  
**Details:**
- Classic database cylinder shape
- Brain icon or network pattern overlay
- Vector arrows indicating semantic search capability
- Label: "Memory System (Redis)"

**MiroAI Prompt:**
```
Design a memory system icon: teal (#06B6D4) database cylinder with subtle brain/network 
overlay. Add small vector search arrows. Flat design, 56x64px, clean minimal style 
with 6px rounded edges.
```

### 4. GraphScout Agent
**Icon:** Compass/pathfinder with graph nodes  
**Color:** Orange (#F59E0B)  
**Shape:** Octagon, 64x64px  
**Details:**
- Compass rose in center
- Graph nodes connected around perimeter
- Discovery rays emanating from center
- Label: "GraphScout"

**MiroAI Prompt:**
```
Create GraphScout pathfinding icon: orange (#F59E0B) octagonal compass with graph 
nodes around perimeter. Central compass needle, discovery rays emanating. Flat modern 
style, 64x64px, 8px rounded corners.
```

### 5. PathExecutor Node
**Icon:** Sequential steps with execution pointer  
**Color:** Purple (#8B5CF6)  
**Shape:** Horizontal capsule, 96x48px  
**Details:**
- 3-4 connected step indicators
- Execution pointer showing current step
- Flow arrows between steps
- Label: "PathExecutor"

**MiroAI Prompt:**
```
PathExecutor node icon: purple (#8B5CF6) horizontal capsule showing 4 connected steps 
with execution pointer. Clean flow arrows, modern flat design. 96x48px capsule shape, 
24px rounded ends.
```

### 6. DecisionEngine
**Icon:** Diamond decision gate with logic symbols  
**Color:** Orange (#F59E0B)  
**Shape:** Diamond, 64x64px  
**Details:**
- Classic flowchart diamond shape
- Logic symbols (?, if/then) inside
- Multiple exit paths indicated
- Label: "DecisionEngine"

**MiroAI Prompt:**
```
DecisionEngine icon: orange (#F59E0B) diamond shape with logic symbols inside. 
Show 2-3 exit paths with arrows. Flat design style, 64x64px diamond, 2px stroke, 
minimal and clean.
```

### 7. PathScorer
**Icon:** Gauge/meter with score indicators  
**Color:** Green (#10B981)  
**Shape:** Semi-circle gauge, 72x48px  
**Details:**
- Semi-circular gauge display
- Score indicators (0-100 scale visible)
- Pointer showing current score
- Label: "PathScorer"

**MiroAI Prompt:**
```
PathScorer gauge icon: green (#10B981) semi-circular meter with score scale 0-100. 
Pointer needle showing score. Modern flat dashboard style, 72x48px, clean minimalist 
design with clear scale markers.
```

### 8. LocalLLM Agent
**Icon:** Chip/processor with AI brain  
**Color:** Orange (#F59E0B)  
**Shape:** Square chip, 64x64px  
**Details:**
- Microchip outline with pins
- AI/neural network pattern inside
- "Local" badge or indicator
- Label: "LocalLLM"

**MiroAI Prompt:**
```
LocalLLM agent icon: orange (#F59E0B) microchip square with visible pins and neural 
network pattern inside. Add small "LOCAL" badge. Flat tech style, 64x64px, 8px rounded 
corners, 2px stroke weight.
```

### 9. OpenAI Agent
**Icon:** Cloud with GPT indicator  
**Color:** Light Orange (#FCD34D)  
**Shape:** Cloud, 80x56px  
**Details:**
- Stylized cloud shape
- "GPT" or OpenAI logo inside
- Connection lines showing API access
- Label: "OpenAI"

**MiroAI Prompt:**
```
OpenAI cloud agent icon: light orange (#FCD34D) stylized cloud with "GPT" text inside. 
Show API connection lines. Modern flat cloud design, 80x56px, smooth curves, 
professional SaaS aesthetic.
```

### 10. Memory Agent (Read/Write)
**Icon:** Document with bidirectional arrows  
**Color:** Teal (#06B6D4)  
**Shape:** Document rectangle, 56x72px  
**Details:**
- Document/page shape
- Bidirectional arrows (read ↓, write ↑)
- Memory layer connection lines
- Label: "Memory Agent"

**MiroAI Prompt:**
```
Memory Agent icon: teal (#06B6D4) document shape with bidirectional arrows showing 
read/write operations. Clean flat design, 56x72px, 6px rounded corners, clear arrow 
indicators for data flow.
```

### 11. Search Agent (DuckDuckGo)
**Icon:** Magnifying glass with web globe  
**Color:** Green (#10B981)  
**Shape:** Circle with handle, 64x64px  
**Details:**
- Classic magnifying glass outline
- Web/globe pattern visible through lens
- Search rays emanating
- Label: "Search"

**MiroAI Prompt:**
```
Search agent icon: green (#10B981) magnifying glass over web globe. Show search rays 
emanating from lens. Flat design, 64x64px total with handle, clean lines, modern 
minimal style.
```

### 12. Router Node
**Icon:** Traffic junction with multiple paths  
**Color:** Purple (#8B5CF6)  
**Shape:** Hexagon, 64x64px  
**Details:**
- Hexagon with routing arrows
- 3+ exit paths clearly visible
- Decision point indicator in center
- Label: "Router"

**MiroAI Prompt:**
```
Router node icon: purple (#8B5CF6) hexagon with routing arrows showing 3-4 exit paths. 
Central decision point indicator. Flat traffic junction style, 64x64px, 8px rounded 
corners, clear directional arrows.
```

### 13. Fork Node
**Icon:** Single path splitting into multiple  
**Color:** Purple (#8B5CF6)  
**Shape:** Y-junction, 72x64px  
**Details:**
- Single input arrow
- Splits into 2-3 parallel output arrows
- Fork point clearly indicated
- Label: "Fork"

**MiroAI Prompt:**
```
Fork node icon: purple (#8B5CF6) Y-junction showing single input splitting into 3 
parallel paths. Clear fork point marker. Flat design, 72x64px, smooth curves, 
2px stroke weight, clean parallel lines.
```

### 14. Join Node
**Icon:** Multiple paths merging into single  
**Color:** Purple (#8B5CF6)  
**Shape:** Inverted Y, 72x64px  
**Details:**
- 2-3 parallel input arrows
- Merge into single output arrow
- Join point clearly indicated
- Label: "Join"

**MiroAI Prompt:**
```
Join node icon: purple (#8B5CF6) inverted Y showing 3 parallel paths merging into 
single output. Clear merge point marker. Flat design, 72x64px, smooth convergence, 
symmetric parallel lines.
```

### 15. Loop Node
**Icon:** Circular arrow with iteration counter  
**Color:** Purple (#8B5CF6)  
**Shape:** Circle with arrow, 64x64px  
**Details:**
- Circular/spiral arrow indicating loop
- Iteration counter (e.g., "×N")
- Entry and exit points marked
- Label: "Loop"

**MiroAI Prompt:**
```
Loop node icon: purple (#8B5CF6) circular arrow with iteration counter "×N". Show clear 
entry/exit points. Flat design, 64x64px circle, smooth curved arrow, modern minimal 
counter display.
```

### 16. Binary Agent
**Icon:** 0/1 decision split  
**Color:** Orange (#F59E0B)  
**Shape:** Circle split vertically, 64x64px  
**Details:**
- Circle divided into two halves
- "0" on left, "1" on right (or ✗/✓)
- Decision line clearly visible
- Label: "Binary"

**MiroAI Prompt:**
```
Binary classification agent icon: orange (#F59E0B) circle split vertically with "0" 
and "1" (or ✗ and ✓). Clean division line. Flat design, 64x64px, bold typography, 
clear binary distinction.
```

### 17. Classification Agent
**Icon:** Multiple category buckets  
**Color:** Orange (#F59E0B)  
**Shape:** Row of containers, 96x64px  
**Details:**
- 3-4 category containers/buckets
- Labels (A, B, C, D) visible
- Distribution arrows pointing to buckets
- Label: "Classification"

**MiroAI Prompt:**
```
Classification agent icon: orange (#F59E0B) row of 4 labeled category buckets (A,B,C,D) 
with distribution arrows. Flat design, 96x64px total, clean bucket shapes with 
6px rounded corners, clear labels.
```

### 18. Validation Agent
**Icon:** Checkmark with validation shield  
**Color:** Green (#10B981)  
**Shape:** Shield, 56x64px  
**Details:**
- Shield outline
- Large checkmark inside
- Validation indicators (✓ or rules icon)
- Label: "Validation"

**MiroAI Prompt:**
```
Validation agent icon: green (#10B981) shield with large checkmark inside. Add subtle 
rule/compliance indicators. Flat design, 56x64px shield shape, 8px rounded corners, 
professional security aesthetic.
```

### 19. Failover Agent
**Icon:** Backup path with fallback arrow  
**Color:** Yellow (#FACC15)  
**Shape:** Path with backup route, 96x56px  
**Details:**
- Primary path shown
- Backup/fallback path below
- Switch indicator at failure point
- Label: "Failover"

**MiroAI Prompt:**
```
Failover agent icon: yellow (#FACC15) showing primary path with backup fallback route. 
Clear switch indicator at failure point. Flat design, 96x56px, dashed backup line, 
modern reliability diagram style.
```

### 20. Graph Introspector
**Icon:** Magnifying glass over graph structure  
**Color:** Teal (#06B6D4)  
**Shape:** Combined, 80x64px  
**Details:**
- Graph network structure visible
- Magnifying glass overlay
- Analysis rays or scan lines
- Label: "Introspector"

**MiroAI Prompt:**
```
Graph Introspector icon: teal (#06B6D4) network graph under magnifying glass with 
analysis scan lines. Show graph nodes being examined. Flat design, 80x64px, clean 
network pattern, analytical style.
```

### 21. Smart Path Evaluator
**Icon:** Brain with path scoring bars  
**Color:** Orange (#F59E0B)  
**Shape:** Brain outline, 64x64px  
**Details:**
- Brain/intelligence icon outline
- Bar chart or score indicators visible
- Path evaluation lines
- Label: "PathEvaluator"

**MiroAI Prompt:**
```
Smart Path Evaluator icon: orange (#F59E0B) brain outline with bar chart score 
indicators inside. Show path evaluation lines. Flat design, 64x64px, clean neural 
aesthetic, modern AI intelligence style.
```

---

## 🔗 Connection Styles

### Data Flow Connections
- **Style:** Solid lines, 2px weight
- **Color:** Gray (#6B7280)
- **Arrow Style:** Simple triangular heads
- **Label Position:** Above line, centered

### Control Flow Connections
- **Style:** Dashed lines, 2px weight
- **Color:** Purple (#A78BFA)
- **Arrow Style:** Double-lined heads
- **Label Position:** Below line, centered

### Error/Fallback Connections
- **Style:** Dotted lines, 2px weight
- **Color:** Red (#F87171)
- **Arrow Style:** Hollow heads
- **Label Position:** Inline with line

---

## 📐 Diagram Layout Patterns

### 1. Sequential Flow Diagram
```
[Orchestrator] → [Agent 1] → [Agent 2] → [Agent 3] → [Output]
```
- Horizontal left-to-right layout
- Equal spacing (48px) between components
- Data flow arrows connecting each step

### 2. Fork-Join Pattern
```
                    → [Agent A] →
[Input] → [Fork] ↗  → [Agent B] → [Join] → [Output]
                    → [Agent C] →
```
- Fork node splits flow vertically
- Parallel branches with equal spacing
- Join node merges back to single flow

### 3. Router Decision Pattern
```
                → [Path A] → [Agent A]
[Input] → [Router] → [Path B] → [Agent B]
                → [Path C] → [Agent C]
```
- Diamond/hexagon router node
- Multiple decision paths
- Conditional labels on each path

### 4. Loop Iteration Pattern
```
[Input] → [Loop Start] → [Agent] → [Condition] ↺
              ↓                           ↓
          [Continue]                  [Exit] → [Output]
```
- Loop node shows iteration
- Feedback arrow to loop start
- Exit condition clearly marked

---

## 🎬 Animation Specifications

### Execution Flow Animation
- **Duration:** 0.3-0.5 seconds per transition
- **Easing:** Ease-in-out cubic
- **Highlight:** Component glows when active (add 4px glow in primary color)
- **Data Flow:** Animated dots traveling along connection lines

### State Transitions
| From State | To State | Animation |
|------------|----------|-----------|
| Idle | Running | Fade in + pulse (1 cycle) |
| Running | Complete | Glow → fade to completion color |
| Running | Error | Shake + fade to error color |
| Any | Pending | Subtle pulse loop (2s cycle) |

---

## 📦 Deliverables for Designers

### File Formats
1. **SVG:** Scalable vector format (primary)
2. **PNG:** High-res (2x, 3x) for presentations
3. **Figma/Sketch:** Source files with components library

### Component Library Structure
```
OrKa_Visual_Components/
├── Icons/
│   ├── Orchestrator.svg
│   ├── ExecutionEngine.svg
│   ├── Memory/
│   │   ├── MemorySystem.svg
│   │   ├── MemoryAgent.svg
│   ├── Agents/
│   │   ├── LocalLLM.svg
│   │   ├── OpenAI.svg
│   │   ├── Binary.svg
│   │   ├── Classification.svg
│   ├── Nodes/
│   │   ├── Router.svg
│   │   ├── Fork.svg
│   │   ├── Join.svg
│   │   ├── Loop.svg
│   └── Tools/
│       ├── Search.svg
│       ├── Validation.svg
├── Diagrams/
│   ├── ComponentArchitecture.svg
│   ├── ExecutionFlow.svg
│   ├── ControlFlow.svg
│   ├── DataFlow.svg
│   ├── MemorySystem.svg
│   └── GraphScout.svg
└── Templates/
    ├── BlankWorkflow.fig
    ├── PresentationSlide.pptx
    └── README.md
```

---

## 🖼️ Complete Diagram Templates

### MiroAI Prompt 1: Component Architecture Diagram
```
Create a comprehensive OrKa architecture diagram showing:
- Orchestrator (blue #2563EB circle) at center
- ExecutionEngine (dark blue #1E40AF) layer below
- Memory System (teal #06B6D4) on left
- Agents cluster (orange #F59E0B) on right
- Nodes (purple #8B5CF6) at bottom
- Clear labeled connections between all components
Use flat design, 1920x1080px canvas, clean minimal style
```

### MiroAI Prompt 2: Execution Flow Diagram
```
Design an execution flow timeline showing:
- Sequential stages from left to right
- Input → GraphScout → PathExecutor → Agents → Join → Output
- Each component with proper colors and icons
- Flow arrows with execution state indicators (active/complete)
- Timeline markers showing execution progress
Horizontal layout, 1600x400px, flat design
```

### MiroAI Prompt 3: Control Flow Patterns
```
Create a grid showing 4 control flow patterns:
1. Sequential (top-left)
2. Fork-Join parallel (top-right)
3. Router conditional (bottom-left)
4. Loop iteration (bottom-right)
Each in its own 700x700px section with labels and color-coded components
Clean educational diagram style, flat design
```

### MiroAI Prompt 4: Data Flow Diagram
```
Design a data flow diagram showing:
- Input data sources (left) with document icons
- Memory system (center top) with teal database
- Agent processing (center) with orange AI icons
- Output destinations (right) with result icons
- Bidirectional data flow arrows with labels
Use flat design, 1400x900px, emphasize data paths with animated dashed lines
```

### MiroAI Prompt 5: Memory System Deep Dive
```
Create detailed memory system diagram showing:
- Redis backend (teal cylinder) at bottom
- RAG vector search layer (teal network) in middle
- Memory agents (teal documents) at top
- Read/write operations with arrows
- Memory presets (sensory/working/episodic/semantic) as categories
Vertical layered architecture, 800x1200px, flat technical style
```

### MiroAI Prompt 6: GraphScout Decision Flow
```
Design GraphScout intelligent routing diagram showing:
- Input question (left)
- GraphScout (orange compass) analyzing paths
- 3 potential agent paths shown as branches
- PathScorer evaluating each (green gauges showing scores)
- DecisionEngine selecting best path (orange diamond with ✓)
- Chosen path highlighted in green, others grayed out
Horizontal decision tree, 1600x800px, flat modern style
```

---

## ✅ Design Checklist

Before finalizing any OrKa visual:
- [ ] All icons use specified color palette
- [ ] Line weights are consistent (1.5-2px standard, 3px emphasis)
- [ ] Corner radius is 6-8px where applicable
- [ ] Spacing between components is 24px minimum
- [ ] Labels are clear and use consistent typography
- [ ] Connection arrows have proper style (solid/dashed/dotted)
- [ ] File formats include SVG (primary) and PNG (2x, 3x)
- [ ] Component follows flat design principles (no shadows/gradients)
- [ ] Colors have sufficient contrast (WCAG AA minimum)
- [ ] Icons scale well from 32px to 256px

---

## 📞 Questions or Feedback?

For questions about visual specifications or to contribute custom components:
- Open an issue: [GitHub Issues](https://github.com/marcosomma/orka-core/issues)
- Tag with `documentation` and `visual-design`

---

**Guide Version:** 1.0.0  
**Last Updated:** 16 November 2025  
**Maintained By:** OrKa Documentation Team
---
← [Components](COMPONENTS.md) | [📚 INDEX](index.md) | [YAML Configuration](YAML_CONFIGURATION.md) →
