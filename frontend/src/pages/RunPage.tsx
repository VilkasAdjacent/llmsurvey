import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRunDetail } from '../api/client'
import type { RunDetail } from '../api/types'
import NarrativeSummary from '../components/NarrativeSummary'
import QuestionChart from '../components/QuestionChart'
import StatsTable from '../components/StatsTable'

export default function RunPage() {
  const { surveyId, runId } = useParams<{ surveyId: string; runId: string }>()
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!surveyId || !runId) return
    getRunDetail(surveyId, runId)
      .then(setDetail)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [surveyId, runId])

  if (loading) return <p>Loading run…</p>
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>
  if (!detail) return null

  const questionIds = Object.keys(detail.results?.questions ?? {})

  return (
    <div>
      <p style={{ marginBottom: 4 }}>
        <Link to={`/surveys/${surveyId}/runs`}>← Runs</Link>
      </p>
      <h1 style={{ marginBottom: 4 }}>{runId}</h1>
      <p style={{ color: '#6b7280', marginTop: 0, marginBottom: 24 }}>{surveyId}</p>

      <NarrativeSummary summary={detail.summary} />

      {questionIds.map((qid) => {
        const result = detail.results.questions[qid]
        const questionStats = detail.stats?.questions?.[qid] ?? {}
        return (
          <div
            key={qid}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: '20px 24px',
              marginBottom: 24,
            }}
          >
            <h2 style={{ margin: '0 0 16px', fontSize: 16 }}>{qid}</h2>
            <QuestionChart questionId={qid} result={result} />
            {Object.keys(questionStats).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <StatsTable stats={questionStats} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
