import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { QuestionResult } from '../api/types'

const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#ec4899']

interface Props {
  questionId: string
  result: QuestionResult
}

export default function QuestionChart({ result }: Props) {
  const options = Object.keys(result.real)
  const modelNames = Object.keys(result.models)
  const sources = ['real', ...modelNames]

  const data = options.map((opt) => {
    const point: Record<string, string | number> = { option: opt }
    point['real'] = result.real[opt] ?? 0
    for (const model of modelNames) {
      point[model] = result.models[model]?.[opt] ?? 0
    }
    return point
  })

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="option"
          tick={{ fontSize: 12 }}
          angle={-25}
          textAnchor="end"
          interval={0}
        />
        <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} domain={[0, 1]} />
        <Tooltip formatter={(v) => typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : v} />
        <Legend verticalAlign="top" />
        {sources.map((src, i) => (
          <Bar key={src} dataKey={src} fill={COLORS[i % COLORS.length]} maxBarSize={40} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
