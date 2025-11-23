package services

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"saving_advisor_system_go/internal/models"
)

// RecommendationService recommendation service
// 对应Pythonversion recommendation_service.py，负责多智能体recommendationsystem
type RecommendationService struct {
	core *SavingAdvisorServices

	// cacherecommendationresult
	cache map[string]*models.MultiAgentRecommendations
}

// NewRecommendationService createrecommendation service实例
func NewRecommendationService(core *SavingAdvisorServices) *RecommendationService {
	return &RecommendationService{
		core:  core,
		cache: make(map[string]*models.MultiAgentRecommendations),
	}
}

// GenerateRecommendations generaterecommendation
// 对应Pythonversion generate_recommendationsmethod，implement多智能体协作system
func (s *RecommendationService) GenerateRecommendations(ctx context.Context, userID string, forceFresh bool) (*models.MultiAgentRecommendations, error) {
	log.Printf("🤖 Generating recommendations for user: %s (force_fresh: %v)", userID, forceFresh)

	// 1. getuserportfolio
	portfolio, err := s.core.assetService.GetUserPortfolio(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get portfolio for recommendations: %w", err)
	}

	// 2. checkcache（if不强制refresh）
	if !forceFresh {
		if cached := s.getCachedRecommendations(userID); cached != nil {
			log.Printf("✅ Retrieved recommendations from cache for user: %s", userID)
			return cached, nil
		}

		// checkFirestorecache
		if s.core.firestoreClient != nil {
			if cached, err := s.core.firestoreClient.GetRecommendations(ctx, userID); err == nil {
				log.Printf("✅ Retrieved recommendations from Firestore cache for user: %s", userID)
				s.cacheRecommendations(userID, cached)
				return cached, nil
			}
		}
	}

	// 3. call多智能体systemgeneraterecommendation
	recommendations, err := s.generateMultiAgentRecommendations(ctx, portfolio)
	if err != nil {
		return nil, fmt.Errorf("failed to generate multi-agent recommendations: %w", err)
	}

	// 4. cacheresult
	s.cacheRecommendations(userID, recommendations)

	// 5. save到Firestore（ifavailable）
	if s.core.firestoreClient != nil {
		if err := s.core.firestoreClient.SaveRecommendations(ctx, userID, recommendations); err != nil {
			log.Printf("⚠️  Failed to save recommendations to Firestore: %v", err)
		}
	}

	log.Printf("✅ Generated fresh recommendations for user: %s", userID)
	return recommendations, nil
}

// generateMultiAgentRecommendations generate多智能体recommendation
// implement多智能体recommendationlogic，对应Pythonversion MultiAgentSystem
func (s *RecommendationService) generateMultiAgentRecommendations(ctx context.Context, portfolio *models.Portfolio) (*models.MultiAgentRecommendations, error) {
	log.Printf("🔬 Generating multi-agent recommendations for portfolio")

	// 定义智能体list，对应不同 assettype
	agents := []string{
		"PortfolioAnalysisAgent",
		"RiskAssessmentAgent",
		"MarketAnalysisAgent",
	}

	var analyses []models.AgentAnalysis

	// 为每个智能体generateanalysis
	for _, agentName := range agents {
		analysis, err := s.generateAgentAnalysis(ctx, agentName, portfolio)
		if err != nil {
			log.Printf("⚠️  Agent %s failed: %v", agentName, err)
			continue // 某个agentfail不影响整体
		}
		analyses = append(analyses, *analysis)
	}

	// if所有agent都fail了，generate默认recommendation
	if len(analyses) == 0 {
		log.Printf("⚠️  All agents failed, generating default recommendations")
		analyses = s.generateDefaultRecommendations(portfolio)
	}

	// generate整体评估
	overallAssessment := s.generateOverallAssessment(portfolio, analyses)

	return &models.MultiAgentRecommendations{
		UserID:            portfolio.UserID,
		Analyses:          analyses,
		OverallAssessment: overallAssessment,
		Timestamp:         time.Now().Format(time.RFC3339),
	}, nil
}

