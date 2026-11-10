import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, BrainCircuit, Route, Search, ShieldCheck } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Topbar from "../components/layout/Topbar";
import { api } from "../services/api";
import { getSummary } from "../services/monitoringService";

const COLORS = { vector: "#3b82f6", graph: "#8b5cf6", hybrid: "#10b981" };

export default function RoutingAnalytics() {
  const [query, setQuery] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { data } = useQuery({ queryKey: ["monitoring-summary"], queryFn: getSummary, refetchInterval: 10000 });
  const metrics = data?.summary?.queries || {};
  const chart = ["vector", "graph", "hybrid"].map((engine) => ({ name: engine, count: metrics.engine_usage?.[engine] || 0 }));

  async function inspect(event) {
    event.preventDefault();
    if (!query.trim() || busy) return;
    setBusy(true); setError(""); setAnalysis(null);
    try { const { data: result } = await api.post("/api/router/analyze", { query: query.trim() }); setAnalysis(result); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <><Topbar title="Routing Inspector" subtitle="Understand how query characteristics influence retrieval strategy"/><div className="space-y-6 p-8">
    <div className="grid gap-4 md:grid-cols-3"><Metric icon={Route} label="Routing decisions" value={metrics.total_queries || 0}/><Metric icon={ShieldCheck} label="Successful queries" value={metrics.successful_queries || 0}/><Metric icon={Activity} label="Fallbacks" value={metrics.fallback_count || 0}/></div>
    <div className="grid gap-6 xl:grid-cols-5">
      <section className="glass-card p-5 xl:col-span-3"><div className="mb-4 flex items-center gap-2"><BrainCircuit size={17} className="text-violet-300"/><h2 className="text-sm font-semibold text-white">Try the routing analyzer</h2></div><form className="flex gap-2" onSubmit={inspect}><input className="input-dark" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. Compare AWS and Azure services for data analytics"/><button className="btn-primary flex items-center gap-2" disabled={busy || !query.trim()}><Search size={15}/>{busy ? "Analyzing…" : "Analyze"}</button></form>
        {error && <p role="alert" className="mt-3 text-xs text-rose-300">{error}</p>}
        {analysis && <div className="mt-5 space-y-4 border-t border-white/5 pt-4"><div className="flex flex-wrap items-center gap-3"><span className="rounded-lg border border-white/10 px-3 py-2 text-sm font-semibold capitalize text-white">{analysis.decision?.selected_engine} RAG</span><span className="text-xs text-slate-400">Confidence {Math.round((analysis.decision?.confidence || 0) * 100)}%</span><span className="text-xs text-slate-500">Intent: {analysis.intent?.intent}</span></div><p className="text-sm leading-6 text-slate-300">{analysis.decision?.reason}</p><div className="grid gap-3 sm:grid-cols-2"><Detail label="Query complexity" value={analysis.complexity?.overall_complexity}/><Detail label="Entity density" value={analysis.complexity?.entity_density}/><Detail label="Estimated hops" value={analysis.complexity?.estimated_hops}/><Detail label="Entities found" value={analysis.features?.entity_count}/></div></div>}
        {!analysis && !error && <p className="mt-4 text-xs text-slate-500">Analyze is advisory; it does not execute retrieval or call an LLM.</p>}
      </section>
      <section className="glass-card p-5 xl:col-span-2"><h2 className="mb-2 text-sm font-semibold text-white">Engine distribution</h2>{chart.every((x) => !x.count) ? <div className="flex h-52 items-center justify-center text-xs text-slate-500">No routed queries recorded this session.</div> : <ResponsiveContainer width="100%" height={220}><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#1a2344"/><XAxis dataKey="name" stroke="#64748b" tick={{fontSize:11}}/><YAxis stroke="#64748b" allowDecimals={false} tick={{fontSize:11}}/><Tooltip contentStyle={{background:"#0b1020",border:"1px solid #233057",borderRadius:8}}/><Bar dataKey="count" radius={[6,6,0,0]}>{chart.map((x) => <Cell key={x.name} fill={COLORS[x.name]}/>)}</Bar></BarChart></ResponsiveContainer>}</section>
    </div>
  </div></>;
}

function Metric({ icon: Icon, label, value }) { return <div className="glass-card flex items-center gap-3 p-4"><div className="rounded-xl bg-electric-500/10 p-2.5 text-electric-300"><Icon size={17}/></div><div><div className="text-xs text-slate-500">{label}</div><div className="mt-0.5 text-lg font-semibold text-white">{value}</div></div></div>; }
function Detail({ label, value }) { return <div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div><div className="mt-1 text-sm capitalize text-slate-200">{value ?? "—"}</div></div>; }
