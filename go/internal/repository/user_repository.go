package repository

import (
	"time"

	"gorm.io/gorm"

	"saving_advisor_system_go/internal/models"
)

// UserRepository handles user data operations
type UserRepository struct {
	db *gorm.DB
}

// NewUserRepository creates a new user repository
func NewUserRepository(db *gorm.DB) *UserRepository {
	return &UserRepository{db: db}
}

// GetUser retrieves a user by ID
func (r *UserRepository) GetUser(userID string) (*models.User, error) {
	var user models.User
	err := r.db.Where("user_id = ?", userID).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

// CreateUser creates a new user
func (r *UserRepository) CreateUser(user *models.User) error {
	user.CreatedAt = time.Now()
	user.UpdatedAt = time.Now()
	user.IsActive = true
	return r.db.Create(user).Error
}

// GetOrCreateUser gets a user or creates if not exists
func (r *UserRepository) GetOrCreateUser(userID, nickname, email string) (*models.User, error) {
	user, err := r.GetUser(userID)
	if err == nil {
		return user, nil
	}

	if err != gorm.ErrRecordNotFound {
		return nil, err
	}

	// Create new user
	newUser := &models.User{
		UserID:   userID,
		Nickname: nickname,
		Email:    email,
	}
	err = r.CreateUser(newUser)
	if err != nil {
		return nil, err
	}

	return newUser, nil
}

// GetUserPortfolio retrieves user's portfolio
func (r *UserRepository) GetUserPortfolio(userID string) ([]models.UserPortfolio, error) {
	var portfolios []models.UserPortfolio
	err := r.db.Where("user_id = ?", userID).Order("asset_type").Find(&portfolios).Error
	return portfolios, err
}

// UpdateUserAsset updates or creates a user asset
func (r *UserRepository) UpdateUserAsset(userID, assetType string, currentValue, targetAllocation float64) (*models.UserPortfolio, error) {
	var portfolio models.UserPortfolio

	// Try to find existing
	err := r.db.Where("user_id = ? AND asset_type = ?", userID, assetType).First(&portfolio).Error

	if err == gorm.ErrRecordNotFound {
		// Create new
		portfolio = models.UserPortfolio{
			UserID:           userID,
			AssetType:        assetType,
			CurrentValue:     currentValue,
			TargetAllocation: targetAllocation,
			LastUpdated:      time.Now(),
		}
		err = r.db.Create(&portfolio).Error
		return &portfolio, err
	}

	if err != nil {
		return nil, err
	}

	// Update existing
	portfolio.CurrentValue = currentValue
	if targetAllocation > 0 {
		portfolio.TargetAllocation = targetAllocation
	}
	portfolio.LastUpdated = time.Now()

	err = r.db.Save(&portfolio).Error
	return &portfolio, err
}

// GetDailyBalanceHistory retrieves user's daily balance history
func (r *UserRepository) GetDailyBalanceHistory(userID string, days int) ([]models.DailyUserBalance, error) {
	startDate := time.Now().AddDate(0, 0, -days)

	var balances []models.DailyUserBalance
	err := r.db.Where("user_id = ? AND date >= ?", userID, startDate).
		Order("date DESC").
		Find(&balances).Error

	return balances, err
}

// SaveDailyBalance saves or updates daily balance
func (r *UserRepository) SaveDailyBalance(balance *models.DailyUserBalance) error {
	// Check if balance for this date already exists
	var existing models.DailyUserBalance
	err := r.db.Where("user_id = ? AND DATE(date) = DATE(?)", balance.UserID, balance.Date).
		First(&existing).Error

	if err == gorm.ErrRecordNotFound {
		// Create new
		balance.CreatedAt = time.Now()
		return r.db.Create(balance).Error
	}

	if err != nil {
		return err
	}

	// Update existing
	existing.FreepointAmount = balance.FreepointAmount
	existing.PrepaidpointAmount = balance.PrepaidpointAmount
	existing.SalesAmount = balance.SalesAmount
	existing.FundsAmount = balance.FundsAmount
	existing.TotalBalance = balance.TotalBalance

	return r.db.Save(&existing).Error
}

// GetUserTransactions retrieves user's transactions
func (r *UserRepository) GetUserTransactions(userID string, limit int) ([]models.Transaction, error) {
	var transactions []models.Transaction
	err := r.db.Where("buyer_id = ? OR seller_id = ?", userID, userID).
		Order("created DESC").
		Limit(limit).
		Find(&transactions).Error

	return transactions, err
}

// SaveTransaction saves a transaction
func (r *UserRepository) SaveTransaction(transaction *models.Transaction) error {
	// Check if transaction exists
	var existing models.Transaction
	err := r.db.Where("transaction_id = ?", transaction.TransactionID).First(&existing).Error

	if err == gorm.ErrRecordNotFound {
		// Create new
		transaction.Created = time.Now()
		transaction.Updated = time.Now()
		return r.db.Create(transaction).Error
	}

	if err != nil {
		return err
	}

	// Update existing
	transaction.Updated = time.Now()
	return r.db.Save(transaction).Error
}

// GetUserAssetStatistics retrieves user's asset statistics
func (r *UserRepository) GetUserAssetStatistics(userID string) (map[string]interface{}, error) {
	// Get total value
	var totalValue float64
	err := r.db.Model(&models.UserPortfolio{}).
		Where("user_id = ?", userID).
		Select("COALESCE(SUM(current_value), 0)").
		Scan(&totalValue).Error
	if err != nil {
		return nil, err
	}

	// Get asset count
	var assetCount int64
	err = r.db.Model(&models.UserPortfolio{}).
		Where("user_id = ?", userID).
		Count(&assetCount).Error
	if err != nil {
		return nil, err
	}

	// Get balance from 30 days ago
	thirtyDaysAgo := time.Now().AddDate(0, 0, -30)
	var balance30DaysAgo float64
	err = r.db.Model(&models.DailyUserBalance{}).
		Where("user_id = ? AND date >= ?", userID, thirtyDaysAgo).
		Order("date ASC").
		Limit(1).
		Select("total_balance").
		Scan(&balance30DaysAgo).Error

	// Calculate growth
	growth := totalValue - balance30DaysAgo
	growthRate := float64(0)
	if balance30DaysAgo > 0 {
		growthRate = (growth / balance30DaysAgo) * 100
	}

	return map[string]interface{}{
		"total_value":        totalValue,
		"asset_count":        assetCount,
		"30_day_growth":      growth,
		"30_day_growth_rate": growthRate,
	}, nil
}