// generateAgentAnalysis 为特定智能体generateanalysis
func (s *RecommendationService) generateAgentAnalysis(ctx context.Context, agentName string, portfolio *models.Portfolio) (*models.AgentAnalysis, error) {
	log.Printf("🤖 Generating analysis for agent: %s", agentName)

	// 构建特定于智能体 tip词
	prompt := s.buildAgentPrompt(agentName, portfolio)

	var findings string
	var recommendations []models.Recommendation

	// ifOpenAI客户端available，callAIgeneraterecommendation
	if s.core.openAIClient != nil {
		aiResponse, err := s.core.openAIClient.GenerateRecommendation(ctx, agentName, prompt)
		if err != nil {
			log.Printf("⚠️  AI generation failed for agent %s: %v", agentName, err)
			// fail时use本地logic
			findings, recommendations = s.generateLocalAgentAnalysis(agentName, portfolio)
		} else {
			// parseAIresponse
			findings, recommendations = s.parseAIResponse(agentName, aiResponse, portfolio)
		}
	} else {
		// use本地analysislogic
		findings, recommendations = s.generateLocalAgentAnalysis(agentName, portfolio)
	}

	// 确定主要assettype
	assetType := s.determineAgentAssetType(agentName, portfolio)

	analysis := &models.AgentAnalysis{
		AgentName:       agentName,
		AssetType:       assetType,
		Findings:        findings,
		Recommendations: recommendations,
	}

	log.Printf("✅ Generated analysis for agent %s: %d recommendations", agentName, len(recommendations))
	return analysis, nil
}

// buildAgentPrompt 构建智能体特定 tip词
func (s *RecommendationService) buildAgentPrompt(agentName string, portfolio *models.Portfolio) string {
	var promptBuilder strings.Builder

	// baseinfo
	promptBuilder.WriteString(fmt.Sprintf("あなた %s して、以下 portfolio analysisしてください：\n\n", agentName))
	promptBuilder.WriteString(fmt.Sprintf("総asset価値: ¥%.0f\n", portfolio.TotalAssets))

	for _, asset := range portfolio.Assets {
		percentage := (asset.CurrentValue / portfolio.TotalAssets) * 100
		promptBuilder.WriteString(fmt.Sprintf("- %s: ¥%.0f (%.1f%%)\n",
			asset.AssetType, asset.CurrentValue, percentage))
	}

	// 根据不同智能体add特定指令
	switch agentName {
	case "PortfolioAnalysisAgent":
		promptBuilder.WriteString("\n以下 観点 from analysisしてください：\n")
		promptBuilder.WriteString("1. 現在 assetconfigure 評価\n")
		promptBuilder.WriteString("2. バランス改善 提案\n")
		promptBuilder.WriteString("3. 具体 なconfigureadjust案\n")
	case "RiskAssessmentAgent":
		promptBuilder.WriteString("\n以下 観点 from analysisしてください：\n")
		promptBuilder.WriteString("1. 現在 リスクレベル評価\n")
		promptBuilder.WriteString("2. リスク軽減策\n")
		promptBuilder.WriteString("3. リスク リターン バランス改善案\n")
	case "MarketAnalysisAgent":
		promptBuilder.WriteString("\n以下 観点 from analysisしてください：\n")
		promptBuilder.WriteString("1. 市場動向 基づく評価\n")
		promptBuilder.WriteString("2. 成長機会 特定\n")
		promptBuilder.WriteString("3. 市場環境 考慮した投資提案\n")
	}

	promptBuilder.WriteString("\n回答 以下 形式 お願いします：\n")
	promptBuilder.WriteString("【analysis結果】\n（analysisin容）\n")
	promptBuilder.WriteString("【recommendations】\n1. タイトル: 説明\n2. タイトル: 説明\n")

	return promptBuilder.String()
}

// generateLocalAgentAnalysis generate本地智能体analysis
func (s *RecommendationService) generateLocalAgentAnalysis(agentName string, portfolio *models.Portfolio) (string, []models.Recommendation) {
	switch agentName {
	case "PortfolioAnalysisAgent":
		return s.generatePortfolioAnalysis(portfolio)
	case "RiskAssessmentAgent":
		return s.generateRiskAssessment(portfolio)
	case "MarketAnalysisAgent":
		return s.generateMarketAnalysis(portfolio)
	default:
		return s.generateGenericAnalysis(portfolio)
	}
}

