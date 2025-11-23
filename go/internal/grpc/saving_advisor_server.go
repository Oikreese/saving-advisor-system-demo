package grpc

import (
	"context"
	"log"
	"time"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "saving_advisor_system_go/api/proto"
	"saving_advisor_system_go/internal/models"
	"saving_advisor_system_go/internal/services"
)

// SavingAdvisorServer gRPCserverimplement
// 对应Pythonversion SavingAdvisorServiceServicer
type SavingAdvisorServer struct {
	pb.UnimplementedSavingAdvisorServiceServer
	coreServices *services.SavingAdvisorServices
}

// NewSavingAdvisorServer creategRPCserver实例
func NewSavingAdvisorServer(coreServices *services.SavingAdvisorServices) *SavingAdvisorServer {
	return &SavingAdvisorServer{
		coreServices: coreServices,
	}
}

// GetUserPortfolio getuserportfolio
// implementproto定义 GetUserPortfoliomethod
func (s *SavingAdvisorServer) GetUserPortfolio(ctx context.Context, req *pb.PortfolioRequest) (*pb.PortfolioResponse, error) {
	log.Printf("📊 gRPC: GetUserPortfolio called for user: %s", req.UserId)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}

	// callasset servicegetportfolio
	portfolio, err := s.coreServices.GetAssetService().GetUserPortfolio(ctx, req.UserId)
	if err != nil {
		log.Printf("❌ Failed to get portfolio: %v", err)
		return nil, status.Error(codes.Internal, "failed to get user portfolio")
	}

	// convert为protobuf格式
	pbAssets := make([]*pb.UserAsset, len(portfolio.Assets))
	for i, asset := range portfolio.Assets {
		pbAssets[i] = &pb.UserAsset{
			AssetType:        asset.AssetType,
			CurrentValue:     asset.CurrentValue,
			TargetAllocation: asset.TargetAllocation,
			LastUpdated:      asset.LastUpdated,
		}
	}

	response := &pb.PortfolioResponse{
		Portfolio: &pb.UserPortfolio{
			UserId:      portfolio.UserID,
			Assets:      pbAssets,
			TotalValue:  portfolio.TotalAssets,
			LastUpdated: portfolio.LastUpdated,
		},
		Success: true,
	}

	log.Printf("✅ gRPC: Portfolio returned for user %s: ¥%.0f", req.UserId, portfolio.TotalAssets)
	return response, nil
}

// GetRecommendationsPreview get多智能体recommendation预览
// implementproto定义 GetRecommendationsPreviewmethod
func (s *SavingAdvisorServer) GetRecommendationsPreview(ctx context.Context, req *pb.RecommendationsPreviewRequest) (*pb.RecommendationsPreviewResponse, error) {
	log.Printf("🤖 gRPC: GetRecommendationsPreview called for user: %s (force_fresh: %v)", req.UserId, req.ForceFresh)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}

	// callrecommendation servicegeneraterecommendation
	recommendations, err := s.coreServices.GetRecommendationService().GenerateRecommendations(ctx, req.UserId, req.ForceFresh)
	if err != nil {
		log.Printf("❌ Failed to generate recommendations: %v", err)
		return nil, status.Error(codes.Internal, "failed to generate recommendations")
	}

	// convert为protobuf格式
	pbAnalyses := make([]*pb.AgentAnalysis, len(recommendations.Analyses))
	for i, analysis := range recommendations.Analyses {
		// convertrecommendationlist
		pbRecommendations := make([]*pb.Recommendation, len(analysis.Recommendations))
		for j, rec := range analysis.Recommendations {
			pbRecommendations[j] = &pb.Recommendation{
				RecommendationId: rec.RecommendationID,
				Title:            rec.Title,
				Description:      rec.Description,
				AssetType:        rec.AssetType,
				PotentialGain:    rec.PotentialGain,
				AgentName:        rec.AgentName,
				Priority:         rec.Priority,
			}
		}

		pbAnalyses[i] = &pb.AgentAnalysis{
			AgentName:       analysis.AgentName,
			AssetType:       analysis.AssetType,
			Findings:        analysis.Findings,
			Recommendations: pbRecommendations,
		}
	}

	response := &pb.RecommendationsPreviewResponse{
		Recommendations: &pb.MultiAgentRecommendations{
			UserId:            recommendations.UserID,
			Analyses:          pbAnalyses,
			OverallAssessment: recommendations.OverallAssessment,
			Timestamp:         recommendations.Timestamp,
		},
		Success: true,
	}

	totalRecs := 0
	for _, analysis := range recommendations.Analyses {
		totalRecs += len(analysis.Recommendations)
	}

	log.Printf("✅ gRPC: Recommendations returned for user %s: %d agents, %d total recommendations",
		req.UserId, len(recommendations.Analyses), totalRecs)
	return response, nil
}

