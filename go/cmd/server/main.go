package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"saving_advisor_system_go/internal/config"
	"saving_advisor_system_go/internal/database"
	"saving_advisor_system_go/internal/repository"
	"saving_advisor_system_go/internal/services"
)

func main() {
	log.Println("🚀 Starting Saving Advisor System (Go)")

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize database
	err = database.InitDatabase(cfg)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer database.CloseDatabase()

	// Initialize repositories
	userRepo := repository.NewUserRepository(database.DB)
	analyticsRepo := repository.NewAnalyticsRepository(database.DB)

	// Initialize services
	openAIService := services.NewOpenAIService(cfg)

	// Setup Gin
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}
	router := gin.Default()

	// CORS middleware
	router.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	})

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "saving_advisor_system_go",
		})
	})

	// Version endpoint
	router.GET("/version", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"version":    "1.0.0",
			"language":   "Go",
			"go_version": "1.21",
		})
	})

	// API v1 group
	v1 := router.Group("/api/v1")
	{
		// User endpoints
		v1.GET("/users/:user_id", func(c *gin.Context) {
			userID := c.Param("user_id")
			user, err := userRepo.GetUser(userID)
			if err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
				return
			}
			c.JSON(http.StatusOK, user)
		})

		v1.GET("/users/:user_id/portfolio", func(c *gin.Context) {
			userID := c.Param("user_id")
			portfolio, err := userRepo.GetUserPortfolio(userID)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, portfolio)
		})

		v1.GET("/users/:user_id/statistics", func(c *gin.Context) {
			userID := c.Param("user_id")
			stats, err := userRepo.GetUserAssetStatistics(userID)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, stats)
		})

		// Analytics endpoints
		v1.GET("/analytics/user/:user_id/behavior", func(c *gin.Context) {
			userID := c.Param("user_id")
			analysis, err := analyticsRepo.GetUserBehaviorAnalysis(userID)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, analysis)
		})

		v1.GET("/analytics/market-trends", func(c *gin.Context) {
			trends, err := analyticsRepo.GetMarketTrends(30)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, trends)
		})

		v1.GET("/analytics/recommendations/performance", func(c *gin.Context) {
			perf, err := analyticsRepo.GetRecommendationPerformance()
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, perf)
		})

		v1.GET("/analytics/engagement", func(c *gin.Context) {
			metrics, err := analyticsRepo.GetUserEngagementMetrics()
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, metrics)
		})

		// Test OpenAI endpoint
		v1.POST("/test/openai", func(c *gin.Context) {
			var req struct {
				Prompt string `json:"prompt"`
			}
			if err := c.ShouldBindJSON(&req); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}

			resp, err := openAIService.CreateChatCompletion(context.Background(), &services.ChatCompletionRequest{
				SystemPrompt: "You are a helpful financial advisor assistant.",
				UserPrompt:   req.Prompt,
			})
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}

			c.JSON(http.StatusOK, resp)
		})
	}

	// Setup HTTP server
	srv := &http.Server{
		Addr:    ":" + cfg.ServerPort,
		Handler: router,
	}

	// Graceful shutdown
	go func() {
		log.Printf("✅ Server started on :%s", cfg.ServerPort)
		log.Printf("📚 API Documentation: http://localhost:%s/api/v1", cfg.ServerPort)
		log.Printf("❤️  Health check: http://localhost:%s/health", cfg.ServerPort)

		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("🛑 Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("👋 Server exited successfully")
}
