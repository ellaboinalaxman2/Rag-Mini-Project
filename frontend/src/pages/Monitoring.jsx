import { useQuery } from "@tanstack/react-query";
import { Activity, Cpu, DollarSign, Gauge, Zap } from "lucide-react";
import Topbar from "../components/layout/Topbar";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import { getMetrics, getProviders, getSummary } from "../services/monitoringService";

export default function Monitoring() {
  const summary = useQuery({ queryKey: ["monitoring-summary"], queryFn: getSummary, refetchInterval: 10000 });
  const metrics = useQuery({ queryKey: ["monitoring-metrics"], queryFn: getMetrics, refetchInterval: 10000 });
  const providers = useQuery({ queryKey: ["monitoring-providers"], queryFn: getProviders, refetchInterval: 30000 });
  if (summary.isLoading) return <><Topbar title="LLMOps Monitoring" subtitle="Runtime health, usage, latency, and estimated spend"/><Loading label="Loading system metrics…"/></>;
  if (summary.isError) return <><Topbar title="LLMOps Monitoring" subtitle="Runtime health, usage, latency, and estimated spend"/><div className="p-8"><ErrorState message={summary.error?.message} onRetry={() => summary.refetch()}/></div></>;
  const values = summary.data?.summary || {};
  const queries = values.queries || {};
  const cost = values.cost || {};
  const tokens = values.tokens || {};
  const latency = metrics.data?.latency || {};
  const providerList = providers.data?.providers;
  return <><Topbar title="LLMOps Monitoring" subtitle="Runtime health, usage, latency, and estimated spend"/><div className="space-y-6 p-8">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={Activity} label="Queries processed" value={queries.total_queries || 0}/><Metric icon={Gauge} label="Success rate" value={`${((queries.success_rate || 0) * 100).toFixed(1)}%`}/><Metric icon={Zap} label="Tokens consumed" value={(tokens.total_tokens || 0).toLocaleString()}/><Metric icon={DollarSign} label="Estimated cost" value={`$${(cost.total_cost_usd || 0).toFixed(4)}`}/></div>
    <div className="grid gap-6 lg:grid-cols-2"><section className="glass-card p-5"><h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white"><Cpu size={16} className="text-electric-300"/>Model and provider usage</h2>{providerList ? <pre className="max-h-72 overflow-auto rounded-xl bg-black/20 p-4 text-xs leading-5 text-slate-300">{JSON.stringify(providerList, null, 2)}</pre> : <p className="text-xs text-slate-500">Provider status unavailable.</p>}<div className="mt-3 grid gap-3 sm:grid-cols-2"><DataCard label="Tokens by model" data={tokens.by_provider_model}/><DataCard label="Cost by model" data={cost.by_model}/></div></section>
    <section className="glass-card p-5"><h2 className="mb-4 text-sm font-semibold text-white">Retrieval latency</h2>{Object.keys(latency).length ? <div className="space-y-3">{Object.entries(latency).flatMap(([engine, stages]) => Object.entries(stages).map(([stage, stat]) => <div key={`${engine}-${stage}`} className="rounded-xl border border-white/5 bg-white/[.025] p-3"><div className="flex justify-between gap-3"><span className="text-xs capitalize text-slate-200">{engine} · {stage.replaceAll("_", " ")}</span><span className="text-xs font-medium text-electric-300">{stat.avg_ms} ms avg</span></div><div className="mt-2 text-[10px] text-slate-500">p95 {stat.p95_ms} ms · {stat.count} samples</div></div>))}</div> : <p className="text-xs text-slate-500">No latency samples recorded yet.</p>}<div className="mt-5 grid grid-cols-2 gap-3"><DataCard label="Cache" data={{enabled: values.cache_enabled, hits: queries.cache?.hits, misses: queries.cache?.misses}}/><DataCard label="Failures and fallbacks" data={{failed: queries.failed_queries, fallbacks: queries.fallback_count}}/></div></section></div>
    <p className="text-xs text-slate-600">Metrics refresh every 10 seconds. Estimated costs depend on configured per model pricing.</p>
  </div></>;
}

function Metric({ icon: Icon, label, value }) { return <div className="glass-card flex items-center gap-3 p-4"><div className="rounded-xl bg-violet-500/10 p-2.5 text-violet-300"><Icon size={17}/></div><div><div className="text-xs text-slate-500">{label}</div><div className="mt-0.5 text-lg font-semibold text-white">{value}</div></div></div>; }
function DataCard({ label, data }) { return <div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><div className="mb-2 text-[10px] uppercase tracking-wider text-slate-500">{label}</div><pre className="max-h-24 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-4 text-slate-400">{JSON.stringify(data || {}, null, 2)}</pre></div>; }
