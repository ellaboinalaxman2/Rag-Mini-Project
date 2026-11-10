import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BookOpenCheck,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FlaskConical,
  Plus,
  RotateCw,
  Trash2,
  XCircle,
  Zap,
} from "lucide-react";

import Topbar from "../components/layout/Topbar";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";
import { listDocuments } from "../services/documentService";
import { api } from "../services/api";

const MAX_CASES = 10;

function newCase() {
  return { query: "", expected_answer: "", document_id: "" };
}

function percent(value) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function MetricCard({ icon: Icon, label, value, note, color = "electric" }) {
  const colors = {
    electric: "bg-electric-500/10 text-electric-300",
    violet: "bg-violet-500/10 text-violet-300",
    emerald: "bg-emerald-500/10 text-emerald-300",
    amber: "bg-amber-500/10 text-amber-300",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card flex min-w-0 items-center gap-3 p-4"
    >
      <div className={`rounded-xl p-2.5 ${colors[color]}`}>
        <Icon size={17} />
      </div>
      <div className="min-w-0">
        <div className="text-xs text-slate-500">{label}</div>
        <div className="mt-0.5 truncate text-lg font-semibold text-white">
          {value}
        </div>
        <div className="mt-0.5 truncate text-[10px] text-slate-500">{note}</div>
      </div>
    </motion.div>
  );
}

function CaseResult({ result }) {
  const passed = result.status === "passed";
  const failed = result.status === "error";
  const StatusIcon = passed ? CheckCircle2 : failed ? CircleAlert : XCircle;
  const statusColor = passed
    ? "text-emerald-300"
    : failed
      ? "text-rose-300"
      : "text-amber-300";

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card overflow-hidden"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 px-4 py-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 text-xs font-mono text-slate-500">
            #{String(result.case_index).padStart(2, "0")}
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-slate-100">{result.query}</h3>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-500">
              <span className="capitalize">{result.retrieval_method || "no route"}</span>
              {result.engine_used && <span>engine: {result.engine_used}</span>}
              {result.model && <span className="font-mono">{result.model}</span>}
            </div>
          </div>
        </div>
        <div className={`flex items-center gap-1.5 text-xs ${statusColor}`}>
          <StatusIcon size={14} />
          {passed ? "Answered" : failed ? "Error" : "No answer"}
        </div>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[1fr_auto]">
        <div className="space-y-3">
          {result.expected_answer && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">
                Reference answer
              </div>
              <p className="text-xs leading-5 text-slate-400">
                {result.expected_answer}
              </p>
            </div>
          )}
          {result.answer && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">
                Generated answer
              </div>
              <p className="whitespace-pre-wrap text-xs leading-5 text-slate-200">
                {result.answer}
              </p>
            </div>
          )}
          {result.sources?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.sources.map((source, sourceIndex) => (
                <span
                  key={`${source.source_id || source.chunk_id || source.entity_id || sourceIndex}`}
                  className="rounded-md border border-white/5 bg-white/[0.025] px-2 py-1 text-[9px] text-slate-400"
                >
                  {source.filename || source.entity_name || source.source_id || `Source ${sourceIndex + 1}`}
                  {source.page_number ? ` · p.${source.page_number}` : ""}
                </span>
              ))}
            </div>
          )}
          {result.error && (
            <p role="alert" className="text-xs text-rose-300">
              {result.error}
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-2 lg:max-w-64 lg:justify-end">
          {result.answer_f1 != null && (
            <ScoreChip label="Token F1" value={percent(result.answer_f1)} />
          )}
          <ScoreChip label="Sources" value={result.source_count} />
          {result.document_retrieved != null && (
            <ScoreChip
              label="Expected doc"
              value={result.document_retrieved ? "Hit" : "Miss"}
              good={result.document_retrieved}
            />
          )}
          <ScoreChip label="Latency" value={`${result.latency_ms} ms`} />
          {result.usage?.total_tokens > 0 && (
            <ScoreChip label="Tokens" value={result.usage.total_tokens} />
          )}
        </div>
      </div>
    </motion.article>
  );
}

function ScoreChip({ label, value, good }) {
  const color =
    good === true
      ? "text-emerald-300"
      : good === false
        ? "text-rose-300"
        : "text-slate-200";
  return (
    <div className="min-w-16 rounded-lg border border-white/5 bg-white/[0.025] px-2.5 py-2 text-right">
      <div className="text-[9px] uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`mt-0.5 text-xs font-semibold ${color}`}>{value}</div>
    </div>
  );
}

