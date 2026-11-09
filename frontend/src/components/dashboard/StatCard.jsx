export default function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = "electric",
}) {
  const accentClass =
    accent === "violet"
      ? "from-violet-500/20 to-transparent text-violet-400"
      : accent === "emerald"
        ? "from-emerald-500/20 to-transparent text-emerald-400"
        : "from-electric-500/20 to-transparent text-electric-400";

  return (
    <div className="glass-card-hover p-5">
      <div className="flex items-start justify-between">
        <div className="text-xs uppercase tracking-wider text-slate-500">
          {label}
        </div>
        {Icon && (
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br ${accentClass}`}
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="mt-3 text-2xl font-bold text-white">{value}</div>
      {hint && <div className="mt-1 text-[11px] text-slate-500">{hint}</div>}
    </div>
  );
}