// generatePortfolioAnalysis generateportfolioanalysis
func (s *RecommendationService) generatePortfolioAnalysis(portfolio *models.Portfolio) (string, []models.Recommendation) {
	allocation := s.core.assetService.CalculateAssetAllocation(portfolio)

	findings := "現在 portfolio analysisしました。"

	// 找出比重最大 asset
	var maxAsset string
	var maxPercentage float64
	for assetType, percentage := range allocation {
		if percentage > maxPercentage {
			maxPercentage = percentage
			maxAsset = assetType
		}
	}

	findings += fmt.Sprintf(" %s %.1f%% 占め、主要asset なっています。", maxAsset, maxPercentage)

	var recommendations []models.Recommendation

	// 根据configure情况generaterecommendation
	if maxPercentage > 70 {
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "diversify"),
			Title:            "asset分散 改善",
			Description:      fmt.Sprintf("%sへ 集中度 高いfor、他 assetクラスへ 分散投資 お勧めします", maxAsset),
			AssetType:        maxAsset,
			PotentialGain:    5000,
			AgentName:        "PortfolioAnalysisAgent",
			Priority:         1,
		})
	}

	// if缺少稳定asset，recommendation增加
	if _, hasStable := allocation["Earnings"]; !hasStable {
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "stable_asset"),
			Title:            "安定asset append",
			Description:      "緊急資金 してEarnings 比重 increaseこ  お勧めします",
			AssetType:        "Earnings",
			PotentialGain:    3000,
			AgentName:        "PortfolioAnalysisAgent",
			Priority:         2,
		})
	}

	return findings, recommendations
}

// generateRiskAssessment generaterisk评估
func (s *RecommendationService) generateRiskAssessment(portfolio *models.Portfolio) (string, []models.Recommendation) {
	riskLevel := s.core.analysisService.assessRiskLevel(portfolio)

	findings := fmt.Sprintf("リスク評価 結果、現在 portfolio リスクレベル 「%s」 す。", riskLevel)

	var recommendations []models.Recommendation

	switch riskLevel {
	case "高":
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "reduce_risk"),
			Title:            "リスク軽減策",
			Description:      "高リスクasset 比重 下げ、安定 なasset 比重 increaseこ  お勧めします",
			AssetType:        "Points",
			PotentialGain:    8000,
			AgentName:        "RiskAssessmentAgent",
			Priority:         1,
		})
	case "低":
		if portfolio.TotalAssets > 200000 {
			recommendations = append(recommendations, models.Recommendation{
				RecommendationID: generateRecommendationID(portfolio.UserID, "growth_opportunity"),
				Title:            "成長機会 utilize",
				Description:      "十分な安定asset お持ちな  、成長性 ある投資 少額 from 始めるこ  検討 きます",
				AssetType:        "Stablecoin",
				PotentialGain:    15000,
				AgentName:        "RiskAssessmentAgent",
				Priority:         2,
			})
		}
	}

	return findings, recommendations
}

// generateMarketAnalysis generate市场analysis
func (s *RecommendationService) generateMarketAnalysis(portfolio *models.Portfolio) (string, []models.Recommendation) {
	findings := "現在 市場環境 analysisし、portfolio  適合性 評価しました。"

	var recommendations []models.Recommendation

	// 基于currentdategenerate不同 市场建议
	now := time.Now()
	quarter := (int(now.Month())-1)/3 + 1

	switch quarter {
	case 1: // Q1
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "q1_strategy"),
			Title:            "year始 投資戦略",
			Description:      "newyear度 向けて、Points投資 比重 見直し、成長機会 探るこ  お勧めします",
			AssetType:        "Points",
			PotentialGain:    12000,
			AgentName:        "MarketAnalysisAgent",
			Priority:         2,
		})
	case 2: // Q2
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "q2_strategy"),
			Title:            "中期成長戦略",
			Description:      "市場 安定期 utilizeし、バランス型 投資配分 検討するこ  お勧めします",
			AssetType:        "Items",
			PotentialGain:    10000,
			AgentName:        "MarketAnalysisAgent",
			Priority:         2,
		})
	case 3: // Q3
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "q3_strategy"),
			Title:            "夏季投資機会",
			Description:      "夏季 消費動向 考慮し、関連assetへ 投資機会 検討 きます",
			AssetType:        "Earnings",
			PotentialGain:    8000,
			AgentName:        "MarketAnalysisAgent",
			Priority:         3,
		})
	default: // Q4
		recommendations = append(recommendations, models.Recommendation{
			RecommendationID: generateRecommendationID(portfolio.UserID, "q4_strategy"),
			Title:            "year末asset整理",
			Description:      "year末 向けてasset配分 見直し 来year 投資計画 準備 お勧めします",
			AssetType:        "Stablecoin",
			PotentialGain:    6000,
			AgentName:        "MarketAnalysisAgent",
			Priority:         2,
		})
	}

	return findings, recommendations
}

