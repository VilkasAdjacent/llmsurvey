import { Navigate, Route, Routes } from 'react-router-dom'
import RunPage from './pages/RunPage'
import RunsPage from './pages/RunsPage'
import SurveysPage from './pages/SurveysPage'

export default function App() {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif' }}>
      <Routes>
        <Route path="/" element={<Navigate to="/surveys" replace />} />
        <Route path="/surveys" element={<SurveysPage />} />
        <Route path="/surveys/:surveyId/runs" element={<RunsPage />} />
        <Route path="/surveys/:surveyId/runs/:runId" element={<RunPage />} />
      </Routes>
    </div>
  )
}
