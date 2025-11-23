package models

import (
	"time"
)

// Recommendation 单个recommendationinfo
type Recommendation struct {
	RecommendationID string  `json:"recommendation_id"`
	Title            string  `json:"title"`
	Description      string  `json:"description"`
	AssetType        string  `json:"asset_type"`
	PotentialGain    float64 `json:"potential_gain"`
	AgentName        string  `json:"agent_name"`
	Priority         int32   `json:"priority"`
}

// AgentAnalysis 智能体analysis result
type AgentAnalysis struct {
	AgentName       string           `json:"agent_name"`
	AssetType       string           `json:"asset_type"`
	Findings        string           `json:"findings"`
	Recommendations []Recommendation `json:"recommendations"`
}

// MultiAgentRecommendations 多智能体recommendationresult
type MultiAgentRecommendations struct {
	UserID            string          `json:"user_id"`
	Analyses          []AgentAnalysis `json:"analyses"`
	OverallAssessment string          `json:"overall_assessment"`
	Timestamp         string          `json:"timestamp"`
}

// Analysis analysis result
type Analysis struct {
	UserID    string    `json:"user_id"`
	Summary   string    `json:"analysis_summary"`
	Timestamp time.Time `json:"timestamp"`
	Success   bool      `json:"success"`
}

// ComprehensiveAnalysis 综合analysis result
type ComprehensiveAnalysis struct {
	UserID               string  `json:"user_id"`
	ComprehensiveSummary string  `json:"comprehensive_summary"`
	InitialAssets        float64 `json:"initial_assets"`
	PredictedAssets      float64 `json:"predicted_assets"`
	Timestamp            string  `json:"timestamp"`
	Success              bool    `json:"success"`
}

// Task taskinfo
type Task struct {
	TaskID           string  `json:"task_id"`
	Title            string  `json:"title"`
	Description      string  `json:"description"`
	DueDate          string  `json:"due_date"`
	CompletionReward float64 `json:"completion_reward"`
	Status           string  `json:"status"`
}

// TasksResponse taskresponse
type TasksResponse struct {
	Tasks []Task `json:"tasks"`
}

// FeedbackRequest feedbackrequest
type FeedbackRequest struct {
	UserID           string `json:"user_id"`
	RecommendationID string `json:"recommendation_id"`
	Status           string `json:"status"` // "accepted", "rejected"
	RejectionReason  string `json:"rejection_reason,omitempty"`
	RejectionDetail  string `json:"rejection_detail,omitempty"`
	AgentName        string `json:"agent_name,omitempty"`
}
