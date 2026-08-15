import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: BASE_URL, timeout: 120000 });

export async function sendChatMessage(sessionId, query) {
  const { data } = await client.post("/api/chat", { session_id: sessionId, query });
  return data;
}

export async function uploadDocument(sessionId, file) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", file);
  const { data } = await client.post("/api/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function checkHealth() {
  const { data } = await client.get("/api/health");
  return data;
}

// ---- Evaluation ----
export async function runEvaluation() {
  // Evaluation runs 10 real end-to-end pipeline calls - can take minutes.
  const { data } = await client.post("/api/eval/run", {}, { timeout: 600000 });
  return data;
}

export async function listEvalRuns() {
  const { data } = await client.get("/api/eval/runs");
  return data;
}

export async function getEvalRun(runId) {
  const { data } = await client.get(`/api/eval/runs/${runId}`);
  return data;
}

export function downloadEvalRunUrl(runId, format) {
  return `${BASE_URL}/api/eval/runs/${runId}/download?format=${format}`;
}
