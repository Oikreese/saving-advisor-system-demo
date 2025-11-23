package services

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"saving_advisor_system_go/internal/models"
)

// AnalysisService analysis service
// 对应Pythonversion analysis_service.py，负责userassetanalysisand报告generate
type AnalysisService struct {
	core *SavingAdvisorServices
}

// NewAnalysisService createanalysis service实例
func NewAnalysisService(core *SavingAdvisorServices) *AnalysisService {
	return &AnalysisService{core: core}
}

// GenerateAnalysis generateanalysis报告
// 对应Pythonversion generate_analysismethod
func (s *AnalysisService) GenerateAnalysis(ctx context.Context, userID string) (*models.Analysis, error) {
	log.Printf("🔬 Generating analysis for user: %s", userID)

	// 1. getuserportfolio
	portfolio, err := s.core.assetService.GetUserPortfolio(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get portfolio for analysis: %w", err)
	}

	// 2. 构建analysistip词
	analysisPrompt := s.buildAnalysisPrompt(portfolio)

	// 3. callAIservicegenerateanalysis（ifOpenAI客户端available）
	var analysisResult string
	if s.core.openAIClient != nil {
		analysisResult, err = s.core.openAIClient.GenerateAnalysis(ctx, analysisPrompt)
		if err != nil {
			log.Printf("⚠️  Failed to generate AI analysis: %v", err)
			// ifAIservicefail，use本地analysislogic
			analysisResult = s.generateLocalAnalysis(portfolio)
		} else {
			log.Printf("✅ Generated AI analysis for user: %s", userID)
		}
	} else {
		// if没有AI客户端，use本地analysislogic
		analysisResult = s.generateLocalAnalysis(portfolio)
		log.Printf("📝 Generated local analysis for user: %s", userID)
	}

	// 4. 构建returnresult
	analysis := &models.Analysis{
		UserID:    userID,
		Summary:   analysisResult,
		Timestamp: time.Now(),
		Success:   true,
	}

	return analysis, nil
}

// buildAnalysisPrompt 构建analysistip词
// 对应Pythonversion tip词构建logic
func (s *AnalysisService) buildAnalysisPrompt(portfolio *models.Portfolio) string {
	var promptBuilder strings.Builder

	promptBuilder.WriteString("請analysis以下投資組合並provide專業建議：\n\n")
	promptBuilder.WriteString(fmt.Sprintf("用戶ID: %s\n", portfolio.UserID))
	promptBuilder.WriteString(fmt.Sprintf("總資產價value: ¥%.0f\n\n", portfolio.TotalAssets))

	promptBuilder.WriteString("資產configure詳情：\n")
	for _, asset := range portfolio.Assets {
		percentage := (asset.CurrentValue / portfolio.TotalAssets) * 100
		promptBuilder.WriteString(fmt.Sprintf("- %s: ¥%.0f (%.1f%%)\n",
			asset.AssetType, asset.CurrentValue, percentage))
	}

	promptBuilder.WriteString("\n請provide：\n")
	promptBuilder.WriteString("1. 當前資產configure analysis\n")
	promptBuilder.WriteString("2. 風險評估\n")
	promptBuilder.WriteString("3. 優化建議\n")
	promptBuilder.WriteString("4. 具體 改進步驟\n")
	promptBuilder.WriteString("\n請用日文回答，保持專業且易懂。")

	return promptBuilder.String()
}

// generateLocalAnalysis generate本地analysis result（当AIserviceunavailable时）
func (s *AnalysisService) generateLocalAnalysis(portfolio *models.Portfolio) string {
	var analysis strings.Builder

	analysis.WriteString("## 投資組合analysis報告\n\n")

	// 基本info
	analysis.WriteString(fmt.Sprintf("**總資產價値**: ¥%.0f\n", portfolio.TotalAssets))
	analysis.WriteString(fmt.Sprintf("**asset種類数**: %d\n\n", len(portfolio.Assets)))

	// assetconfigureanalysis
	analysis.WriteString("### assetconfigureanalysis\n\n")

	allocation := s.core.assetService.CalculateAssetAllocation(portfolio)
	for assetType, percentage := range allocation {
		var comment string
		switch {
		case percentage > 70:
			comment = "（集中度 高い）"
		case percentage > 40:
			comment = "（主要asset）"
		case percentage < 5:
			comment = "（少額configure）"
		default:
			comment = "（適度なconfigure）"
		}

		analysis.WriteString(fmt.Sprintf("- **%s**: %.1f%% %s\n", assetType, percentage, comment))
	}

	// risk评估
	analysis.WriteString("\n### リスク評価\n\n")
	riskLevel := s.assessRiskLevel(portfolio)
	analysis.WriteString(fmt.Sprintf("**リスクレベル**: %s\n\n", riskLevel))

	switch riskLevel {
	case "低":
		analysis.WriteString("現在 portfolio 保守  、安定性 重視したconfigure す。")
	case "中":
		analysis.WriteString("バランス 取れたportfolio す。リスク 収益 バランス 適度 す。")
	case "高":
		analysis.WriteString("積極 なportfolio す。高いリターン 期待 きます 、リスクも高い す。")
	}

	// optimize建议
	analysis.WriteString("\n\n### 最適化 提案\n\n")
	suggestions := s.generateOptimizationSuggestions(portfolio, allocation)
	for i, suggestion := range suggestions {
		analysis.WriteString(fmt.Sprintf("%d. %s\n", i+1, suggestion))
	}

	analysis.WriteString("\n---\n")
	analysis.WriteString("*こ analysis 自動generateされたも  す。投資判断 際 specialist家 ご相談ください。*")

	return analysis.String()
}

