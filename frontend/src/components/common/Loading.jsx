export default function Loading({ label = "Loading..." }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-400">
      <span className="mr-3 inline-block h-4 w-4 animate-spin rounded-full border-2 border-electric-500 border-t-transparent" />
      {label}
    </div>
  );
}
