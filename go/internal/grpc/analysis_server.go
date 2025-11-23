package grpc

import (
	"context"
	"log"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "saving_advisor_system_go/api/proto"
	"saving_advisor_system_go/internal/services"
)

// AnalysisServer analysis servicegRPCserverimplement
// 对应Pythonversion AnalysisServiceServicer
type AnalysisServer struct {
	pb.UnimplementedAnalysisServiceServer
	coreServices *services.SavingAdvisorServices
}

// NewAnalysisServer createanalysis servicegRPCserver实例
func NewAnalysisServer(coreServices *services.SavingAdvisorServices) *AnalysisServer {
	return &AnalysisServer{
		coreServices: coreServices,
	}
}

// GetGeneralAnalysis getuserportfoliooverallanalysis
// implementproto定义 GetGeneralAnalysismethod
func (s *AnalysisServer) GetGeneralAnalysis(ctx context.Context, req *pb.AnalysisRequest) (*pb.AnalysisResponse, error) {
	log.Printf("🔬 gRPC: GetGeneralAnalysis called for user: %s", req.UserId)

	// argumentvalidate
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id is required")
	}

	// callanalysis servicegenerateanalysis
	analysis, err := s.coreServices.GetAnalysisService().GenerateAnalysis(ctx, req.UserId)
	if err != nil {
		log.Printf("❌ Failed to generate analysis: %v", err)
		return nil, status.Error(codes.Internal, "failed to generate analysis")
	}

	// 构建response
	response := &pb.AnalysisResponse{
		UserId:          analysis.UserID,
		AnalysisSummary: analysis.Summary,
		Timestamp:       analysis.Timestamp.Unix(),
		Success:         analysis.Success,
		ErrorMessage:    "", // success时为空
	}

	log.Printf("✅ gRPC: Analysis returned for user %s: %d chars",
		req.UserId, len(analysis.Summary))
	return response, nil
}
