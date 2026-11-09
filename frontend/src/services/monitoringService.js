import { api } from "./api";

export async function getSummary() {
  const { data } = await api.get("/api/monitoring/summary");
  return data;
}

export async function getMetrics() {
  const { data } = await api.get("/api/monitoring/metrics");
  return data;
}

export async function getProviders() {
  const { data } = await api.get("/api/monitoring/providers");
  return data;
}
