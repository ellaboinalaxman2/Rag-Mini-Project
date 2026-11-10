import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  Route,
  Activity,
  FlaskConical,
  FileText,
  Sparkles,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/assistant", label: "AI Assistant", icon: MessageSquare },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/graph", label: "Knowledge Graph", icon: Network },
  { to: "/routing", label: "Routing Analytics", icon: Route },
  { to: "/monitoring", label: "LLMOps Monitoring", icon: Activity },
  {
    to: "/evaluation",
    label: "Evaluation Center",
    icon: FlaskConical,
  },
];

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-white/5 bg-navy-900">
      <div className="flex items-center gap-3 border-b border-white/5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-electric-500 to-violet-500 shadow-glow">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-wide text-white">
            INTELLIGENT RAG
          </div>
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-emerald-400">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Online
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end, soon }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              [
                "group mb-1 flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition",
                isActive
                  ? "bg-gradient-to-r from-electric-500/20 to-violet-500/20 text-white shadow-[inset_0_0_0_1px_rgba(59,130,246,0.3)]"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-100",
              ].join(" ")
            }
          >
            <span className="flex items-center gap-3">
              <Icon className="h-4 w-4" />
              {label}
            </span>
            {soon && (
              <span className="rounded-md bg-white/5 px-1.5 py-0.5 text-[9px] uppercase text-slate-500">
                Soon
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/5 px-4 py-4 text-[11px] text-slate-500">
        <div>v1.0.0 · Phase 9A</div>
        <div className="mt-1">Vector · Graph · Hybrid</div>
      </div>
    </aside>
  );
}
