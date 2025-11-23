package config

import (
	"fmt"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config holds all configuration for the application
type Config struct {
	// Server
	ServerPort string
	Environment string
	Debug bool

	// Database
	DBHost     string
	DBPort     string
	DBUser     string
	DBPassword string
	DBName     string
	DBDriver   string // "postgres" or "sqlite"

	// Redis
	RedisURL string

	// OpenAI
	OpenAIAPIKey string
	OpenAIModel  string

	// Security
	SecretKey string
}

// Load loads configuration from environment variables
func Load() (*Config, error) {
	// Load .env file if it exists
	_ = godotenv.Load()

	cfg := &Config{
		// Server
		ServerPort:  getEnv("SERVER_PORT", "8080"),
		Environment: getEnv("ENVIRONMENT", "development"),
		Debug:       getEnvBool("DEBUG", true),

		// Database
		DBHost:     getEnv("DB_HOST", "localhost"),
		DBPort:     getEnv("DB_PORT", "5432"),
		DBUser:     getEnv("DB_USER", "postgres"),
		DBPassword: getEnv("DB_PASSWORD", "postgres"),
		DBName:     getEnv("DB_NAME", "saving_advisor"),
		DBDriver:   getEnv("DB_DRIVER", "sqlite"), // default to sqlite for development

		// Redis
		RedisURL: getEnv("REDIS_URL", "redis://localhost:6379"),

		// OpenAI
		OpenAIAPIKey: getEnv("OPENAI_API_KEY", ""),
		OpenAIModel:  getEnv("OPENAI_MODEL", "gpt-4"),

		// Security
		SecretKey: getEnv("SECRET_KEY", "change-this-in-production"),
	}

	return cfg, nil
}

// DatabaseDSN returns the database connection string
func (c *Config) DatabaseDSN() string {
	if c.DBDriver == "sqlite" {
		return "./saving_advisor.db"
	}
	// PostgreSQL DSN
	return fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName,
	)
}

// getEnv gets an environment variable or returns a default value
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

// getEnvBool gets an environment variable as bool or returns a default value
func getEnvBool(key string, defaultValue bool) bool {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	boolValue, err := strconv.ParseBool(value)
	if err != nil {
		return defaultValue
	}
	return boolValue
}