// generateGenericAnalysis generate通用analysis
func (s *RecommendationService) generateGenericAnalysis(portfolio *models.Portfolio) (string, []models.Recommendation) {
	findings := "portfolio 全般 なanalysis 行いました。"

	recommendations := []models.Recommendation{
		{
			RecommendationID: generateRecommendationID(portfolio.UserID, "general_advice"),
			Title:            "定期 な見直し",
			Description:      "投資portfolio 定期 な見直し 最適化 お勧めします",
			AssetType:        "全般",
			PotentialGain:    5000,
			AgentName:        "GeneralAgent",
			Priority:         3,
		},
	}

	return findings, recommendations
}

// parseAIResponse parseAIresponse
func (s *RecommendationService) parseAIResponse(agentName, aiResponse string, portfolio *models.Portfolio) (string, []models.Recommendation) {
	// 简单 AIresponseparselogic
	// 在实际application中，这里需要更复杂 自然语言handle

	lines := strings.Split(aiResponse, "\n")
	var findings string
	var recommendations []models.Recommendation

	inFindings := false
	inRecommendations := false

	for _, line := range lines {
		line = strings.TrimSpace(line)

		if strings.Contains(line, "【analysis結果】") {
			inFindings = true
			inRecommendations = false
			continue
		}

		if strings.Contains(line, "【recommendations】") {
			inFindings = false
			inRecommendations = true
			continue
		}

		if inFindings && line != "" {
			findings += line + " "
		}

		if inRecommendations && strings.HasPrefix(line, "1.") || strings.HasPrefix(line, "2.") || strings.HasPrefix(line, "3.") {
			// parserecommendationproject
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				title := strings.TrimSpace(strings.TrimPrefix(parts[0], strings.Split(parts[0], ".")[0]+"."))
				description := strings.TrimSpace(parts[1])

				recommendation := models.Recommendation{
					RecommendationID: generateRecommendationID(portfolio.UserID, agentName+"_ai"),
					Title:            title,
					Description:      description,
					AssetType:        s.determineAgentAssetType(agentName, portfolio),
					PotentialGain:    7500, // 默认潜在收益
					AgentName:        agentName,
					Priority:         2,
				}

				recommendations = append(recommendations, recommendation)
			}
		}
	}

	// ifparsefail，回退到本地logic
	if findings == "" || len(recommendations) == 0 {
		return s.generateLocalAgentAnalysis(agentName, portfolio)
	}

	return findings, recommendations
}

// determineAgentAssetType 确定智能体 主要assettype
func (s *RecommendationService) determineAgentAssetType(agentName string, portfolio *models.Portfolio) string {
	allocation := s.core.assetService.CalculateAssetAllocation(portfolio)

	// 找出比重最大 assettype
	var maxAsset string
	var maxPercentage float64
	for assetType, percentage := range allocation {
		if percentage > maxPercentage {
			maxPercentage = percentage
			maxAsset = assetType
		}
	}

	// 根据智能体typereturn相关assettype
	switch agentName {
	case "PortfolioAnalysisAgent":
		return maxAsset
	case "RiskAssessmentAgent":
		return "Points" // 偏向安全asset
	case "MarketAnalysisAgent":
		return "Stablecoin" // 偏向市场相关asset
	default:
		return maxAsset
	}
}

