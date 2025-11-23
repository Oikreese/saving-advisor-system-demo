package models

import (
	"time"

	"gorm.io/gorm"
)

// User represents a user in the system
type User struct {
	UserID    string         `gorm:"primaryKey;size:50" json:"user_id"`
	Nickname  string         `gorm:"size:100" json:"nickname"`
	Email     string         `gorm:"uniqueIndex;size:255" json:"email"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	IsActive  bool           `gorm:"default:true" json:"is_active"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	Portfolios []UserPortfolio `gorm:"foreignKey:UserID" json:"portfolios,omitempty"`
	Sessions   []AISession     `gorm:"foreignKey:UserID" json:"sessions,omitempty"`
}

// UserPortfolio represents a user's asset portfolio
type UserPortfolio struct {
	ID               uint           `gorm:"primaryKey" json:"id"`
	UserID           string         `gorm:"size:50;index:idx_portfolio_user_asset" json:"user_id"`
	AssetType        string         `gorm:"size:50;index:idx_portfolio_user_asset" json:"asset_type"`
	CurrentValue     float64        `gorm:"default:0" json:"current_value"`
	TargetAllocation float64        `gorm:"default:0" json:"target_allocation"`
	LastUpdated      time.Time      `json:"last_updated"`
	Metadata         string         `gorm:"type:jsonb" json:"metadata"` // JSON field
	DeletedAt        gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	User User `gorm:"foreignKey:UserID" json:"user,omitempty"`
}

// DailyUserBalance represents daily balance snapshots
type DailyUserBalance struct {
	ID                 uint      `gorm:"primaryKey" json:"id"`
	UserID             string    `gorm:"size:50;index:idx_balance_user_date" json:"user_id"`
	Date               time.Time `gorm:"index:idx_balance_user_date" json:"date"`
	FreepointAmount    float64   `gorm:"default:0" json:"freepoint_amount"`
	PrepaidpointAmount float64   `gorm:"default:0" json:"prepaidpoint_amount"`
	SalesAmount        float64   `gorm:"default:0" json:"sales_amount"`
	FundsAmount        float64   `gorm:"default:0" json:"funds_amount"`
	TotalBalance       float64   `gorm:"default:0" json:"total_balance"`
	CreatedAt          time.Time `json:"created_at"`
}

// Transaction represents a transaction record
type Transaction struct {
	TransactionID string         `gorm:"primaryKey;size:100" json:"transaction_id"`
	UserID        string         `gorm:"size:50;index" json:"user_id"`
	BuyerID       string         `gorm:"size:50;index" json:"buyer_id"`
	SellerID      string         `gorm:"size:50;index" json:"seller_id"`
	ItemID        string         `gorm:"size:100" json:"item_id"`
	CategoryID    int            `json:"category_id"`
	Price         float64        `json:"price"`
	Status        string         `gorm:"size:20;index" json:"status"`
	PaidMethod    string         `gorm:"size:50" json:"paid_method"`
	ConsumePoint  float64        `gorm:"default:0" json:"consume_point"`
	ConsumeSales  float64        `gorm:"default:0" json:"consume_sales"`
	Created       time.Time      `gorm:"index" json:"created"`
	Updated       time.Time      `json:"updated"`
	Metadata      string         `gorm:"type:jsonb" json:"metadata"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`
}

// AISession represents an AI analysis session
type AISession struct {
	SessionID      string         `gorm:"primaryKey;size:100" json:"session_id"`
	UserID         string         `gorm:"size:50;index:idx_session_user" json:"user_id"`
	SessionType    string         `gorm:"size:100;index" json:"session_type"`
	InputData      string         `gorm:"type:jsonb" json:"input_data"`
	AIResponse     string         `gorm:"type:jsonb" json:"ai_response"`
	UserFeedback   string         `gorm:"type:jsonb" json:"user_feedback"`
	ProcessingTime int            `json:"processing_time_ms"`
	CreatedAt      time.Time      `gorm:"index" json:"created_at"`
	UpdatedAt      time.Time      `json:"updated_at"`
	DeletedAt      gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	User User `gorm:"foreignKey:UserID" json:"user,omitempty"`
}

// Recommendation represents a recommendation made to a user
type Recommendation struct {
	RecommendationID string         `gorm:"primaryKey;size:100" json:"recommendation_id"`
	UserID           string         `gorm:"size:50;index" json:"user_id"`
	SessionID        string         `gorm:"size:100;index" json:"session_id"`
	AgentName        string         `gorm:"size:100" json:"agent_name"`
	Title            string         `gorm:"size:255" json:"title"`
	Description      string         `gorm:"type:text" json:"description"`
	AssetType        string         `gorm:"size:50" json:"asset_type"`
	PotentialGain    float64        `gorm:"default:0" json:"potential_gain"`
	Priority         int            `gorm:"default:0" json:"priority"`
	Status           string         `gorm:"size:20;index" json:"status"`
	Feedback         string         `gorm:"type:jsonb" json:"feedback"`
	CreatedAt        time.Time      `gorm:"index" json:"created_at"`
	DeletedAt        gorm.DeletedAt `gorm:"index" json:"-"`
}

// UserFeedback represents user feedback on recommendations
type UserFeedback struct {
	FeedbackID       string         `gorm:"primaryKey;size:100" json:"feedback_id"`
	UserID           string         `gorm:"size:50;index" json:"user_id"`
	RecommendationID string         `gorm:"size:100;index" json:"recommendation_id"`
	Status           string         `gorm:"size:20" json:"status"`
	RejectionReason  string         `gorm:"size:100" json:"rejection_reason"`
	RejectionDetail  string         `gorm:"type:text" json:"rejection_detail"`
	CreatedAt        time.Time      `gorm:"index" json:"created_at"`
	DeletedAt        gorm.DeletedAt `gorm:"index" json:"-"`
}

// AnalyticsCache represents cached analytics results
type AnalyticsCache struct {
	CacheID   string         `gorm:"primaryKey;size:100" json:"cache_id"`
	CacheKey  string         `gorm:"uniqueIndex;size:255" json:"cache_key"`
	CacheType string         `gorm:"size:50;index" json:"cache_type"`
	Data      string         `gorm:"type:jsonb" json:"data"`
	CreatedAt time.Time      `json:"created_at"`
	ExpiresAt *time.Time     `gorm:"index" json:"expires_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
}

// TableName overrides for GORM
func (User) TableName() string              { return "users" }
func (UserPortfolio) TableName() string     { return "user_portfolios" }
func (DailyUserBalance) TableName() string  { return "daily_user_balance" }
func (Transaction) TableName() string       { return "transactions" }
func (AISession) TableName() string         { return "ai_sessions" }
func (Recommendation) TableName() string    { return "recommendations" }
func (UserFeedback) TableName() string      { return "user_feedback" }
func (AnalyticsCache) TableName() string    { return "analytics_cache" }

