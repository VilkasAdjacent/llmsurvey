import type { ModelStats } from '../api/types'

interface Props {
  stats: Record<string, ModelStats>
}

function divergenceColor(value: number): string {
  if (value < 0.05) return '#16a34a'
  if (value < 0.15) return '#ca8a04'
  return '#dc2626'
}

export default function StatsTable({ stats }: Props) {
  const models = Object.keys(stats)
  if (models.length === 0) return null

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ background: '#f3f4f6' }}>
          <th style={th}>Model</th>
          <th style={th}>χ² p-value</th>
          <th style={th}>KL div</th>
          <th style={th}>JS div</th>
          <th style={th}>Bias direction</th>
          <th style={th}>Parse failures</th>
        </tr>
      </thead>
      <tbody>
        {models.map((model) => {
          const s = stats[model]
          return (
            <tr key={model} style={{ borderBottom: '1px solid #e5e7eb' }}>
              <td style={td}>{model}</td>
              <td style={td}>
                {s.chi_square_p != null ? s.chi_square_p.toFixed(4) : '—'}
              </td>
              <td style={{ ...td, color: divergenceColor(s.kl_divergence), fontWeight: 600 }}>
                {s.kl_divergence.toFixed(4)}
              </td>
              <td style={{ ...td, color: divergenceColor(s.js_divergence), fontWeight: 600 }}>
                {s.js_divergence.toFixed(4)}
              </td>
              <td style={td}>{s.bias_direction}</td>
              <td style={td}>{(s.parse_failure_rate * 100).toFixed(1)}%</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

const th: React.CSSProperties = {
  padding: '6px 10px',
  textAlign: 'left',
  fontWeight: 600,
  borderBottom: '2px solid #d1d5db',
}

const td: React.CSSProperties = {
  padding: '6px 10px',
}
