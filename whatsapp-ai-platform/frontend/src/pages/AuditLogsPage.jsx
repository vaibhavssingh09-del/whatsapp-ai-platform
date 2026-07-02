import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../api/resources";

export default function AuditLogsPage() {
  const { data: logs = [], isLoading } = useQuery({ queryKey: ["audit-logs"], queryFn: dashboardApi.auditLogs });

  return (
    <div className="p-6">
      <h1 className="mb-1 font-display text-xl font-semibold text-ink-900">Audit logs</h1>
      <p className="mb-6 text-sm text-ink-500">Every security-relevant action taken by users and the AI agent.</p>

      {isLoading ? (
        <p className="text-sm text-ink-400">Loading…</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-ink-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-400">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-t border-ink-100 font-mono text-xs">
                  <td className="whitespace-nowrap px-4 py-3 text-ink-500">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-ink-700">{log.actor_label}</td>
                  <td className="px-4 py-3 font-semibold text-signal-700">{log.action}</td>
                  <td className="px-4 py-3 text-ink-500">
                    {log.resource_type}
                    {log.resource_id ? `:${log.resource_id.slice(-6)}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && <p className="p-6 text-center text-sm text-ink-400">No audit events yet.</p>}
        </div>
      )}
    </div>
  );
}
