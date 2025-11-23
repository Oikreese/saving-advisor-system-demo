package repository

import (
	"time"

	"gorm.io/gorm"

	"saving_advisor_system_go/internal/models"
)

// AnalyticsRepository handles analytics data operations
type AnalyticsRepository struct {
	db *gorm.DB
}

// NewAnalyticsRepository creates a new analytics repository
func NewAnalyticsRepository(db *gorm.DB) *AnalyticsRepository {
	return &AnalyticsRepository{db: db}
}

// UserBehaviorAnalysis represents user behavior analytics
type UserBehaviorAnalysis struct {
	TotalTransactions      int64   `json:"total_transactions"`
	AvgTransactionValue    float64 `json:"avg_transaction_value"`
	TotalTransactionValue  float64 `json:"total_transaction_value"`
	BuyerTransactions      int64   `json:"buyer_transactions"`
	SellerTransactions     int64   `json:"seller_transactions"`
	AISessionCount         int64   `json:"ai_session_count"`
	FeedbackCount          int64   `json:"feedback_count"`
	AvgBalance             float64 `json:"avg_balance"`
	MaxBalance             float64 `json:"max_balance"`
	MinBalance             float64 `json:"min_balance"`
}

// GetUserBehaviorAnalysis retrieves user behavior analytics
func (r *AnalyticsRepository) GetUserBehaviorAnalysis(userID string) (*UserBehaviorAnalysis, error) {
	analysis := &UserBehaviorAnalysis{}

	// Transaction statistics
	var transactionStats struct {
		TotalTransactions     int64
		AvgTransactionValue   float64
		TotalTransactionValue float64
		BuyerTransactions     int64
		SellerTransactions    int64
	}

	err := r.db.Model(&models.Transaction{}).
		Select(`
			COUNT(*) as total_transactions,
			COALESCE(AVG(price), 0) as avg_transaction_value,
			COALESCE(SUM(price), 0) as total_transaction_value,
			SUM(CASE WHEN buyer_id = ? THEN 1 ELSE 0 END) as buyer_transactions,
			SUM(CASE WHEN seller_id = ? THEN 1 ELSE 0 END) as seller_transactions
		`, userID, userID).
		Where("buyer_id = ? OR seller_id = ?", userID, userID).
		Scan(&transactionStats).Error

	if err != nil {
		return nil, err
	}

	analysis.TotalTransactions = transactionStats.TotalTransactions
	analysis.AvgTransactionValue = transactionStats.AvgTransactionValue
	analysis.TotalTransactionValue = transactionStats.TotalTransactionValue
	analysis.BuyerTransactions = transactionStats.BuyerTransactions
	analysis.SellerTransactions = transactionStats.SellerTransactions

	// AI Session statistics
	thirtyDaysAgo := time.Now().AddDate(0, 0, -30)

	err = r.db.Model(&models.AISession{}).
		Where("user_id = ? AND created_at >= ?", userID, thirtyDaysAgo).
		Count(&analysis.AISessionCount).Error
	if err != nil {
		return nil, err
	}

	err = r.db.Model(&models.AISession{}).
		Where("user_id = ? AND created_at >= ? AND user_feedback IS NOT NULL", userID, thirtyDaysAgo).
		Count(&analysis.FeedbackCount).Error
	if err != nil {
		return nil, err
	}

	// Balance statistics
	var balanceStats struct {
		AvgBalance float64
		MaxBalance float64
		MinBalance float64
	}

	err = r.db.Model(&models.DailyUserBalance{}).
		Select(`
			COALESCE(AVG(total_balance), 0) as avg_balance,
			COALESCE(MAX(total_balance), 0) as max_balance,
			COALESCE(MIN(total_balance), 0) as min_balance
		`).
		Where("user_id = ? AND date >= ?", userID, thirtyDaysAgo).
		Scan(&balanceStats).Error

	if err == nil {
		analysis.AvgBalance = balanceStats.AvgBalance
		analysis.MaxBalance = balanceStats.MaxBalance
		analysis.MinBalance = balanceStats.MinBalance
	}

	return analysis, nil
}

// MarketTrend represents market trend data
type MarketTrend struct {
	Date             string  `json:"date"`
	TransactionCount int64   `json:"transaction_count"`
	AvgPrice         float64 `json:"avg_price"`
	TotalValue       float64 `json:"total_value"`
}