// SubmitRecommendationFeedback submitrecommendationfeedback
// implementproto定义 SubmitRecommendationFeedbackmethod
func (s *SavingAdvisorServer) SubmitRecommendationFeedback(ctx context.Context, req *pb.FeedbackRequest) (*pb.FeedbackResponse, error) {
	log.Printf("📝 gRPC: SubmitRecommendationFeedback called for recommendation: %s", req.RecommendationId)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}
	if req.RecommendationId == "" {
		return nil, status.Error(codes.InvalidArgument, "recommendation_id is required")
	}
	if req.Status == "" {
		return nil, status.Error(codes.InvalidArgument, "status is required")
	}

	// convert为in部model
	feedback := &models.FeedbackRequest{
		UserID:           req.UserId,
		RecommendationID: req.RecommendationId,
		Status:           req.Status,
		RejectionReason:  req.RejectionReason,
		RejectionDetail:  req.RejectionDetail,
		AgentName:        req.AgentName,
	}

	// callrecommendation servicesubmitfeedback
	err := s.coreServices.GetRecommendationService().SubmitFeedback(ctx, feedback)
	if err != nil {
		log.Printf("❌ Failed to submit feedback: %v", err)
		return nil, status.Error(codes.Internal, "failed to submit feedback")
	}

	response := &pb.FeedbackResponse{
		Success: true,
		Message: "Feedback submitted successfully",
	}

	log.Printf("✅ gRPC: Feedback submitted for recommendation %s: %s", req.RecommendationId, req.Status)
	return response, nil
}

// GetVisualizationData get可视化data
// implementproto定义 GetVisualizationDatamethod
func (s *SavingAdvisorServer) GetVisualizationData(ctx context.Context, req *pb.VisualizationRequest) (*pb.VisualizationResponse, error) {
	log.Printf("📊 gRPC: GetVisualizationData called for user: %s, chart: %s", req.UserId, req.ChartType)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}
	if req.ChartType == "" {
		req.ChartType = "pie" // 默认饼图
	}

	// callasset serviceget可视化data
	vizData, err := s.coreServices.GetAssetService().GetVisualizationData(ctx, req.UserId, req.ChartType)
	if err != nil {
		log.Printf("❌ Failed to get visualization data: %v", err)
		return nil, status.Error(codes.Internal, "failed to get visualization data")
	}

	// convertassetdecomposedata
	assetBreakdown := make(map[string]float64)
	for assetType, value := range vizData.AssetBreakdown {
		assetBreakdown[assetType] = value
	}

	response := &pb.VisualizationResponse{
		Data: &pb.VisualizationData{
			ChartType:  vizData.ChartType,
			Data:       assetBreakdown,
			TotalValue: vizData.TotalValue,
			Timestamp:  vizData.Timestamp,
		},
		Success: true,
	}

	log.Printf("✅ gRPC: Visualization data returned for user %s: %d asset types",
		req.UserId, len(vizData.AssetBreakdown))
	return response, nil
}

// GetUserTasks getusertasklist
// implementproto定义 GetUserTasksmethod
func (s *SavingAdvisorServer) GetUserTasks(ctx context.Context, req *pb.TasksRequest) (*pb.TasksResponse, error) {
	log.Printf("📋 gRPC: GetUserTasks called for user: %s", req.UserId)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}

	// generatemocktaskdata（在实际application中，这里shouldcalltaskservice）
	mockTasks := s.generateMockTasks(req.UserId)

	// convert为protobuf格式
	pbTasks := make([]*pb.Task, len(mockTasks.Tasks))
	for i, task := range mockTasks.Tasks {
		pbTasks[i] = &pb.Task{
			TaskId:           task.TaskID,
			Title:            task.Title,
			Description:      task.Description,
			DueDate:          task.DueDate,
			CompletionReward: task.CompletionReward,
			Status:           task.Status,
		}
	}

	response := &pb.TasksResponse{
		Tasks:   pbTasks,
		Success: true,
	}

	log.Printf("✅ gRPC: Tasks returned for user %s: %d tasks", req.UserId, len(mockTasks.Tasks))
	return response, nil
}

