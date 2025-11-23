package services

import (
	"context"
	"testing"
	"time"
)

// TestSavingAdvisorServices testcore serviceinitialize
func TestSavingAdvisorServices(t *testing.T) {
	// use默认configurecreateservice
	services := NewSavingAdvisorServices()

	if services == nil {
		t.Fatal("Failed to create SavingAdvisorServices")
	}

	// check子servicewhether正确initialize
	if services.GetAssetService() == nil {
		t.Error("AssetService not initialized")
	}

	if services.GetAnalysisService() == nil {
		t.Error("AnalysisService not initialized")
	}

	if services.GetRecommendationService() == nil {
		t.Error("RecommendationService not initialized")
	}

	// 清理资源
	if err := services.Close(); err != nil {
		t.Errorf("Failed to close services: %v", err)
	}
}

// TestAssetService testasset service
func TestAssetService(t *testing.T) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	assetService := services.GetAssetService()
	ctx := context.Background()

	// testgetuserportfolio（usemock data）
	portfolio, err := assetService.GetUserPortfolio(ctx, "1001")
	if err != nil {
		t.Fatalf("Failed to get user portfolio: %v", err)
	}

	if portfolio == nil {
		t.Fatal("Portfolio is nil")
	}

	if portfolio.UserID != "1001" {
		t.Errorf("Expected UserID 1001, got %s", portfolio.UserID)
	}

	if len(portfolio.Assets) == 0 {
		t.Error("Portfolio should have assets")
	}

	if portfolio.TotalAssets <= 0 {
		t.Error("Portfolio total value should be positive")
	}

	t.Logf("✅ Portfolio retrieved: UserID=%s, Assets=%d, TotalAssets=¥%.0f",
		portfolio.UserID, len(portfolio.Assets), portfolio.TotalAssets)
}

// TestAnalysisService testanalysis service
func TestAnalysisService(t *testing.T) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	analysisService := services.GetAnalysisService()
	ctx := context.Background()

	// testgenerateanalysis报告
	analysis, err := analysisService.GenerateAnalysis(ctx, "1001")
	if err != nil {
		t.Fatalf("Failed to generate analysis: %v", err)
	}

	if analysis == nil {
		t.Fatal("Analysis is nil")
	}

	if analysis.UserID != "1001" {
		t.Errorf("Expected UserID 1001, got %s", analysis.UserID)
	}

	if analysis.Summary == "" {
		t.Error("Analysis summary should not be empty")
	}

	if !analysis.Success {
		t.Error("Analysis should be successful")
	}

	if analysis.Timestamp.IsZero() {
		t.Error("Analysis timestamp should be set")
	}

	t.Logf("✅ Analysis generated: UserID=%s, Summary length=%d",
		analysis.UserID, len(analysis.Summary))
}

// TestRecommendationService testrecommendation service
func TestRecommendationService(t *testing.T) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	recommendationService := services.GetRecommendationService()
	ctx := context.Background()

	// testgeneraterecommendation
	recommendations, err := recommendationService.GenerateRecommendations(ctx, "1001", true)
	if err != nil {
		t.Fatalf("Failed to generate recommendations: %v", err)
	}

	if recommendations == nil {
		t.Fatal("Recommendations is nil")
	}

	if recommendations.UserID != "1001" {
		t.Errorf("Expected UserID 1001, got %s", recommendations.UserID)
	}

	if len(recommendations.Analyses) == 0 {
		t.Error("Should have at least one analysis")
	}

	if recommendations.OverallAssessment == "" {
		t.Error("Overall assessment should not be empty")
	}

	if recommendations.Timestamp == "" {
		t.Error("Timestamp should not be empty")
	}

	// validatetimestamp格式
	if _, err := time.Parse(time.RFC3339, recommendations.Timestamp); err != nil {
		t.Errorf("Invalid timestamp format: %v", err)
	}

	// statisticsrecommendationcount
	totalRecommendations := 0
	for _, analysis := range recommendations.Analyses {
		totalRecommendations += len(analysis.Recommendations)
	}

	t.Logf("✅ Recommendations generated: UserID=%s, Agents=%d, Total recommendations=%d",
		recommendations.UserID, len(recommendations.Analyses), totalRecommendations)
}

// TestVisualizationData test可视化data
func TestVisualizationData(t *testing.T) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	assetService := services.GetAssetService()
	ctx := context.Background()

	// testgenerate可视化data
	vizData, err := assetService.GetVisualizationData(ctx, "1001", "pie")
	if err != nil {
		t.Fatalf("Failed to get visualization data: %v", err)
	}

	if vizData == nil {
		t.Fatal("Visualization data is nil")
	}

	if vizData.ChartType != "pie" {
		t.Errorf("Expected chart type 'pie', got %s", vizData.ChartType)
	}

	if len(vizData.AssetBreakdown) == 0 {
		t.Error("Asset breakdown should not be empty")
	}

	if vizData.TotalValue <= 0 {
		t.Error("Total value should be positive")
	}

	if vizData.Timestamp == "" {
		t.Error("Timestamp should not be empty")
	}

	t.Logf("✅ Visualization data generated: ChartType=%s, Assets=%d, TotalValue=¥%.0f",
		vizData.ChartType, len(vizData.AssetBreakdown), vizData.TotalValue)
}

// TestHealthCheck testhealth check
func TestHealthCheck(t *testing.T) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	ctx := context.Background()

	// testhealth check（在没有real data库connected 情况下）
	err := services.HealthCheck(ctx)
	// health check可能会fail，因为我们没有configure真实 databaseconnected
	// 但serviceshould能够handle这种情况而不会panic

	if err != nil {
		t.Logf("⚠️  Health check failed (expected in test environment): %v", err)
	} else {
		t.Log("✅ Health check passed")
	}
}

// BenchmarkRecommendationGeneration recommendationgenerateperformance基准test
func BenchmarkRecommendationGeneration(b *testing.B) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	recommendationService := services.GetRecommendationService()
	ctx := context.Background()

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		_, err := recommendationService.GenerateRecommendations(ctx, "1001", true)
		if err != nil {
			b.Fatalf("Failed to generate recommendations: %v", err)
		}
	}
}

// BenchmarkAnalysisGeneration analysisgenerateperformance基准test
func BenchmarkAnalysisGeneration(b *testing.B) {
	services := NewSavingAdvisorServices()
	defer services.Close()

	analysisService := services.GetAnalysisService()
	ctx := context.Background()

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		_, err := analysisService.GenerateAnalysis(ctx, "1001")
		if err != nil {
			b.Fatalf("Failed to generate analysis: %v", err)
		}
	}
}
