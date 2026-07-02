import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, CheckCircle2, Bot, UserCircle2 } from "lucide-react";
import { conversationsApi } from "../api/resources";

const STATUS_STYLES = {
  bot_active: "bg-signal-100 text-signal-700",
  human_handoff: "bg-amber-400/20 text-amber-500",
  resolved: "bg-ink-200 text-ink-600",
  archived: "bg-ink-100 text-ink-400",
};

function ConversationList({ selectedId, onSelect, statusFilter, setStatusFilter }) {
  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ["conversations", statusFilter],
    queryFn: () => conversationsApi.list(statusFilter || undefined),
    refetchInterval: 8000, // near-real-time monitor without a websocket: cheap and adequate for this scale
  });

  return (
    <div className="flex w-full max-w-xs flex-col border-r border-ink-200 bg-white md:w-80">
      <div className="border-b border-ink-200 p-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-full rounded-lg border border-ink-200 bg-ink-50 px-2.5 py-2 text-sm text-ink-700"
        >
          <option value="">All conversations</option>
          <option value="bot_active">Bot active</option>
          <option value="human_handoff">Needs human</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>
      <div className="flex-1 overflow-y-auto">
        {isLoading && <p className="p-4 text-sm text-ink-400">Loading…</p>}
        {conversations.map((c) => (
          <button
            key={c._id}
            onClick={() => {
              console.log("Clicked conversation:", c);
              onSelect(c._id);
            }}
            className={`flex w-full flex-col gap-1 border-b border-ink-100 px-4 py-3 text-left transition ${
              selectedId === c._id ? "bg-signal-50" : "hover:bg-ink-50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-ink-800">{c.contact_name || c.wa_contact_id}</span>
              {c.unread_count > 0 && (
                <span className="rounded-full bg-signal-500 px-1.5 py-0.5 text-[10px] font-bold text-ink-950">
                  {c.unread_count}
                </span>
              )}
            </div>
            <p className="truncate text-xs text-ink-500">{c.last_message_preview || "No messages yet"}</p>
            <span className={`w-fit rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[c.status]}`}>
              {c.status.replace("_", " ")}
            </span>
          </button>
        ))}
        {!isLoading && conversations.length === 0 && (
          <p className="p-4 text-sm text-ink-400">No conversations match this filter.</p>
        )}
      </div>
    </div>
  );
}

function LiveChatView({ conversationId }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");

  const { data: messages = [] } = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => conversationsApi.messages(conversationId),
    enabled: !!conversationId,
    refetchInterval: 5000,
  });

  const replyMutation = useMutation({
    mutationFn: (text) => conversationsApi.reply(conversationId, text),
    onSuccess: () => {
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => conversationsApi.resolve(conversationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });

  if (!conversationId) {
    return <div className="flex flex-1 items-center justify-center text-sm text-ink-400">Select a conversation</div>;
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-ink-200 bg-white px-5 py-3">
        <h2 className="font-display text-base font-semibold text-ink-800">Live chat</h2>
        <button
          onClick={() => resolveMutation.mutate()}
          className="flex items-center gap-1.5 rounded-lg border border-ink-200 px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50"
        >
          <CheckCircle2 size={14} /> Mark resolved
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto bg-ink-50 p-5">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.direction === "outbound" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-md rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                m.direction === "outbound" ? "bg-signal-500 text-ink-950" : "bg-white text-ink-800"
              }`}
            >
              <p>{m.text}</p>
              {m.direction === "outbound" && (
                <div className="mt-1 flex items-center gap-1.5 text-[10px] opacity-70">
                  {m.sent_by_bot ? <Bot size={11} /> : <UserCircle2 size={11} />}
                  <span>
                    {m.sent_by_bot ? `Bot · confidence ${(m.agent_confidence ?? 0).toFixed(2)}` : "Agent"}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
        {messages.length === 0 && <p className="text-sm text-ink-400">No messages yet.</p>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (draft.trim()) replyMutation.mutate(draft.trim());
        }}
        className="flex items-center gap-2 border-t border-ink-200 bg-white p-3"
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type a reply as an operator…"
          className="flex-1 rounded-lg border border-ink-200 px-3.5 py-2.5 text-sm outline-none focus:border-signal-500"
        />
        <button
          type="submit"
          disabled={replyMutation.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-semibold text-ink-950 hover:bg-signal-400 disabled:opacity-60"
        >
          <Send size={14} /> Send
        </button>
      </form>
    </div>
  );
}

export default function ConversationMonitorPage() {
  const [selectedId, setSelectedId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");

  return (
    <div className="flex h-full">
      <ConversationList
        selectedId={selectedId}
        onSelect={setSelectedId}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
      />
      <LiveChatView conversationId={selectedId} />
    </div>
  );
}
