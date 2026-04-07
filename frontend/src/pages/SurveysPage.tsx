import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSurveys } from '../api/client'
import type { SurveyMeta } from '../api/types'

export default function SurveysPage() {
  const [surveys, setSurveys] = useState<SurveyMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSurveys()
      .then(setSurveys)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading surveys…</p>
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>
  if (surveys.length === 0) return <p>No surveys found. Run <code>llmsurvey run</code> first.</p>

  return (
    <div>
      <h1>Surveys</h1>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {surveys.map((s) => (
          <li
            key={s.id}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: '16px 20px',
              marginBottom: 12,
            }}
          >
            <Link
              to={`/surveys/${s.id}/runs`}
              style={{ fontSize: 18, fontWeight: 600, textDecoration: 'none', color: '#4f46e5' }}
            >
              {s.name}
            </Link>
            <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>
              {s.source} · {s.question_count} question{s.question_count !== 1 ? 's' : ''}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
