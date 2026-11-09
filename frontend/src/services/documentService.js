import { api } from "./api";

export async function listDocuments() {
  const { data } = await api.get("/api/documents");
  return data;
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/api/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getDocument(documentId) {
  const { data } = await api.get(`/api/documents/${documentId}`);
  return data;
}

export async function indexVector(documentId) {
  const { data } = await api.post(`/api/vector/index/${documentId}`);
  return data;
}

export async function indexGraph(documentId) {
  const { data } = await api.post(`/api/graph/index/${documentId}`);
  return data;
}
