import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Network,
  Activity,
  Database,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  X,
  Layers,
  Sparkles,
  ExternalLink,
  Info,
} from "lucide-react";
import Topbar from "../components/layout/Topbar";
import { api } from "../services/api";

const TYPE_COLORS = {
  Technology: { bg: "#0284c7", border: "#38bdf8", glow: "rgba(56,189,248,0.4)" },
  Person: { bg: "#7c3aed", border: "#a78bfa", glow: "rgba(167,139,250,0.4)" },
  Organization: { bg: "#d97706", border: "#fbbf24", glow: "rgba(251,191,36,0.4)" },
  Skill: { bg: "#059669", border: "#34d399", glow: "rgba(52,211,153,0.4)" },
  Concept: { bg: "#e11d48", border: "#fb7185", glow: "rgba(251,113,133,0.4)" },
  Location: { bg: "#4f46e5", border: "#818cf8", glow: "rgba(129,140,248,0.4)" },
  Entity: { bg: "#2563eb", border: "#60a5fa", glow: "rgba(96,165,250,0.4)" },
};

function getNodeColor(type) {
  return TYPE_COLORS[type] || TYPE_COLORS.Entity;
}

export default function GraphExplorer() {
  const [search, setSearch] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [selected, setSelected] = useState(null);
  const [activeType, setActiveType] = useState("ALL");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [draggedNode, setDraggedNode] = useState(null);

  const containerRef = useRef(null);
  const animRef = useRef(null);
  const [nodePositions, setNodePositions] = useState({});

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["graph-explore", submitted],
    queryFn: async () =>
      (await api.post("/api/graph/explore", { query: submitted || null, limit: 150 })).data,
    refetchOnWindowFocus: false,
  });

  const graph = useMemo(
    () => data || { entities: [], relationships: [] },
    [data]
  );

  // Collect distinct entity types
  const entityTypes = useMemo(() => {
    const types = new Set(graph.entities.map((e) => e.type || "Entity"));
    return ["ALL", ...Array.from(types)];
  }, [graph.entities]);

  // Initialize node layout with force physics simulation
  useEffect(() => {
    if (!graph.entities.length) {
      setNodePositions({});
      return;
    }

    const width = 900;
    const height = 650;
    const initial = {};

    graph.entities.forEach((node, i) => {
      const angle = (i / Math.max(graph.entities.length, 1)) * Math.PI * 2;
      const radius = Math.min(260, 110 + graph.entities.length * 3.5);
      initial[node.id] = {
        x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
        y: height / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
      };
    });

    setNodePositions(initial);

    // Run simple force relaxation for 60 iterations
    let positions = { ...initial };
    let iterations = 0;

    const simulate = () => {
      if (iterations > 75) return;
      iterations++;

      const updated = { ...positions };
      const entityIds = Object.keys(updated);

      // Repulsion between all nodes
      for (let i = 0; i < entityIds.length; i++) {
        const id1 = entityIds[i];
        for (let j = i + 1; j < entityIds.length; j++) {
          const id2 = entityIds[j];
          const n1 = updated[id1];
          const n2 = updated[id2];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const distSq = dx * dx + dy * dy || 1;
          const dist = Math.sqrt(distSq);
          if (dist < 180) {
            const force = (180 - dist) / 180 * 2.2;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            n1.vx -= fx;
            n1.vy -= fy;
            n2.vx += fx;
            n2.vy += fy;
          }
        }
      }

      // Spring attraction between connected relationships
      graph.relationships.forEach((rel) => {
        const s = updated[rel.source_id];
        const t = updated[rel.target_id];
        if (!s || !t) return;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const targetDist = 120;
        const force = (dist - targetDist) * 0.04;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        s.vx += fx;
        s.vy += fy;
        t.vx -= fx;
        t.vy -= fy;
      });

      // Damping and center gravity
      entityIds.forEach((id) => {
        const n = updated[id];
        // Center gravity
        n.vx += (width / 2 - n.x) * 0.005;
        n.vy += (height / 2 - n.y) * 0.005;
        // Damping
        n.vx *= 0.82;
        n.vy *= 0.82;
        n.x += n.vx;
        n.y += n.vy;
        // Boundary containment
        n.x = Math.max(60, Math.min(width - 60, n.x));
        n.y = Math.max(60, Math.min(height - 60, n.y));
      });

      positions = updated;
      setNodePositions({ ...positions });
      animRef.current = requestAnimationFrame(simulate);
    };

    animRef.current = requestAnimationFrame(simulate);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [graph]);

  // Connected relationships for selected entity
  const connectedRels = useMemo(() => {
    if (!selected) return [];
    return graph.relationships.filter(
      (r) => r.source_id === selected.id || r.target_id === selected.id
    );
  }, [selected, graph.relationships]);

  // Connected node IDs
  const connectedNodeIds = useMemo(() => {
    if (!selected) return new Set();
    const set = new Set([selected.id]);
    connectedRels.forEach((r) => {
      set.add(r.source_id);
      set.add(r.target_id);
    });
    return set;
  }, [selected, connectedRels]);

  // Handle Dragging
  const handleNodeMouseDown = (e, node) => {
    e.stopPropagation();
    setDraggedNode(node.id);
  };

  const handleMouseMove = useCallback(
    (e) => {
      if (draggedNode && nodePositions[draggedNode]) {
        const rect = containerRef.current.getBoundingClientRect();
        const clientX = (e.clientX - rect.left - pan.x) / zoom;
        const clientY = (e.clientY - rect.top - pan.y) / zoom;
        setNodePositions((prev) => ({
          ...prev,
          [draggedNode]: {
            ...prev[draggedNode],
            x: clientX,
            y: clientY,
            vx: 0,
            vy: 0,
          },
        }));
      } else if (isPanning) {
        setPan({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        });
      }
    },
    [draggedNode, isPanning, dragStart, pan, zoom, nodePositions]
  );

  const handleMouseUp = () => {
    setDraggedNode(null);
    setIsPanning(false);
  };

  const handleCanvasMouseDown = (e) => {
    if (e.target.tagName === "svg" || e.target.id === "graph-canvas") {
      setIsPanning(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((z) => Math.min(2.5, Math.max(0.4, z * factor)));
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelected(null);
  };

  return (
    <>
      <Topbar
        title="Knowledge Graph Explorer"
        subtitle="Visual, interactive multi-hop knowledge graph with live Neo4j entity reasoning"
      />
      <div className="space-y-6 p-8">
        {/* Header toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <Metric icon={Network} label="Entities" value={graph.entities.length} />
            <Metric icon={Activity} label="Relationships" value={graph.relationships.length} />
            <Metric icon={Database} label="Knowledge Store" value="Neo4j Aura / Local" />
          </div>

          <form
            className="flex w-full max-w-md items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setSubmitted(search.trim());
              setSelected(null);
            }}
          >
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
              <input
                className="input-dark pl-9 pr-3 text-xs"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Find entities or relationships..."
              />
            </div>
            <button type="submit" className="btn-primary text-xs flex items-center gap-1.5">
              <Sparkles size={13} />
              Explore
            </button>
          </form>
        </div>

        {/* Entity type filter bar */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500 mr-1">
            <Layers size={13} /> Types:
          </span>
          {entityTypes.map((type) => {
            const count =
              type === "ALL"
                ? graph.entities.length
                : graph.entities.filter((e) => (e.type || "Entity") === type).length;
            const active = activeType === type;
            const color = TYPE_COLORS[type] || TYPE_COLORS.Entity;
            return (
              <button
                key={type}
                onClick={() => setActiveType(type)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs transition ${
                  active
                    ? "bg-white/10 font-medium text-white shadow-sm ring-1 ring-white/20"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor: type === "ALL" ? "#38bdf8" : color.border,
                  }}
                />
                {type}
                <span className="text-[10px] text-slate-500">({count})</span>
              </button>
            );
          })}
        </div>

        {/* Interactive Graph Canvas */}
        <div
          ref={containerRef}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseDown={handleCanvasMouseDown}
          onWheel={handleWheel}
          className="glass-card relative h-[650px] w-full overflow-hidden select-none cursor-grab active:cursor-grabbing border border-white/10"
        >
          {/* Animated Background Mesh */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.12),transparent_70%)] pointer-events-none" />
          <div
            className="absolute inset-0 opacity-[0.03] pointer-events-none"
            style={{
              backgroundImage:
                "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
              backgroundSize: "32px 32px",
            }}
          />

          {/* Viewport Floating Controls */}
          <div className="absolute left-4 top-4 z-10 flex flex-col gap-1.5 rounded-xl border border-white/10 bg-navy-900/80 p-1.5 backdrop-blur shadow-xl">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
              className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
              title="Zoom In"
            >
              <ZoomIn size={16} />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
              className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
              title="Zoom Out"
            >
              <ZoomOut size={16} />
            </button>
            <button
              onClick={resetView}
              className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
              title="Reset View"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          {/* Legend */}
          <div className="absolute left-4 bottom-4 z-10 hidden sm:flex items-center gap-3 rounded-xl border border-white/10 bg-navy-900/80 px-3 py-2 text-[11px] text-slate-400 backdrop-blur">
            <span className="font-medium text-slate-300">Drag to move nodes</span>
            <span>•</span>
            <span>Scroll to zoom</span>
            <span>•</span>
            <span>Click node for details</span>
          </div>

          {/* Loading / Error / Empty States */}
          {isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-400">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-electric-400 border-t-transparent mr-2" />
              Loading Neo4j knowledge graph topology...
            </div>
          ) : error ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <div className="text-sm text-rose-400">Failed to connect to Neo4j graph</div>
              <p className="max-w-md text-xs text-slate-500">{error.message}</p>
              <button className="btn-ghost text-xs" onClick={() => refetch()}>
                Retry connection
              </button>
            </div>
          ) : graph.entities.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <Network size={36} className="text-slate-600" />
              <p className="text-base font-semibold text-slate-300">Knowledge graph is empty</p>
              <p className="max-w-md text-xs text-slate-500">
                Upload a document on the Documents page and click "Graph Index" to extract entities
                and build relations.
              </p>
            </div>
          ) : (
            <svg
              id="graph-canvas"
              viewBox="0 0 900 650"
              className="h-full w-full"
            >
              <defs>
                {/* Glow Filter */}
                <filter id="neon-glow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <filter id="active-pulse" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur stdDeviation="8" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                {/* Relationship Direction Arrow */}
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="22"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
                </marker>
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="25"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
                </marker>
              </defs>

              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* RELATIONSHIP EDGES */}
                {graph.relationships.map((rel, idx) => {
                  const s = nodePositions[rel.source_id];
                  const t = nodePositions[rel.target_id];
                  if (!s || !t) return null;

                  const isSourceMatch = activeType === "ALL" || (rel.source_type || "Entity") === activeType;
                  const isTargetMatch = activeType === "ALL" || (rel.target_type || "Entity") === activeType;
                  if (!isSourceMatch && !isTargetMatch) return null;

                  const isConnected =
                    !selected ||
                    rel.source_id === selected.id ||
                    rel.target_id === selected.id;

                  const midX = (s.x + t.x) / 2;
                  const midY = (s.y + t.y) / 2;

                  return (
                    <g
                      key={`rel-${rel.source_id}-${rel.target_id}-${idx}`}
                      opacity={isConnected ? 1 : 0.12}
                      className="transition-opacity duration-300"
                    >
                      {/* Edge Line with flowing energy animation */}
                      <line
                        x1={s.x}
                        y1={s.y}
                        x2={t.x}
                        y2={t.y}
                        stroke={isConnected && selected ? "#38bdf8" : "#334155"}
                        strokeWidth={isConnected && selected ? 2.5 : 1.2}
                        strokeDasharray={isConnected && selected ? "6 4" : "none"}
                        markerEnd={isConnected && selected ? "url(#arrow-active)" : "url(#arrow)"}
                        className={isConnected && selected ? "animate-pulse" : ""}
                      />
                      {/* Relationship Label Badge */}
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect
                          x="-35"
                          y="-9"
                          width="70"
                          height="18"
                          rx="9"
                          fill="#0b1020"
                          stroke={isConnected && selected ? "#38bdf8" : "#1e293b"}
                          strokeWidth="1"
                        />
                        <text
                          x="0"
                          y="3"
                          textAnchor="middle"
                          fill={isConnected && selected ? "#7dd3fc" : "#94a3b8"}
                          fontSize="8.5"
                          fontWeight="600"
                          className="pointer-events-none select-none"
                        >
                          {(rel.relation_type || "RELATES").slice(0, 11)}
                        </text>
                      </g>
                    </g>
                  );
                })}

                {/* ENTITY NODES */}
                {graph.entities.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;

                  const isTypeMatch = activeType === "ALL" || (node.type || "Entity") === activeType;
                  const isSelected = selected?.id === node.id;
                  const isConnected = connectedNodeIds.has(node.id);
                  const isSearchMatch =
                    submitted &&
                    node.name.toLowerCase().includes(submitted.toLowerCase());

                  const opacity =
                    !isTypeMatch
                      ? 0.15
                      : selected
                      ? isConnected
                        ? 1
                        : 0.22
                      : 1;

                  const color = getNodeColor(node.type);

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      opacity={opacity}
                      onMouseDown={(e) => handleNodeMouseDown(e, node)}
                      onClick={() => setSelected(node)}
                      className="cursor-pointer transition-opacity duration-200"
                    >
                      {/* Pulse ring for selected or search matching node */}
                      {(isSelected || isSearchMatch) && (
                        <circle
                          r="28"
                          fill="none"
                          stroke={color.border}
                          strokeWidth="2"
                          strokeDasharray="4 4"
                          className="animate-spin"
                          style={{ animationDuration: "8s" }}
                        />
                      )}

                      {/* Main Node Circle */}
                      <circle
                        r={isSelected ? 22 : 17}
                        fill={color.bg}
                        stroke={color.border}
                        strokeWidth={isSelected ? 3 : 2}
                        filter="url(#neon-glow)"
                      />

                      {/* Center Core */}
                      <circle r="4" fill="#ffffff" opacity="0.9" />

                      {/* Node Label Text */}
                      <text
                        y={isSelected ? 35 : 29}
                        textAnchor="middle"
                        fill="#f8fafc"
                        fontSize={isSelected ? "12" : "10.5"}
                        fontWeight={isSelected ? "700" : "500"}
                        className="pointer-events-none select-none drop-shadow"
                      >
                        {node.name.length > 20 ? `${node.name.slice(0, 19)}…` : node.name}
                      </text>

                      {/* Node Type Pill Below */}
                      <text
                        y={isSelected ? 47 : 39}
                        textAnchor="middle"
                        fill={color.border}
                        fontSize="8"
                        fontWeight="600"
                        className="pointer-events-none select-none uppercase tracking-wider"
                      >
                        {node.type || "Entity"}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}

          {/* Slide-out Node Inspector Panel */}
          {selected && (
            <aside className="absolute right-4 top-4 bottom-4 w-[340px] overflow-y-auto rounded-2xl border border-white/10 bg-navy-900/95 p-5 shadow-2xl backdrop-blur-md">
              <div className="flex items-start justify-between border-b border-white/10 pb-4">
                <div>
                  <span
                    className="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
                    style={{
                      backgroundColor: `${getNodeColor(selected.type).border}22`,
                      color: getNodeColor(selected.type).border,
                    }}
                  >
                    {selected.type || "Entity"}
                  </span>
                  <h3 className="mt-1.5 text-lg font-bold text-white leading-tight">
                    {selected.name}
                  </h3>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-white"
                >
                  <X size={18} />
                </button>
              </div>

              {selected.description && (
                <div className="mt-4 text-xs leading-relaxed text-slate-300 bg-white/[0.03] p-3 rounded-xl border border-white/5">
                  <div className="flex items-center gap-1.5 text-[10px] uppercase font-semibold text-slate-500 mb-1">
                    <Info size={12} /> Description
                  </div>
                  {selected.description}
                </div>
              )}

              {/* Connected Relationships */}
              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <span>Connected Relations</span>
                  <span className="badge border-white/10 bg-white/5 text-[10px]">
                    {connectedRels.length}
                  </span>
                </div>

                {connectedRels.length === 0 ? (
                  <div className="text-xs text-slate-500 italic">
                    No connected edges in this view.
                  </div>
                ) : (
                  <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
                    {connectedRels.map((rel, i) => {
                      const isOutgoing = rel.source_id === selected.id;
                      const partnerName = isOutgoing ? rel.target_name : rel.source_name;
                      const partnerType = isOutgoing ? rel.target_type : rel.source_type;

                      return (
                        <div
                          key={`detail-rel-${i}`}
                          className="rounded-xl border border-white/5 bg-white/[0.025] p-3 text-xs"
                        >
                          <div className="flex items-center justify-between gap-1 text-[11px]">
                            <span className="font-semibold text-electric-400">
                              {rel.relation_type || "RELATES_TO"}
                            </span>
                            <span className="text-[10px] text-slate-500">
                              {isOutgoing ? "outgoing →" : "← incoming"}
                            </span>
                          </div>

                          <div className="mt-1.5 font-medium text-slate-200">
                            {isOutgoing ? selected.name : partnerName}{" "}
                            <span className="text-slate-500">→</span>{" "}
                            {isOutgoing ? partnerName : selected.name}
                          </div>

                          {rel.evidence && (
                            <div className="mt-2 text-[11px] italic text-slate-400 border-l-2 border-white/10 pl-2">
                              "{rel.evidence}"
                            </div>
                          )}

                          {rel.document_id && (
                            <div className="mt-2 flex items-center gap-1 text-[10px] text-slate-500">
                              <ExternalLink size={10} />
                              Source: {rel.document_id}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </aside>
          )}
        </div>
      </div>
    </>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="glass-card flex items-center gap-3 px-4 py-3">
      <div className="rounded-xl bg-electric-500/10 p-2 text-electric-400">
        <Icon size={16} />
      </div>
      <div>
        <div className="text-[11px] text-slate-500">{label}</div>
        <div className="text-base font-bold text-white">{value}</div>
      </div>
    </div>
  );
}
