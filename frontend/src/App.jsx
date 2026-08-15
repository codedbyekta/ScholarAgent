import { useState } from "react";
import ChatView from "./components/ChatView.jsx";
import EvalDashboard from "./components/EvalDashboard.jsx";

export default function App() {
  const [tab, setTab] = useState("chat");

  return (
    <div className="h-screen flex flex-col">
      <header className="flex items-center gap-1 border-b border-border px-4 py-2 shrink-0">
        <button
          onClick={() => setTab("chat")}
          className={`text-sm px-3 py-1.5 rounded-md ${
            tab === "chat" ? "bg-accent text-white" : "text-gray-400 hover:text-gray-200"
          }`}
        >
          Chat
        </button>
        <button
          onClick={() => setTab("eval")}
          className={`text-sm px-3 py-1.5 rounded-md ${
            tab === "eval" ? "bg-accent text-white" : "text-gray-400 hover:text-gray-200"
          }`}
        >
          Evaluation Dashboard
        </button>
      </header>

      <div className="flex-1 overflow-hidden">
        {tab === "chat" ? <ChatView /> : <EvalDashboard />}
      </div>
    </div>
  );
}
