package database

import (
	"fmt"
	"log"

	"gorm.io/driver/postgres"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"saving_advisor_system_go/internal/config"
	"saving_advisor_system_go/internal/models"
)

// DB is the global database instance
var DB *gorm.DB

// InitDatabase initializes the database connection
func InitDatabase(cfg *config.Config) error {
	var err error
	var dialector gorm.Dialector

	// Choose database driver
	if cfg.DBDriver == "postgres" {
		log.Println("Connecting to PostgreSQL...")
		dialector = postgres.Open(cfg.DatabaseDSN())
	} else {
		log.Println("Using SQLite database...")
		dialector = sqlite.Open(cfg.DatabaseDSN())
	}

	// Set logger level
	logLevel := logger.Info
	if !cfg.Debug {
		logLevel = logger.Warn
	}

	// Open database connection
	DB, err = gorm.Open(dialector, &gorm.Config{
		Logger: logger.Default.LogMode(logLevel),
	})
	if err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}

	// Auto-migrate models
	log.Println("Running database migrations...")
	err = DB.AutoMigrate(
		&models.User{},
		&models.UserPortfolio{},
		&models.DailyUserBalance{},
		&models.Transaction{},
		&models.AISession{},
		&models.Recommendation{},
		&models.UserFeedback{},
		&models.AnalyticsCache{},
	)
	if err != nil {
		return fmt.Errorf("failed to run migrations: %w", err)
	}

	log.Println("Database initialized successfully")
	return nil
}

// CloseDatabase closes the database connection
func CloseDatabase() error {
	if DB == nil {
		return nil
	}

	sqlDB, err := DB.DB()
	if err != nil {
		return err
	}

	return sqlDB.Close()
}

