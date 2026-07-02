import { useQuery } from "@tanstack/react-query";
import { MessageSquare, Bot, Users, CheckCircle, Gauge, TrendingUp } from "lucide-react";
import { dashboardApi } from "../api/resources";

function MetricCard({ icon: Icon, label, value, accent }) {
  return (
    <div className="rounded-xl border border-ink-200 bg-white p-5">
      <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg ${accent}`}>
        <Icon size={17} />
      </div>
      <p className="font-display text-2xl font-semibold text-ink-900">{value}</p>
      <p className="text-sm text-ink-500">{label}</p>
    </div>
  );
}

export default function MetricsPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ["dashboard-metrics"],
    queryFn: dashboardApi.metrics,
    refetchInterval: 15000,
  });

  if (isLoading || !metrics) {
    return <div className="p-6 text-sm text-ink-400">Loading metrics…</div>;
  }

  return (
    <div className="p-6">
      <h1 className="mb-1 font-display text-xl font-semibold text-ink-900">Metrics</h1>
      <p className="mb-6 text-sm text-ink-500">A snapshot of how the AI agent and your team are performing.</p>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard icon={MessageSquare} label="Total conversations" value={metrics.total_conversations} accent="bg-signal-100 text-signal-700" />
        <MetricCard icon={Bot} label="Bot active" value={metrics.active_bot_conversations} accent="bg-signal-100 text-signal-700" />
        <MetricCard icon={Users} label="Human handoff" value={metrics.human_handoff_conversations} accent="bg-amber-400/20 text-amber-500" />
        <MetricCard icon={CheckCircle} label="Resolved" value={metrics.resolved_conversations} accent="bg-ink-100 text-ink-600" />
        <MetricCard icon={TrendingUp} label="Messages (24h)" value={metrics.messages_last_24h} accent="bg-signal-100 text-signal-700" />
        <MetricCard icon={Gauge} label="Avg. bot confidence" value={metrics.avg_agent_confidence} accent="bg-signal-100 text-signal-700" />
      </div>

      <div className="mt-6 rounded-xl border border-ink-200 bg-white p-5">
        <p className="text-sm text-ink-500">Handoff rate</p>
        <div className="mt-2 flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-100">
            <div className="h-full bg-amber-400" style={{ width: `${Math.min(metrics.handoff_rate_pct, 100)}%` }} />
          </div>
          <span className="font-display text-sm font-semibold text-ink-800">{metrics.handoff_rate_pct}%</span>
        </div>
        <p className="mt-2 text-xs text-ink-400">
          Share of conversations the AI agent escalated to a human, out of all conversations.
        </p>
      </div>
    </div>
  );
}