// HealthCheck health check
// implementproto定义 HealthCheckmethod
func (s *SavingAdvisorServer) HealthCheck(ctx context.Context, req *pb.EmptyRequest) (*pb.HealthResponse, error) {
	log.Printf("🔍 gRPC: HealthCheck called")

	// executehealth check
	err := s.coreServices.HealthCheck(ctx)
	status := "healthy"
	if err != nil {
		status = "degraded" // 部分serviceunavailable但system仍可run
		log.Printf("⚠️  Health check warnings: %v", err)
	}

	response := &pb.HealthResponse{
		Status:    status,
		Service:   "SavingAdvisorService",
		Version:   "1.0.0",
		Timestamp: time.Now().Format(time.RFC3339),
	}

	log.Printf("✅ gRPC: Health check completed: %s", status)
	return response, nil
}

// GetGeneralAnalysis get通用analysis
// implementproto定义 GetGeneralAnalysismethod
func (s *SavingAdvisorServer) GetGeneralAnalysis(ctx context.Context, req *pb.BaseRequest) (*pb.BaseResponse, error) {
	log.Printf("🔬 gRPC: GetGeneralAnalysis called for user: %s", req.UserId)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}

	// callanalysis service
	analysis, err := s.coreServices.GetAnalysisService().GenerateAnalysis(ctx, req.UserId)
	if err != nil {
		log.Printf("❌ Failed to generate general analysis: %v", err)
		return nil, status.Error(codes.Internal, "failed to generate analysis")
	}

	response := &pb.BaseResponse{
		Success:      analysis.Success,
		Message:      analysis.Summary,
		Timestamp:    time.Now().Format(time.RFC3339),
		ErrorMessage: "", // success时为空
	}

	log.Printf("✅ gRPC: General analysis returned for user %s: %d chars",
		req.UserId, len(analysis.Summary))
	return response, nil
}

// GetComprehensiveAnalysis get综合analysis
// implementproto定义 GetComprehensiveAnalysismethod
func (s *SavingAdvisorServer) GetComprehensiveAnalysis(ctx context.Context, req *pb.ComprehensiveAnalysisRequest) (*pb.ComprehensiveAnalysisResponse, error) {
	log.Printf("🔬 gRPC: GetComprehensiveAnalysis called for user: %s", req.UserId)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}

	// getportfolio
	portfolio, err := s.coreServices.GetAssetService().GetUserPortfolio(ctx, req.UserId)
	if err != nil {
		return nil, status.Error(codes.Internal, "failed to get portfolio")
	}

	// generateanalysis
	analysis, err := s.coreServices.GetAnalysisService().GenerateAnalysis(ctx, req.UserId)
	if err != nil {
		return nil, status.Error(codes.Internal, "failed to generate analysis")
	}

	// 计算预测asset（简单 growthmodel）
	predictedAssets := portfolio.TotalAssets * 1.08 // 假设8% yeargrowth

	response := &pb.ComprehensiveAnalysisResponse{
		UserId:               req.UserId,
		ComprehensiveSummary: analysis.Summary,
		InitialAssets:        portfolio.TotalAssets,
		PredictedAssets:      predictedAssets,
		Timestamp:            time.Now().Format(time.RFC3339),
		Success:              true,
	}

	log.Printf("✅ gRPC: Comprehensive analysis returned for user %s: ¥%.0f -> ¥%.0f",
		req.UserId, portfolio.TotalAssets, predictedAssets)
	return response, nil
}

// generateMockTasks generatemocktaskdata
func (s *SavingAdvisorServer) generateMockTasks(userID string) *models.TasksResponse {
	return &models.TasksResponse{
		Tasks: []models.Task{
			{
				TaskID:           userID + "_task_1",
				Title:            "portfolio見直し",
				Description:      "現在 投資portfolio 見直し、recommendations 確認してください",
				DueDate:          time.Now().AddDate(0, 0, 7).Format("2006-01-02"),
				CompletionReward: 1000,
				Status:           "pending",
			},
			{
				TaskID:           userID + "_task_2",
				Title:            "リスク評価 確認",
				Description:      "最new リスク評価レポート 確認し、必要 応じてadjustしてください",
				DueDate:          time.Now().AddDate(0, 0, 14).Format("2006-01-02"),
				CompletionReward: 800,
				Status:           "pending",
			},
			{
				TaskID:           userID + "_task_3",
				Title:            "市場動向 レビュー",
				Description:      "最new 市場analysis 確認し、投資戦略 updateしてください",
				DueDate:          time.Now().AddDate(0, 0, 30).Format("2006-01-02"),
				CompletionReward: 1200,
				Status:           "in_progress",
			},
		},
	}
}
