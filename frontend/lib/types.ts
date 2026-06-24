export interface AgentEvent {
  type: "token" | "tool" | "route" | "interrupt" | "resumed" | "error" | "done";
  content?: string;
  name?: string;
  route?: string;
  approved?: boolean;
  payload?: { action?: string; route?: string; message?: string };
}

export interface Analytics {
  user_id: string;
  xp: number;
  streak_days: number;
  topics_completed: number;
  quizzes_taken: number;
  average_quiz_score: number | null;
  weak_areas: string[];
  goals: string[];
}

export interface ResumeAnalysis {
  target_role: string;
  characters_extracted: number;
  analysis: {
    ats_score?: number;
    strengths?: string[];
    weaknesses?: string[];
    missing_keywords?: string[];
    bullet_rewrites?: { before: string; after: string }[];
    summary?: string;
    raw?: string;
  };
}
