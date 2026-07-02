import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Building2 } from "lucide-react";
import { tenantsApi } from "../api/resources";
import { useAuth } from "../context/AuthContext";

export default function TenantSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const { switchTenant } = useAuth();

  const { data: current } = useQuery({ queryKey: ["tenant-current"], queryFn: tenantsApi.current });
  const { data: accessible = [] } = useQuery({ queryKey: ["tenant-accessible"], queryFn: tenantsApi.accessible });

  // Only render the switcher affordance if the user actually has more than
  // one tenant to switch between — otherwise it's dead UI for the ~95% of
  // single-tenant users, showing a static label instead.
  const canSwitch = accessible.length > 1;

  return (
    <div className="relative">
      <button
        onClick={() => canSwitch && setIsOpen((v) => !v)}
        className={`flex items-center gap-2 rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm font-medium text-ink-700 ${
          canSwitch ? "cursor-pointer hover:border-ink-300" : "cursor-default"
        }`}
      >
        <Building2 size={15} className="text-ink-400" />
        <span>{current?.name || "…"}</span>
        {canSwitch && <ChevronDown size={14} className="text-ink-400" />}
      </button>

      {isOpen && canSwitch && (
        <div className="absolute left-0 top-full z-20 mt-1.5 w-56 rounded-lg border border-ink-200 bg-white py-1 shadow-lg">
          {accessible.map((t) => (
            <button
              key={t.id}
              onClick={async () => {
                await switchTenant(t.id);
                setIsOpen(false);
                window.location.reload();
              }}
              className={`block w-full px-3.5 py-2 text-left text-sm hover:bg-ink-50 ${
                t.id === current?.id ? "font-semibold text-signal-700" : "text-ink-700"
              }`}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
