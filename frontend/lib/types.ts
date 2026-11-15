export interface Prediction {
  match_date: string;
  home_team: string;
  away_team: string;
  division: string;
  predicted_result: "H" | "D" | "A";
  confidence: "alta" | "media" | "baja";
  prob_home: number;
  prob_draw: number;
  prob_away: number;
  prob_over25: number;
  prob_btts: number;
  ft_result?: "H" | "D" | "A" | null;
  ft_home_goals?: number | null;
  ft_away_goals?: number | null;
  home_slug?: string;
  away_slug?: string;
  match_slug?: string;
  league_slug?: string;
  league_name?: string;
  league_flag?: string;
}

export interface TeamFeatures {
  goals_scored_avg: number;
  goals_conceded_avg: number;
  goals_scored_avg_3: number;
  goals_conceded_avg_3: number;
  xg_for_avg: number;
  xg_against_avg: number;
  win_rate: number;
  win_rate_3: number;
  btts_rate: number;
  over25_rate: number;
  venue_win_rate: number;
  venue_goals_avg: number;
  league_pos: number;
  h2h_win_rate: number;
  h2h_avg_goals: number;
  h2h_matches: number;
  xg_diff_avg: number;
}

export interface MatchDetail {
  prediction: Prediction;
  home_features: TeamFeatures | null;
  away_features: TeamFeatures | null;
  elo: { home: number; away: number } | null;
  h2h: Array<{
    date: string;
    home_goals: number;
    away_goals: number;
    result: string;
  }>;
  ventajas: { home: string[]; away: string[] };
  league_name?: string;
  league_flag?: string;
  league_slug?: string;
}

export interface AccuracyStats {
  total: number;
  accuracy: number;
  by_confidence: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
  by_division: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
}

export interface LeagueInfo {
  code: string;
  slug: string;
  name: string;
  flag: string;
}
