import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("owner@demo-store.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/conversations");
    } catch (err) {
      const detail = err.response?.data?.detail;

if (Array.isArray(detail)) {
  setError(detail[0]?.msg || "Couldn't sign in.");
} else if (typeof detail === "string") {
  setError(detail);
} else {
  setError("Couldn't sign in. Check your email and password.");
}
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2.5 text-ink-50">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-signal-500">
            <MessageCircle size={18} className="text-ink-950" strokeWidth={2.5} />
          </div>
          <span className="font-display text-lg font-semibold">WhatsApp AI Platform</span>
        </div>

        <div className="rounded-2xl border border-ink-800 bg-ink-900 p-7 shadow-2xl">
          <h1 className="font-display text-xl font-semibold text-ink-50">Sign in</h1>
          <p className="mt-1 text-sm text-ink-400">Access your conversation dashboard.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-400">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-ink-700 bg-ink-950 px-3.5 py-2.5 text-sm text-ink-50 outline-none placeholder:text-ink-500 focus:border-signal-500"
                placeholder="you@business.com"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-400">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-ink-700 bg-ink-950 px-3.5 py-2.5 text-sm text-ink-50 outline-none placeholder:text-ink-500 focus:border-signal-500"
                placeholder="••••••••"
              />
            </div>

            {error && <p className="rounded-lg bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-lg bg-signal-500 py-2.5 text-sm font-semibold text-ink-950 transition hover:bg-signal-400 disabled:opacity-60"
            >
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="mt-5 text-center text-xs text-ink-500">
            Seed demo login: owner@demo-store.test / ChangeMe123!
          </p>
        </div>
      </div>
    </div>
  );
}