export default function Evaluation() {
  const queryClient = useQueryClient();
  const [cases, setCases] = useState([newCase()]);
  const [run, setRun] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });
  const historyQuery = useQuery({
    queryKey: ["evaluation-runs"],
    queryFn: async () => (await api.get("/api/evaluation/runs")).data.runs,
  });
  const documents = documentsQuery.data?.documents ?? [];

  function updateCase(index, key, value) {
    setCases((previous) =>
      previous.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [key]: value } : item,
      ),
    );
  }

  async function runEvaluation(event) {
    event.preventDefault();
    if (busy) return;
    const validCases = cases.filter((item) => item.query.trim());
    if (!validCases.length) {
      setError("Add at least one question before running an evaluation.");
      return;
    }

    setBusy(true);
    setError("");
    setRun(null);
    try {
      const payload = {
        cases: validCases.map((item) => ({
          query: item.query.trim(),
          expected_answer: item.expected_answer.trim() || null,
          document_id: item.document_id || null,
        })),
      };
      const { data } = await api.post("/api/evaluation/run", payload, {
        timeout: 300000,
      });
      setRun(data);
      await queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function openRun(runId) {
    setError("");
    try {
      const { data } = await api.get(`/api/evaluation/runs/${runId}`);
      setRun(data);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const summary = run?.summary;
  const runHistory = historyQuery.data ?? [];

  return (
    <>
      <Topbar
        title="Evaluation Center"
        subtitle="Benchmark routed answers against references and document evidence"
      />
      <div className="space-y-6 p-8">
        <section className="glass-card p-5">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
                <FlaskConical size={16} className="text-violet-300" />
                Evaluation dataset
              </h2>
              <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">
                Add up to {MAX_CASES} questions. A reference answer enables
                token-overlap F1 scoring; selecting a document checks whether
                the answer is grounded in that document.
              </p>
            </div>
            <span className="badge border-white/10 bg-white/5 text-slate-300">
              {cases.length}/{MAX_CASES} cases
            </span>
          </div>

          <form onSubmit={runEvaluation} className="space-y-3">
            <AnimatePresence initial={false}>
              {cases.map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="grid gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3 xl:grid-cols-[1fr_1fr_220px_40px]"
                >
                  <label className="text-[10px] text-slate-400">
                    Question
                    <textarea
                      required
                      rows={2}
                      maxLength={2000}
                      className="input-dark mt-1 min-h-16 resize-y text-xs"
                      placeholder="e.g. What is an operating system?"
                      value={item.query}
                      onChange={(event) =>
                        updateCase(index, "query", event.target.value)
                      }
                      disabled={busy}
                    />
                  </label>
                  <label className="text-[10px] text-slate-400">
                    Reference answer
                    <textarea
                      rows={2}
                      maxLength={5000}
                      className="input-dark mt-1 min-h-16 resize-y text-xs"
                      placeholder="Optional - used for token F1 scoring"
                      value={item.expected_answer}
                      onChange={(event) =>
                        updateCase(index, "expected_answer", event.target.value)
                      }
                      disabled={busy}
                    />
                  </label>
                  <label className="text-[10px] text-slate-400">
                    Expected document
                    <select
                      className="input-dark mt-1 text-xs"
                      value={item.document_id}
                      onChange={(event) =>
                        updateCase(index, "document_id", event.target.value)
                      }
                      disabled={busy || documentsQuery.isLoading}
                    >
                      <option value="">All documents / general</option>
                      {documents.map((document) => (
                        <option key={document.id} value={document.id}>
                          {document.filename}
                        </option>
                      ))}
                    </select>
                    <span className="mt-1 block text-[9px] text-slate-600">
                      Leave blank to test general routing.
                    </span>
                  </label>
                  <button
                    type="button"
                    className="btn-ghost self-center justify-self-end p-2 text-slate-500 hover:text-rose-300"
                    title="Remove test case"
                    aria-label={`Remove test case ${index + 1}`}
                    disabled={busy || cases.length === 1}
                    onClick={() =>
                      setCases((previous) =>
                        previous.filter((_, itemIndex) => itemIndex !== index),
                      )
                    }
                  >
                    <Trash2 size={15} />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <button
                type="button"
                className="btn-ghost flex items-center gap-2 text-xs"
                disabled={busy || cases.length >= MAX_CASES}
                onClick={() => setCases((previous) => [...previous, newCase()])}
              >
                <Plus size={14} />
                Add test case
              </button>
              <button
                type="submit"
                className="btn-primary flex items-center gap-2"
                disabled={busy || documentsQuery.isError}
              >
                {busy ? (
                  <RotateCw size={15} className="animate-spin" />
                ) : (
                  <FlaskConical size={15} />
                )}
                {busy ? "Running evaluation…" : "Run evaluation"}
              </button>
            </div>
          </form>
          {documentsQuery.isError && (
            <p role="alert" className="mt-3 text-xs text-rose-300">
              Could not load documents: {documentsQuery.error.message}
            </p>
          )}
          {error && (
            <p role="alert" className="mt-3 text-xs text-rose-300">
              {error}
            </p>
          )}
        </section>

        {historyQuery.isError && (
          <ErrorState
            message={historyQuery.error.message}
            onRetry={() => historyQuery.refetch()}
          />
        )}
        {historyQuery.isLoading && <Loading label="Loading evaluation history…" />}
        {!historyQuery.isLoading && runHistory.length > 0 && (
          <section className="glass-card p-4">
            <div className="mb-3 text-xs font-semibold text-slate-200">
              Recent runs
            </div>
            <div className="flex flex-wrap gap-2">
              {runHistory.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => openRun(item.id)}
                  className={`rounded-lg border px-3 py-2 text-left transition ${
                    run?.id === item.id
                      ? "border-electric-400/40 bg-electric-500/10"
                      : "border-white/5 bg-white/[0.02] hover:border-white/15"
                  }`}
                >
                  <span className="block text-[10px] text-slate-300">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                  <span className="mt-1 block text-[9px] text-slate-500">
                    {item.case_count} cases · {percent(item.summary.answer_rate)} answered
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        {run && (
          <motion.section
            key={run.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-white">
                  Run results
                </h2>
                <p className="mt-1 text-[10px] text-slate-500">
                  {new Date(run.created_at).toLocaleString()} · run {run.id.slice(0, 8)}
                </p>
              </div>
              <p className="text-[10px] text-slate-500">
                Reference scoring is lexical token F1, not an LLM judge.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <MetricCard
                icon={CheckCircle2}
                label="Answer rate"
                value={percent(summary.answer_rate)}
                note={`${summary.answered_cases}/${summary.total_cases} received an answer`}
                color="emerald"
              />
              <MetricCard
                icon={Activity}
                label="Mean token F1"
                value={percent(summary.mean_answer_f1)}
                note={`${summary.reference_cases} cases with a reference`}
                color="violet"
              />
              <MetricCard
                icon={BookOpenCheck}
                label="Evidence rate"
                value={percent(summary.evidence_rate)}
                note="Answers with at least one source"
              />
              <MetricCard
                icon={ArrowUpRight}
                label="Document hit rate"
                value={percent(summary.document_hit_rate)}
                note={`${summary.document_cases} document-scoped cases`}
                color="emerald"
              />
              <MetricCard
                icon={Clock3}
                label="Mean latency"
                value={`${summary.mean_latency_ms} ms`}
                note={`${summary.total_tokens.toLocaleString()} total tokens`}
                color="amber"
              />
            </div>

            <div className="space-y-3">
              {run.results.map((result) => (
                <CaseResult key={`${run.id}-${result.case_index}`} result={result} />
              ))}
            </div>
          </motion.section>
        )}

        {!run && !runHistory.length && !historyQuery.isLoading && (
          <div className="glass-card flex flex-col items-center px-6 py-12 text-center">
            <div className="rounded-2xl bg-violet-500/10 p-3 text-violet-300">
              <FlaskConical size={22} />
            </div>
            <h2 className="mt-4 text-sm font-semibold text-white">
              Your benchmark starts here
            </h2>
            <p className="mt-2 max-w-md text-xs leading-5 text-slate-400">
              Add a few representative questions, their reference answers, and
              the document each question should use. Run the same set again
              after changing retrieval or routing to compare results.
            </p>
            <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-500">
              <ArrowDownRight size={13} />
              Results and run history are saved locally in the project database.
              <Zap size={12} />
            </div>
          </div>
        )}
      </div>
    </>
  );
}