// GetMarketTrends retrieves market trend analytics
func (r *AnalyticsRepository) GetMarketTrends(days int) ([]MarketTrend, error) {
	startDate := time.Now().AddDate(0, 0, -days)

	var trends []MarketTrend
	err := r.db.Model(&models.Transaction{}).
		Select(`
			DATE(created) as date,
			COUNT(*) as transaction_count,
			COALESCE(AVG(price), 0) as avg_price,
			COALESCE(SUM(price), 0) as total_value
		`).
		Where("created >= ?", startDate).
		Group("DATE(created)").
		Order("DATE(created)").
		Scan(&trends).Error

	return trends, err
}

// RecommendationPerformance represents recommendation system performance
type RecommendationPerformance struct {
	TotalRecommendations int     `json:"total_recommendations"`
	Accepted             int     `json:"accepted"`
	Rejected             int     `json:"rejected"`
	Pending              int     `json:"pending"`
	AcceptanceRate       float64 `json:"acceptance_rate"`
	AnalysisPeriod       string  `json:"analysis_period"`
}

// GetRecommendationPerformance retrieves recommendation system performance
func (r *AnalyticsRepository) GetRecommendationPerformance() (*RecommendationPerformance, error) {
	thirtyDaysAgo := time.Now().AddDate(0, 0, -30)

	perf := &RecommendationPerformance{
		AnalysisPeriod: "30 days",
	}

	var stats struct {
		Total    int64
		Accepted int64
		Rejected int64
		Pending  int64
	}

	err := r.db.Model(&models.Recommendation{}).
		Select(`
			COUNT(*) as total,
			SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted,
			SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
			SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
		`).
		Where("created_at >= ?", thirtyDaysAgo).
		Scan(&stats).Error

	if err != nil {
		return nil, err
	}

	perf.TotalRecommendations = int(stats.Total)
	perf.Accepted = int(stats.Accepted)
	perf.Rejected = int(stats.Rejected)
	perf.Pending = int(stats.Pending)

	if stats.Total > 0 {
		perf.AcceptanceRate = float64(stats.Accepted) / float64(stats.Total) * 100
	}

	return perf, nil
}

// UserEngagementMetrics represents user engagement metrics
type UserEngagementMetrics struct {
	TotalUsers            int     `json:"total_users"`
	WeeklyActiveUsers     int     `json:"weekly_active_users"`
	MonthlyActiveUsers    int     `json:"monthly_active_users"`
	WeeklyEngagementRate  float64 `json:"weekly_engagement_rate"`
	MonthlyEngagementRate float64 `json:"monthly_engagement_rate"`
}

// GetUserEngagementMetrics retrieves user engagement metrics
func (r *AnalyticsRepository) GetUserEngagementMetrics() (*UserEngagementMetrics, error) {
	metrics := &UserEngagementMetrics{}

	// Total users
	var totalUsers int64
	err := r.db.Model(&models.User{}).Count(&totalUsers).Error
	if err != nil {
		return nil, err
	}
	metrics.TotalUsers = int(totalUsers)

	// Weekly active users
	weekAgo := time.Now().AddDate(0, 0, -7)
	var weeklyActive int64
	err = r.db.Model(&models.AISession{}).
		Where("created_at >= ?", weekAgo).
		Distinct("user_id").
		Count(&weeklyActive).Error
	if err != nil {
		return nil, err
	}
	metrics.WeeklyActiveUsers = int(weeklyActive)

	// Monthly active users
	monthAgo := time.Now().AddDate(0, -1, 0)
	var monthlyActive int64
	err = r.db.Model(&models.AISession{}).
		Where("created_at >= ?", monthAgo).
		Distinct("user_id").
		Count(&monthlyActive).Error
	if err != nil {
		return nil, err
	}
	metrics.MonthlyActiveUsers = int(monthlyActive)

	// Calculate engagement rates
	if totalUsers > 0 {
		metrics.WeeklyEngagementRate = float64(weeklyActive) / float64(totalUsers) * 100
		metrics.MonthlyEngagementRate = float64(monthlyActive) / float64(totalUsers) * 100
	}

	return metrics, nil
}

