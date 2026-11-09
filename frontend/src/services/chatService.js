import { api } from "./api";

export async function askRouted(query, documentId = null) {
  const body = { query };
  if (documentId) body.document_id = documentId;
  const { data } = await api.post("/api/router/query", body);
  return data;
}

export async function analyzeQuery(query) {
  const { data } = await api.post("/api/router/analyze", { query });
  return data;
}
