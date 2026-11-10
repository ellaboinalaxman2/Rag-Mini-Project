import { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  ChevronDown,
  ChevronRight,
  FileText,
  Cpu,
  Clock,
  Zap,
  Info,
} from "lucide-react";

import Topbar from "../components/layout/Topbar";
import { askRouted } from "../services/chatService";

function RouteBadge({ engine, retrievalMethod, burden, model }) {
  if (retrievalMethod === "general_fallback") {
    const burdenColors = {
      high: "border-rose-500/40 bg-rose-500/10 text-rose-400",
      medium: "border-amber-500/40 bg-amber-500/10 text-amber-400",
      low: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    };
    const color = burdenColors[burden] || "border-amber-500/40 bg-amber-500/10 text-amber-400";
    const shortModel = model ? model.split("/").pop() : "";
    return (
      <span className={`badge ${color} flex items-center gap-1.5`}>
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
        General AI • {burden ? `${burden.toUpperCase()} Burden` : "Adaptive"}
        {shortModel && <span className="opacity-75 font-mono text-[10px]">({shortModel})</span>}
      </span>
    );
  }
  const styles = {
    vector: "border-electric-500/40 bg-electric-500/10 text-electric-400",
    graph: "border-violet-500/40 bg-violet-500/10 text-violet-400",
    hybrid: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
  };
  return (
    <span
      className={`badge ${styles[engine] || "border-white/10 text-slate-300"}`}
    >
      {engine} RAG
    </span>
  );
}

