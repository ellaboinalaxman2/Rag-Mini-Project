export default function Topbar({ title, subtitle }) {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-white/5 bg-navy-900/80 px-8 py-4 backdrop-blur-md">
      <div>
        <h1 className="text-xl font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 md:flex">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Backend connected
        </div>
      </div>
    </header>
  );
}