// assessRiskLevel 评估risk水平
func (s *AnalysisService) assessRiskLevel(portfolio *models.Portfolio) string {
	allocation := s.core.assetService.CalculateAssetAllocation(portfolio)

	// 根据assettypeallocation计算risk分数
	riskScore := 0.0

	for assetType, percentage := range allocation {
		var assetRisk float64
		switch assetType {
		case "Earnings":
			assetRisk = 0.1 // 低risk
		case "Points":
			assetRisk = 0.2 // 较低risk
		case "Stablecoin":
			assetRisk = 0.3 // 中等risk
		case "Items":
			assetRisk = 0.6 // 较高risk
		case "Giga":
			assetRisk = 0.4 // 中等偏高risk
		default:
			assetRisk = 0.5 // 默认中等risk
		}

		riskScore += assetRisk * (percentage / 100)
	}

	// 分classrisk等级
	switch {
	case riskScore <= 0.2:
		return "低"
	case riskScore <= 0.4:
		return "中"
	default:
		return "高"
	}
}

// generateOptimizationSuggestions generateoptimize建议
func (s *AnalysisService) generateOptimizationSuggestions(portfolio *models.Portfolio, allocation map[string]float64) []string {
	var suggestions []string

	// check过度集中
	for assetType, percentage := range allocation {
		if percentage > 80 {
			suggestions = append(suggestions, fmt.Sprintf("%sへ 集中度 非常 高い す。リスク分散 for、他 assetクラスへ 投資 検討してください。", assetType))
		}
	}

	// checkwhether有现金classasset
	hasCash := false
	for assetType := range allocation {
		if assetType == "Earnings" {
			hasCash = true
			break
		}
	}

	if !hasCash {
		suggestions = append(suggestions, "緊急資金 して、一定額 現金類asset（Earnings） 保有するこ  お勧めします。")
	}

	// checkwhether缺乏多样性
	if len(portfolio.Assets) < 3 {
		suggestions = append(suggestions, "asset 多様性 高めるfor、異なるassetクラスへ 投資 検討してください。")
	}

	// 根据totalasset价valueprovide建议
	if portfolio.TotalAssets < 100000 {
		suggestions = append(suggestions, "現在 asset額 考慮する 、まず 安定 なasset（Points、売上金） 蓄積 優firstするこ  お勧めします。")
	} else if portfolio.TotalAssets > 500000 {
		suggestions = append(suggestions, "十分なasset お持ち す  、成長性 ある投資商品へ 分散投資 検討 きます。")
	}

	// if没有找到具体问题，provide通用建议
	if len(suggestions) == 0 {
		suggestions = append(suggestions, "現在 portfolio 良好 す。定期 な見直し 市場動向 応じたadjust 継続してください。")
	}

	return suggestions
}

// ComparePortfolios 比较portfolio（forA/Btestorhistory对比）
func (s *AnalysisService) ComparePortfolios(ctx context.Context, portfolio1, portfolio2 *models.Portfolio) (map[string]interface{}, error) {
	log.Printf("📊 Comparing portfolios: %s vs %s", portfolio1.UserID, portfolio2.UserID)

	allocation1 := s.core.assetService.CalculateAssetAllocation(portfolio1)
	allocation2 := s.core.assetService.CalculateAssetAllocation(portfolio2)

	comparison := map[string]interface{}{
		"portfolio1": map[string]interface{}{
			"user_id":     portfolio1.UserID,
			"total_value": portfolio1.TotalAssets,
			"allocation":  allocation1,
			"risk_level":  s.assessRiskLevel(portfolio1),
		},
		"portfolio2": map[string]interface{}{
			"user_id":     portfolio2.UserID,
			"total_value": portfolio2.TotalAssets,
			"allocation":  allocation2,
			"risk_level":  s.assessRiskLevel(portfolio2),
		},
		"differences": map[string]interface{}{
			"value_diff":     portfolio2.TotalAssets - portfolio1.TotalAssets,
			"value_diff_pct": ((portfolio2.TotalAssets - portfolio1.TotalAssets) / portfolio1.TotalAssets) * 100,
		},
	}

	return comparison, nil
}

// GetAnalysisHistory getanalysishistory（mock data）
func (s *AnalysisService) GetAnalysisHistory(ctx context.Context, userID string, days int) ([]map[string]interface{}, error) {
	log.Printf("📜 Getting analysis history for user %s, last %d days", userID, days)

	// if有BigQuery客户端，可以queryhistorydata
	if s.core.bigQueryClient != nil {
		analyticsData, err := s.core.bigQueryClient.QueryUserAnalytics(ctx, userID)
		if err != nil {
			log.Printf("⚠️  Failed to get analytics from BigQuery: %v", err)
			// fail时returnmock data
			return s.getMockAnalysisHistory(userID, days), nil
		}

		log.Printf("✅ Retrieved analysis history from BigQuery")
		return analyticsData, nil
	}

	// returnmockhistorydata
	return s.getMockAnalysisHistory(userID, days), nil
}

// getMockAnalysisHistory generatemockanalysishistory
func (s *AnalysisService) getMockAnalysisHistory(userID string, days int) []map[string]interface{} {
	history := []map[string]interface{}{}

	for i := days; i >= 0; i -= 7 { // every Monday次analysis
		date := time.Now().AddDate(0, 0, -i)

		// mock不同时期 analysis result
		mockAnalysis := map[string]interface{}{
			"date":            date.Format("2006-01-02"),
			"user_id":         userID,
			"total_assets":    150000 + float64(i*100), // mockassetgrowth
			"risk_level":      []string{"低", "中", "高"}[i%3],
			"score":           80 + (i % 20),
			"recommendations": 3 + (i % 3),
		}

		history = append(history, mockAnalysis)
	}

	return history
}
