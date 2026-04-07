interface Props {
  summary: string | null
}

export default function NarrativeSummary({ summary }: Props) {
  if (!summary) return null

  return (
    <div
      style={{
        background: '#f0f9ff',
        border: '1px solid #bae6fd',
        borderRadius: 8,
        padding: '16px 20px',
        marginBottom: 32,
        lineHeight: 1.7,
        whiteSpace: 'pre-wrap',
      }}
    >
      <h3 style={{ margin: '0 0 8px', color: '#0369a1' }}>Narrative Summary</h3>
      <p style={{ margin: 0 }}>{summary}</p>
    </div>
  )
}