// generateDefaultRecommendations generate默认recommendation（当所有智能体都fail时）
func (s *RecommendationService) generateDefaultRecommendations(portfolio *models.Portfolio) []models.AgentAnalysis {
	log.Printf("📝 Generating default recommendations for portfolio")

	return []models.AgentAnalysis{
		{
			AgentName: "DefaultAgent",
			AssetType: "全般",
			Findings:  "現在 portfolio 安定 な構成 なっています。定期 な見直し お勧めします。",
			Recommendations: []models.Recommendation{
				{
					RecommendationID: generateRecommendationID(portfolio.UserID, "default"),
					Title:            "定期 な見直し",
					Description:      "3ヶmonthご  portfolio 見直し 行い、市場環境 応じたadjust 検討してください",
					AssetType:        "全般",
					PotentialGain:    5000,
					AgentName:        "DefaultAgent",
					Priority:         2,
				},
			},
		},
	}
}

// generateOverallAssessment generate整体评估
func (s *RecommendationService) generateOverallAssessment(portfolio *models.Portfolio, analyses []models.AgentAnalysis) string {
	var assessment strings.Builder

	assessment.WriteString("複数 AIagent よるanalysis 結果、")
	assessment.WriteString(fmt.Sprintf("総額¥%.0f portfolio ついて以下 総合評価 いたします。", portfolio.TotalAssets))

	totalRecommendations := 0
	for _, analysis := range analyses {
		totalRecommendations += len(analysis.Recommendations)
	}

	assessment.WriteString(fmt.Sprintf(" %d個 AIagent from 合計%d件 提案 受けました。",
		len(analyses), totalRecommendations))

	// 根据recommendationcountprovide不同 评估
	switch {
	case totalRecommendations >= 5:
		assessment.WriteString(" 改善 余地 多く見つかりました  、段階 な最適化 お勧めします。")
	case totalRecommendations >= 3:
		assessment.WriteString(" いくつか 改善点 見つかりました。優first度 高い項目 from executeするこ  お勧めします。")
	default:
		assessment.WriteString(" 現在 portfolio 比較 良好な状態 す。提案された項目 参考 微adjust 検討してください。")
	}

	return assessment.String()
}

// getCachedRecommendations getcache recommendation
func (s *RecommendationService) getCachedRecommendations(userID string) *models.MultiAgentRecommendations {
	// checkcachewhetherexpired（30minute）
	if cached, exists := s.cache[userID]; exists {
		cacheTime, err := time.Parse(time.RFC3339, cached.Timestamp)
		if err == nil && time.Since(cacheTime) < 30*time.Minute {
			return cached
		}
		// 清除expiredcache
		delete(s.cache, userID)
	}
	return nil
}

// cacheRecommendations cacherecommendationresult
func (s *RecommendationService) cacheRecommendations(userID string, recommendations *models.MultiAgentRecommendations) {
	s.cache[userID] = recommendations
}

// generateRecommendationID generaterecommendationID
func generateRecommendationID(userID, suffix string) string {
	timestamp := time.Now().Unix()
	return fmt.Sprintf("%s_%s_%d", userID, suffix, timestamp)
}

// SubmitFeedback submitrecommendationfeedback
func (s *RecommendationService) SubmitFeedback(ctx context.Context, feedback *models.FeedbackRequest) error {
	log.Printf("📝 Submitting feedback for recommendation %s: %s", feedback.RecommendationID, feedback.Status)

	// 这里可以将feedbacksave到database
	if s.core.bigQueryClient != nil {
		eventData := map[string]interface{}{
			"recommendation_id": feedback.RecommendationID,
			"status":            feedback.Status,
			"rejection_reason":  feedback.RejectionReason,
			"agent_name":        feedback.AgentName,
		}

		err := s.core.bigQueryClient.InsertUserEvent(ctx, feedback.UserID, "recommendation_feedback", eventData)
		if err != nil {
			log.Printf("⚠️  Failed to save feedback to BigQuery: %v", err)
		}
	}

	// 根据feedbackadjust未来recommendation（简单 学习机制）
	s.updateRecommendationModel(feedback)

	log.Printf("✅ Feedback submitted successfully")
	return nil
}

// updateRecommendationModel 根据feedbackupdaterecommendationmodel
func (s *RecommendationService) updateRecommendationModel(feedback *models.FeedbackRequest) {
	// 简单 feedback学习机制
	// 在实际application中，这里可以implement更复杂 机器学习logic
	log.Printf("📊 Updating recommendation model based on feedback: %s", feedback.Status)

	// 这里可以recorduser偏好，forimprove未来 recommendation算法
}
