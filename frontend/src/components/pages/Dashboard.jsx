import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  MessageSquare,
  Clock,
  DollarSign,
  CheckCircle2,
  Activity,
} from "lucide-react";

import Topbar from "../components/layout/Topbar";
import StatCard from "../components/dashboard/StatCard";
import RetrievalDistribution from "../components/dashboard/RetrievalDistribution";
import Loading from "../components/common/Loading";

import { listDocuments } from "../services/documentService";
import { getSummary } from "../services/monitoringService";

export default function Dashboard() {
  const docsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  const summaryQuery = useQuery({
    queryKey: ["monitoring-summary"],
    queryFn: getSummary,
    refetchInterval: 10_000,
  });

  const docCount = docsQuery.data?.total_documents ?? 0;
  const summary = summaryQuery.data?.summary;
  const metrics = summary?.queries;
  const tokens = summary?.tokens;
  const cost = summary?.cost;

  const totalQueries = metrics?.total_queries ?? 0;
  const successRate = ((metrics?.success_rate ?? 0) * 100).toFixed(1);
  const totalTokens = tokens?.total_tokens ?? 0;
  const totalCost = (cost?.total_cost_usd ?? 0).toFixed(4);

  return (
    <>
      <Topbar
        title="Dashboard"
        subtitle="System overview and intelligent retrieval analytics"
      />
      <div className="space-y-6 p-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Documents"
            value={docCount}
            icon={FileText}
            accent="electric"
            hint="Uploaded & indexed"
          />
          <StatCard
            label="Questions Asked"
            value={totalQueries}
            icon={MessageSquare}
            accent="violet"
            hint="All retrieval engines"
          />
          <StatCard
            label="Success Rate"
            value={`${successRate}%`}
            icon={CheckCircle2}
            accent="emerald"
            hint="Successful / total"
          />
          <StatCard
            label="Est. Cost (USD)"
            value={`$${totalCost}`}
            icon={DollarSign}
            accent="violet"
            hint={`${totalTokens.toLocaleString()} tokens`}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <RetrievalDistribution usage={metrics?.engine_usage} />
          </div>

          <div className="glass-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-white">
              System Status
            </h3>
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Backend</span>
                <span className="badge border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                  healthy
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Cache</span>
                <span className="badge border-white/10 bg-white/5 text-slate-300">
                  {summary?.cache_enabled ? "enabled" : "disabled"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Fallbacks</span>
                <span className="badge border-white/10 bg-white/5 text-slate-300">
                  {metrics?.fallback_count ?? 0}
                </span>
              </div>
            </div>
            <div className="mt-4 border-t border-white/5 pt-4 text-[11px] text-slate-500">
              <Activity className="mr-1 inline h-3 w-3" />
              Metrics auto-refresh every 10s
            </div>
          </div>
        </div>

        {summaryQuery.isLoading && <Loading label="Loading metrics..." />}
      </div>
    </>
  );
}
