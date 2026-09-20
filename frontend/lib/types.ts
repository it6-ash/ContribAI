/** Issue difficulty stays three-valued; it describes the work, not a person. */
export type Difficulty = "beginner" | "intermediate" | "advanced";

/** Skill proficiency, five bands. Three collapsed everything from one hobby
 *  repo to years of merged work into "intermediate". */
export type Level =
  | "novice"
  | "beginner"
  | "intermediate"
  | "advanced"
  | "expert";

export type QualityTier =
  | "bare"
  | "sparse"
  | "workable"
  | "welcoming"
  | "exemplary";

export interface Skill {
  name: string;
  category: string;
  confidence: number;
  level: Level;
  evidence: string[];
  source: string;
  last_used_at: string | null;
}

export interface User {
  id: number;
  username: string;
  avatar_url: string | null;
  bio: string | null;
  is_demo: boolean;
  experience_level: string;
  mode: string;
  interests: string[];
  profile_analyzed_at: string | null;
}

export interface Profile {
  user: User;
  skills: Skill[];
  skills_by_category: Record<string, Skill[]>;
  /** Names the server could not store, so the UI can say so rather than
   *  appearing to have accepted them. */
  rejected_skills?: string[];
}

export interface RepoHealth {
  activity: "high" | "medium" | "low" | "unknown";
  days_since_commit: number | null;
  has_contributing: boolean;
  has_code_of_conduct: boolean;
  has_tests: boolean;
  has_license: boolean;
  contributors: number;
  median_pr_response_hours: number | null;
  open_issues: number;
  score: number;
  /** How well the project supports an incoming contributor. Not code quality. */
  tier: QualityTier;
  signals: string[];
}

export interface Repository {
  id: number;
  full_name: string;
  owner: string;
  name: string;
  description: string | null;
  language: string | null;
  topics: string[];
  stars: number;
  forks: number;
  open_issues: number;
  contributors: number;
  url: string;
  health: RepoHealth;
  readme?: string | null;
  setup_commands?: string[];
  tree?: string[];
}

export interface IssueAnalysis {
  summary: string;
  problem_description: string;
  why_it_matters: string;
  difficulty: Difficulty;
  difficulty_basis: string;
  estimated_hours_min: number;
  estimated_hours_max: number;
  required_skills: string[];
  concepts: string[];
  affected_files: string[];
  investigation_order: string[];
  open_questions: string[];
  clarity: number;
  learning_value: number;
  risk: string;
  confidence: "low" | "medium" | "high";
  source: "heuristic" | "llm";
}

export interface Issue {
  id: number;
  number: number;
  title: string;
  body: string | null;
  labels: string[];
  comments: number;
  state: string;
  url: string;
  is_demo: boolean;
  created_at: string | null;
  updated_at: string | null;
  repository: Repository;
  analysis: IssueAnalysis | null;
}

export interface SkillGap {
  skill: string;
  category: string;
  severity: "core" | "supporting";
  learning_hours: number;
}

export interface MatchedSkill {
  skill: string;
  confidence: number;
}

export interface Recommendation {
  id: number | null;
  issue: Issue;
  fit_score: number;
  dimensions: Record<string, number>;
  matched_skills: MatchedSkill[];
  skill_gaps: SkillGap[];
  readiness: Record<string, number>;
  reasoning: string[];
  bucket: string;
  skill_gap_narrative: string;
}

export interface RecommendationsResponse {
  stats: {
    analyzed?: number;
    passed_filters?: number;
    strong_matches?: number;
    dropped?: Record<string, number>;
    discovery?: Record<string, unknown>;
  };
  recommendations: Recommendation[];
  generated_at: string;
}

export interface PlanStep {
  title: string;
  objective: string;
  command: string;
  expected: string;
  common_failure: string;
}

export interface Plan {
  issue_id: number;
  prerequisites: string[];
  steps: PlanStep[];
  source: "heuristic" | "llm";
}

export interface Health {
  status: string;
  llm_provider: string;
  llm_available: boolean;
  github_oauth_configured: boolean;
  issues_in_corpus: number;
  demo_profiles: string[];
}

export interface Taxonomy {
  skills: Record<string, string[]>;
  modes: Record<string, string>;
  experience_levels: string[];
  skill_levels: Level[];
  repo_quality_tiers: QualityTier[];
  weights: Record<string, number>;
}
