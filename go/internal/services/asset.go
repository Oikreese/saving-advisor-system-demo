package services

import (
	"context"
	"fmt"
	"log"
	"time"

	"saving_advisor_system_go/internal/models"
)

// AssetService asset管理service
// 对应Pythonversion asset_service.py，负责userassetandportfolio管理
type AssetService struct {
	core *SavingAdvisorServices
}

// NewAssetService createasset service实例
func NewAssetService(core *SavingAdvisorServices) *AssetService {
	return &AssetService{core: core}
}

// GetUserPortfolio getuserportfolio
// 对应Pythonversion get_user_portfoliomethod
func (s *AssetService) GetUserPortfolio(ctx context.Context, userID string) (*models.Portfolio, error) {
	log.Printf("🔍 Getting portfolio for user: %s", userID)

	// 强制要求Firestore客户端available
	if s.core.firestoreClient == nil {
		return nil, fmt.Errorf("firestore client is not available - please check your configuration and credentials")
	}

	// fromFirestoregetdata，fail时directlyreturnerror
	portfolio, err := s.core.firestoreClient.GetUserPortfolio(ctx, userID)
	if err != nil {
		log.Printf("❌ Failed to get portfolio from Firestore: %v", err)
		return nil, fmt.Errorf("failed to get portfolio from firestore: %w", err)
	}

	log.Printf("✅ Retrieved portfolio from Firestore for user: %s", userID)
	return portfolio, nil
}

// getMockPortfolio generatemockportfoliodata
// 对应Pythonversion mockdata generationlogic
func (s *AssetService) getMockPortfolio(userID string) *models.Portfolio {
	now := time.Now()

	// 根据userIDgenerate不同 mock data
	var assets []models.Asset
	var totalValue float64

	switch userID {
	case "1001":
		assets = []models.Asset{
			{
				AssetType:        "Points",
				CurrentValue:     25000,
				TargetAllocation: 30,
				LastUpdated:      now.Format(time.RFC3339),
			},
			{
				AssetType:        "Earnings",
				CurrentValue:     150000,
				TargetAllocation: 60,
				LastUpdated:      now.Format(time.RFC3339),
			},
			{
				AssetType:        "Items",
				CurrentValue:     8000,
				TargetAllocation: 5,
				LastUpdated:      now.Format(time.RFC3339),
			},
			{
				AssetType:        "Stablecoin",
				CurrentValue:     12000,
				TargetAllocation: 5,
				LastUpdated:      now.Format(time.RFC3339),
			},
		}
		totalValue = 195000
	case "1002":
		assets = []models.Asset{
			{
				AssetType:        "Points",
				CurrentValue:     18000,
				TargetAllocation: 25,
				LastUpdated:      now.Format(time.RFC3339),
			},
			{
				AssetType:        "Earnings",
				CurrentValue:     120000,
				TargetAllocation: 70,
				LastUpdated:      now.Format(time.RFC3339),
			},
			{
				AssetType:        "Items",
				CurrentValue:     5000,
				TargetAllocation: 5,
				LastUpdated:      now.Format(time.RFC3339),
			},
		}
		totalValue = 143000
	default:
		// 默认usercombine
		assets = []models.Asset{
			{
				AssetType:        "Points",
				CurrentValue:     15000,
				TargetAllocation: 30,
				LastUpdated:      now.Format(time.RFC3339),
			},
			{
				AssetType:        "Earnings",
				CurrentValue:     100000,
				TargetAllocation: 70,
				LastUpdated:      now.Format(time.RFC3339),
			},
		}
		totalValue = 115000
	}

	return &models.Portfolio{
		UserID:      userID,
		Assets:      assets,
		TotalAssets: totalValue,
		LastUpdated: now.Format(time.RFC3339),
	}
}

// UpdateUserAsset updateuserasset
func (s *AssetService) UpdateUserAsset(ctx context.Context, userID string, asset *models.Asset) error {
	log.Printf("📝 Updating asset for user %s: %s", userID, asset.AssetType)

	// ifFirestore客户端available，update到database
	if s.core.firestoreClient != nil {
		err := s.core.firestoreClient.UpdateUserAsset(ctx, userID, asset)
		if err != nil {
			return fmt.Errorf("failed to update asset in firestore: %w", err)
		}
		log.Printf("✅ Asset updated in Firestore for user: %s", userID)
		return nil
	}

	// if没有database客户端，只是recordlog
	log.Printf("📝 Mock: Asset updated for user %s, asset: %+v", userID, asset)
	return nil
}

