import { useState } from "react";
import { uploadDocument } from "../api/client";

export default function FileUpload({ sessionId, onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");
    try {
      const result = await uploadDocument(sessionId, file);
      onUploaded(result);
    } catch (err) {
      setError("Upload failed. Is the backend running?");
      console.error(err);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="border border-dashed border-border rounded-lg p-3 text-xs text-gray-400">
      Upload a PDF to let the agent search <b className="text-gray-200">your own papers</b> (RAG tool).
      <input
        type="file"
        accept="application/pdf"
        onChange={handleChange}
        disabled={uploading}
        className="w-full mt-2 text-[11px] text-gray-400"
      />
      {uploading && <div className="mt-1 text-accent">Indexing…</div>}
      {error && <div className="mt-1 text-red-400">{error}</div>}
    </div>
  );
}
