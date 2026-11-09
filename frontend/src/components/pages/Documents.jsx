import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Layers, Network } from "lucide-react";

import Topbar from "../components/layout/Topbar";
import Loading from "../components/common/Loading";
import ErrorState from "../components/common/ErrorState";

import {
  listDocuments,
  uploadDocument,
  indexVector,
  indexGraph,
} from "../services/documentService";

export default function Documents() {
  const queryClient = useQueryClient();
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [busy, setBusy] = useState({});

  const docsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  async function handleFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocument(file);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleIndex(docId, kind) {
    setBusy((prev) => ({ ...prev, [docId]: kind }));
    try {
      if (kind === "vector") await indexVector(docId);
      else await indexGraph(docId);
    } catch (err) {
      alert(`${kind} index failed: ${err.message}`);
    } finally {
      setBusy((prev) => {
        const next = { ...prev };
        delete next[docId];
        return next;
      });
    }
  }

  const docs = docsQuery.data?.documents ?? [];

  return (
    <>
      <Topbar
        title="Documents"
        subtitle="Upload and manage your knowledge base"
      />
      <div className="space-y-6 p-8">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Upload Document
              </h3>
              <p className="mt-1 text-xs text-slate-400">
                PDF or DOCX · Max 10 MB · Duplicate detection enabled
              </p>
            </div>
            <div>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={handleFile}
              />
              <button
                className="btn-primary flex items-center gap-2"
                disabled={uploading}
                onClick={() => inputRef.current?.click()}
              >
                <Upload className="h-4 w-4" />
                {uploading ? "Processing..." : "Choose file"}
              </button>
            </div>
          </div>
          {uploadError && (
            <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
              {uploadError}
            </div>
          )}
        </div>

        {docsQuery.isLoading && <Loading label="Loading documents..." />}
        {docsQuery.isError && (
          <ErrorState
            message={docsQuery.error?.message}
            onRetry={() => docsQuery.refetch()}
          />
        )}

        {!docsQuery.isLoading && docs.length === 0 && (
          <div className="glass-card flex flex-col items-center justify-center py-16 text-center">
            <FileText className="mb-3 h-10 w-10 text-slate-600" />
            <div className="text-sm text-slate-300">No documents yet</div>
            <div className="mt-1 text-xs text-slate-500">
              Upload a PDF or DOCX to get started
            </div>
          </div>
        )}

        {docs.length > 0 && (
          <div className="glass-card overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-white/5 bg-white/[0.02] text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Filename</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Chunks</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-slate-500" />
                        <span className="text-slate-200">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-slate-400">
                      {doc.file_type}
                    </td>
                    <td className="px-5 py-3 text-slate-400">
                      {doc.chunk_count}
                    </td>
                    <td className="px-5 py-3">
                      <span className="badge border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          className="btn-ghost flex items-center gap-1 text-xs"
                          onClick={() => handleIndex(doc.id, "vector")}
                          disabled={busy[doc.id]}
                        >
                          <Layers className="h-3 w-3" />
                          {busy[doc.id] === "vector" ? "Indexing..." : "Vector"}
                        </button>
                        <button
                          className="btn-ghost flex items-center gap-1 text-xs"
                          onClick={() => handleIndex(doc.id, "graph")}
                          disabled={busy[doc.id]}
                        >
                          <Network className="h-3 w-3" />
                          {busy[doc.id] === "graph" ? "Building..." : "Graph"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