function SourcesPanel({ sources = [] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-navy-900/60">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs text-slate-300"
      >
        <span className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          {sources.length} source{sources.length > 1 ? "s" : ""}
        </span>
        <span className="text-slate-500">View evidence</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-white/5 px-3 py-2">
          {sources.map((src, i) => (
            <div
              key={`${src.source_id || src.chunk_id}-${i}`}
              className="rounded-lg border border-white/5 bg-white/[0.02] p-2 text-[11px] text-slate-400"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-3 w-3 text-slate-500" />
                <span className="font-mono text-slate-300">
                  {src.source_id || `#${i + 1}`}
                </span>
                {src.filename && (
                  <span className="text-slate-500">- {src.filename}</span>
                )}
                {src.page_number && (
                  <span className="text-slate-500">
                    - page {src.page_number}
                  </span>
                )}
              </div>
              {src.similarity != null && (
                <div className="mt-1 text-slate-500">
                  similarity {src.similarity}
                </div>
              )}
              {src.evidence && (
                <div className="mt-1 italic text-slate-500">
                  "{src.evidence}"
                </div>
              )}
              {src.relation_type && (
                <div className="mt-1 text-slate-500">
                  {src.from_entity} - {src.relation_type} - {src.to_entity}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function handleSend() {
    const query = input.trim();
    if (!query || busy) return;

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setBusy(true);

    try {
      const result = await askRouted(query);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer || "(No answer generated)",
          routing: result.routing,
          retrieval_method: result.retrieval_method,
          fallback_reason: result.fallback_reason,
          burden: result.burden || result.routing?.burden,
          burden_reason: result.burden_reason || result.routing?.burden_reason,
          sources: result.sources || [],
          meta: {
            model: result.model,
            usage: result.usage,
            latency: result.total_latency_ms,
          },
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err.message}`,
          error: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  return (
    <>
      <Topbar
        title="AI Assistant"
        subtitle="Ask anything - the system routes to Vector, Graph or Hybrid automatically"
      />
      <div className="flex h-[calc(100vh-73px)] flex-col p-8">
        <div className="flex-1 space-y-4 overflow-y-auto pr-2">
          {messages.length === 0 && (
            <div className="glass-card mx-auto mt-16 max-w-lg p-8 text-center">
              <Sparkles className="mx-auto mb-3 h-8 w-8 text-electric-400" />
              <h3 className="text-base font-semibold text-white">
                Intelligent RAG Routing
              </h3>
              <p className="mt-2 text-xs text-slate-400">
                Ask a definition question to use Vector RAG. Ask about
                relationships to use Graph RAG. Ask something complex to use
                Hybrid RAG. The router decides automatically.
              </p>
              <div className="mt-4 grid gap-2 text-left text-[11px] text-slate-500">
                <div>- "What is cloud computing?" - vector</div>
                <div>- "Who developed ChatGPT?" - graph</div>
                <div>- "How are AWS and EC2 related?" - hybrid</div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className="flex gap-3">
              <div
                className={`flex h-8 w-8 flex-none items-center justify-center rounded-lg text-xs font-bold ${
                  msg.role === "user"
                    ? "bg-electric-500/20 text-electric-400"
                    : "bg-gradient-to-br from-electric-500 to-violet-500 text-white"
                }`}
              >
                {msg.role === "user" ? "U" : "AI"}
              </div>
              <div className="min-w-0 flex-1">
                <div
                  className={`glass-card ${
                    msg.error ? "border-rose-500/30" : ""
                  } px-4 py-3`}
                >
                  <div className="whitespace-pre-wrap text-sm text-slate-100">
                    {msg.content}
                  </div>

                  {msg.retrieval_method === "general_fallback" && (
                    <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                      <Info className="mt-0.5 h-4 w-4 flex-none text-amber-400" />
                      <div className="space-y-1">
                        <div className="font-medium text-amber-200">
                          This answer is from general AI knowledge, not your uploaded documents.
                        </div>
                        {msg.burden && (
                          <div className="text-[11px] text-amber-400/80">
                            Evaluated cognitive burden: <strong className="uppercase text-amber-300">{msg.burden}</strong>
                            {msg.burden_reason && <span> — {msg.burden_reason}</span>}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {msg.routing && (
                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/5 pt-3 text-[11px]">
                      <RouteBadge
                        engine={msg.routing.selected_engine}
                        retrievalMethod={msg.retrieval_method}
                        burden={msg.burden}
                        model={msg.meta?.model}
                      />
                      <span className="text-slate-500">
                        intent: {msg.routing.intent}
                      </span>
                      <span className="text-slate-500">
                        confidence:{" "}
                        {(msg.routing.routing_confidence * 100).toFixed(0)}%
                      </span>
                      {msg.routing.fallback_applied &&
                        msg.retrieval_method !== "general_fallback" && (
                          <span className="badge border-amber-500/40 bg-amber-500/10 text-amber-400">
                            fallback
                          </span>
                        )}
                    </div>
                  )}

                  {msg.routing?.reason && (
                    <div className="mt-2 text-[11px] italic text-slate-500">
                      {msg.routing.reason}
                    </div>
                  )}

                  <SourcesPanel sources={msg.sources} />

                  {msg.meta && (
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-slate-500">
                      {msg.meta.model && (
                        <span className="flex items-center gap-1">
                          <Cpu className="h-3 w-3" />
                          {msg.meta.model}
                        </span>
                      )}
                      {msg.meta.latency && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {msg.meta.latency.toFixed(0)}ms
                        </span>
                      )}
                      {msg.meta.usage?.total_tokens && (
                        <span className="flex items-center gap-1">
                          <Zap className="h-3 w-3" />
                          {msg.meta.usage.total_tokens} tokens
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {busy && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 flex-none items-center justify-center rounded-lg bg-gradient-to-br from-electric-500 to-violet-500 text-xs font-bold text-white">
                AI
              </div>
              <div className="glass-card flex items-center gap-2 px-4 py-3 text-xs text-slate-400">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-electric-400" />
                Analyzing query and selecting retrieval engine...
              </div>
            </div>
          )}

          <div ref={scrollRef} />
        </div>

        <div className="mt-4 flex items-end gap-2">
          <textarea
            rows={1}
            className="input-dark resize-none"
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={busy}
          />
          <button
            onClick={handleSend}
            disabled={busy || !input.trim()}
            className="btn-primary flex items-center gap-2"
          >
            <Send className="h-4 w-4" />
            Send
          </button>
        </div>
      </div>
    </>
  );
}