// GetVisualizationData get可视化data
// 对应Pythonversion visualization相关feature
func (s *AssetService) GetVisualizationData(ctx context.Context, userID, chartType string) (*models.VisualizationData, error) {
	log.Printf("📊 Generating visualization data for user %s, chart type: %s", userID, chartType)

	// getuserportfolio
	portfolio, err := s.GetUserPortfolio(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get portfolio for visualization: %w", err)
	}

	// 构建assetdecomposedata
	assetBreakdown := make(map[string]float64)
	for _, asset := range portfolio.Assets {
		assetBreakdown[asset.AssetType] = asset.CurrentValue
	}

	visualizationData := &models.VisualizationData{
		ChartType:      chartType,
		AssetBreakdown: assetBreakdown,
		TotalValue:     portfolio.TotalAssets,
		Timestamp:      time.Now().Format(time.RFC3339),
	}

	log.Printf("✅ Generated visualization data: %d asset types", len(assetBreakdown))
	return visualizationData, nil
}

// CalculateAssetAllocation 计算assetconfigure
func (s *AssetService) CalculateAssetAllocation(portfolio *models.Portfolio) map[string]float64 {
	allocation := make(map[string]float64)

	if portfolio.TotalAssets == 0 {
		return allocation
	}

	for _, asset := range portfolio.Assets {
		percentage := (asset.CurrentValue / portfolio.TotalAssets) * 100
		allocation[asset.AssetType] = percentage
	}

	return allocation
}

// GetAssetPerformance getassettable现（mock data）
func (s *AssetService) GetAssetPerformance(ctx context.Context, userID, assetType string, days int) (map[string]interface{}, error) {
	log.Printf("📈 Getting asset performance for user %s, asset: %s, days: %d", userID, assetType, days)

	// ifBigQuery客户端available，fromdatarepositorygetreal data
	if s.core.bigQueryClient != nil {
		trends, err := s.core.bigQueryClient.QueryMarketTrends(ctx, assetType, days)
		if err != nil {
			log.Printf("⚠️  Failed to get market trends from BigQuery: %v", err)
			// fail时returnmock data
			return s.getMockAssetPerformance(assetType, days), nil
		}

		// convertBigQueryresult为适合 格式
		performance := map[string]interface{}{
			"asset_type": assetType,
			"period":     days,
			"data":       trends,
		}

		log.Printf("✅ Retrieved asset performance from BigQuery")
		return performance, nil
	}

	// returnmock data
	return s.getMockAssetPerformance(assetType, days), nil
}

// getMockAssetPerformance generatemockassettable现data
func (s *AssetService) getMockAssetPerformance(assetType string, days int) map[string]interface{} {
	// 根据assettypegenerate不同 mocktable现data
	var baseValue float64
	var volatility float64

	switch assetType {
	case "Points":
		baseValue = 1.0
		volatility = 0.02 // 2%波动
	case "Earnings":
		baseValue = 1.0
		volatility = 0.01 // 1%波动
	case "Items":
		baseValue = 1.0
		volatility = 0.05 // 5%波动
	case "Stablecoin":
		baseValue = 1.0
		volatility = 0.01 // 1%波动
	default:
		baseValue = 1.0
		volatility = 0.03 // 3%波动
	}

	// generatemock historydata
	performanceData := []map[string]interface{}{}
	currentValue := baseValue

	for i := days; i >= 0; i-- {
		// 简单 随机波动mock
		change := (float64(i%7) - 3) * volatility / 3
		currentValue += change

		date := time.Now().AddDate(0, 0, -i).Format("2006-01-02")
		performanceData = append(performanceData, map[string]interface{}{
			"date":       date,
			"value":      currentValue,
			"change":     change,
			"change_pct": change * 100,
		})
	}

	return map[string]interface{}{
		"asset_type":   assetType,
		"period":       days,
		"data":         performanceData,
		"current":      currentValue,
		"total_change": currentValue - baseValue,
	}
}

// ValidatePortfolio validateportfoliodata
func (s *AssetService) ValidatePortfolio(portfolio *models.Portfolio) []string {
	var errors []string

	if portfolio.UserID == "" {
		errors = append(errors, "userID不能为空")
	}

	if len(portfolio.Assets) == 0 {
		errors = append(errors, "portfolio不能为空")
	}

	totalValue := float64(0)
	for _, asset := range portfolio.Assets {
		if asset.AssetType == "" {
			errors = append(errors, "assettype不能为空")
		}
		if asset.CurrentValue < 0 {
			errors = append(errors, fmt.Sprintf("asset %s  价value不能为负数", asset.AssetType))
		}
		totalValue += asset.CurrentValue
	}

	// checktotal价valuewhether一致（允许小 浮点数误差）
	if abs(totalValue-portfolio.TotalAssets) > 0.01 {
		errors = append(errors, "portfoliototal价valueandasset价value之and不一致")
	}

	return errors
}

// abs 计算绝对value
func abs(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}
