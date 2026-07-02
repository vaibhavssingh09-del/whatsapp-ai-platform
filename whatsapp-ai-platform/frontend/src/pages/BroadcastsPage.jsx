import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Megaphone, X, Plus } from "lucide-react";
import { broadcastsApi } from "../api/resources";

const STATUS_STYLES = {
  draft: "bg-ink-100 text-ink-600",
  scheduled: "bg-amber-400/20 text-amber-500",
  sending: "bg-signal-100 text-signal-700",
  completed: "bg-signal-100 text-signal-700",
  failed: "bg-red-100 text-red-600",
  cancelled: "bg-ink-100 text-ink-400",
};

function BroadcastDrawer({ onClose }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [templateLanguage, setTemplateLanguage] = useState("en_US");
  const [recipients, setRecipients] = useState("");

  const createMutation = useMutation({
    mutationFn: broadcastsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] });
      onClose();
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    createMutation.mutate({
      name,
      template_name: templateName,
      template_language: templateLanguage,
      template_variables: {},
      recipient_wa_contact_ids: recipients
        .split(/[\n,]/)
        .map((r) => r.trim())
        .filter(Boolean),
    });
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30">
      <div className="flex h-full w-full max-w-md flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-ink-200 p-5">
          <h2 className="font-display text-lg font-semibold text-ink-900">New broadcast</h2>
          <button onClick={onClose}>
            <X size={18} className="text-ink-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 space-y-4 overflow-y-auto p-5">
          <p className="rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-600">
            Broadcasts always send a Meta-approved template message. This is a WhatsApp policy
            requirement for business-initiated messages outside the 24-hour window — free text
            isn't permitted here.
          </p>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">Campaign name</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-signal-500"
              placeholder="July Sale Announcement"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">Approved template name</label>
            <input
              required
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-signal-500"
              placeholder="july_sale_announcement"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">Template language code</label>
            <input
              required
              value={templateLanguage}
              onChange={(e) => setTemplateLanguage(e.target.value)}
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-signal-500"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-500">
              Recipient numbers (one per line, E.164 without '+')
            </label>
            <textarea
              required
              rows={5}
              value={recipients}
              onChange={(e) => setRecipients(e.target.value)}
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-signal-500"
              placeholder={"919812345678\n14155550101"}
            />
          </div>

          {createMutation.isError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {createMutation.error?.response?.data?.detail || "Failed to create broadcast"}
            </p>
          )}

          <button
            type="submit"
            disabled={createMutation.isPending}
            className="w-full rounded-lg bg-signal-500 py-2.5 text-sm font-semibold text-ink-950 hover:bg-signal-400 disabled:opacity-60"
          >
            {createMutation.isPending ? "Sending…" : "Send broadcast"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function BroadcastsPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { data: broadcasts = [], isLoading } = useQuery({ queryKey: ["broadcasts"], queryFn: broadcastsApi.list });

  return (
    <div className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink-900">Broadcast campaigns</h1>
          <p className="text-sm text-ink-500">Send approved WhatsApp templates to a list of customers.</p>
        </div>
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-semibold text-ink-950 hover:bg-signal-400"
        >
          <Plus size={16} /> New broadcast
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-ink-400">Loading…</p>
      ) : broadcasts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ink-200 p-10 text-center text-sm text-ink-400">
          <Megaphone className="mx-auto mb-2 text-ink-300" size={28} />
          No broadcasts yet.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-ink-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-400">
              <tr>
                <th className="px-4 py-3">Campaign</th>
                <th className="px-4 py-3">Template</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Sent</th>
                <th className="px-4 py-3">Failed</th>
              </tr>
            </thead>
            <tbody>
              {broadcasts.map((b) => (
                <tr key={b.id} className="border-t border-ink-100">
                  <td className="px-4 py-3 font-medium text-ink-800">{b.name}</td>
                  <td className="px-4 py-3 text-ink-500">{b.template_name}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[b.status]}`}>
                      {b.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-ink-700">{b.sent_count}</td>
                  <td className="px-4 py-3 text-ink-700">{b.failed_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {drawerOpen && <BroadcastDrawer onClose={() => setDrawerOpen(false)} />}
    </div>
  );
}
