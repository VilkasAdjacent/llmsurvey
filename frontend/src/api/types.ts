export interface SurveyMeta {
  id: string
  name: string
  source: string
  question_count: number
}

export interface RunMeta {
  run_id: string
  models: string[]
  participant_count: number
  has_summary: boolean
}

export interface QuestionResult {
  real: Record<string, number>
  models: Record<string, Record<string, number>>
}

export interface RunResults {
  questions: Record<string, QuestionResult>
}

export interface ModelStats {
  chi_square_p: number | null
  kl_divergence: number
  js_divergence: number
  bias_direction: string
  per_option_delta: Record<string, number>
  parse_failure_rate: number
}

export interface RunStats {
  questions: Record<string, Record<string, ModelStats>>
}

export interface RunDetail {
  results: RunResults
  stats: RunStats
  summary: string | null
}
