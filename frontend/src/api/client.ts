import type { RunDetail, RunMeta, SurveyMeta } from './types'

export const getSurveys = (): Promise<SurveyMeta[]> =>
  fetch('/api/surveys').then((r) => r.json())

export const getRuns = (surveyId: string): Promise<RunMeta[]> =>
  fetch(`/api/surveys/${surveyId}/runs`).then((r) => r.json())

export const getRunDetail = (surveyId: string, runId: string): Promise<RunDetail> =>
  fetch(`/api/surveys/${surveyId}/runs/${runId}`).then((r) => r.json())
