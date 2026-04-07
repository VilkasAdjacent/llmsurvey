import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRuns } from '../api/client'
import type { RunMeta } from '../api/types'

export default function RunsPage() {
  const { surveyId } = useParams<{ surveyId: string }>()
  const [runs, setRuns] = useState<RunMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!surveyId) return
    getRuns(surveyId)
      .then(setRuns)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [surveyId])

  if (loading) return <p>Loading runs…</p>
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>

  return (
    <div>
      <p style={{ marginBottom: 4 }}>
        <Link to="/surveys">← Surveys</Link>
      </p>
      <h1>Runs — {surveyId}</h1>
      {runs.length === 0 && <p>No runs yet.</p>}
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {runs.map((r) => (
          <li
            key={r.run_id}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: '14px 20px',
              marginBottom: 10,
            }}
          >
            <Link
              to={`/surveys/${surveyId}/runs/${r.run_id}`}
              style={{ fontWeight: 600, textDecoration: 'none', color: '#4f46e5' }}
            >
              {r.run_id}
            </Link>
            <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>
              {r.models.join(', ')} · {r.participant_count} participants
              {r.has_summary ? '' : ' · no summary'}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
