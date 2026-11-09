import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

const COLORS = { vector: "#3b82f6", graph: "#8b5cf6", hybrid: "#10b981" };

export default function RetrievalDistribution({ usage = {} }) {
  const data = ["vector", "graph", "hybrid"].map((key) => ({
    name: key,
    count: usage[key] || 0,
  }));

  const empty = data.every((d) => d.count === 0);

  return (
    <div className="glass-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">
          Retrieval Engine Usage
        </h3>
        <span className="text-[11px] text-slate-500">Session</span>
      </div>

      {empty ? (
        <div className="flex h-48 items-center justify-center text-xs text-slate-500">
          No queries yet — ask something in the AI Assistant.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={data}
            margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2344" />
            <XAxis
              dataKey="name"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              tickLine={false}
            />
            <YAxis
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "#0b1020",
                border: "1px solid #233057",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "#e5e7eb" }}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
