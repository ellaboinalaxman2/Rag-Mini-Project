export default function ErrorState({
  message = "Something went wrong.",
  onRetry,
}) {
  return (
    <div className="glass-card mx-auto max-w-lg p-6 text-center">
      <div className="mb-2 text-sm font-semibold text-rose-400">
        Request failed
      </div>
      <div className="mb-4 text-xs text-slate-400">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost text-xs">
          Try again
        </button>
      )}
    </div>
  );
}
