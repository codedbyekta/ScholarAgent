import ReactMarkdown from "react-markdown";

export default function MessageBubble({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`max-w-3xl px-4 py-3 rounded-lg leading-relaxed ${
      isUser
        ? "self-end bg-accent text-white"
        : "self-start bg-panel border border-border prose-invert-custom"
    }`}>
      {isUser ? <span>{content}</span> : <ReactMarkdown>{content}</ReactMarkdown>}
    </div>
  );
}
