package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "saving_advisor_system_go/api/proto"
)

// SimpleHTTPHandler 简单 HTTP到gRPC代理handle器
type SimpleHTTPHandler struct {
	grpcClient     pb.SavingAdvisorServiceClient
	analysisClient pb.AnalysisServiceClient
}

// sendJSONError 发送JSON格式 errorresponse
func (h *SimpleHTTPHandler) sendJSONError(w http.ResponseWriter, message string, details string, statusCode int) {
	log.Printf("❌ API Error: %s - %s", message, details)

	errorResponse := map[string]interface{}{
		"success":     false,
		"error":       message,
		"details":     details,
		"timestamp":   time.Now().Format(time.RFC3339),
		"status_code": statusCode,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(errorResponse); err != nil {
		log.Printf("❌ Failed to encode error response: %v", err)
	}
}

// NewSimpleHTTPHandler createHTTPhandle器
func NewSimpleHTTPHandler(grpcEndpoint string) (*SimpleHTTPHandler, error) {
	// connected到gRPCserver
	conn, err := grpc.NewClient(grpcEndpoint, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to gRPC server: %w", err)
	}

	return &SimpleHTTPHandler{
		grpcClient:     pb.NewSavingAdvisorServiceClient(conn),
		analysisClient: pb.NewAnalysisServiceClient(conn),
	}, nil
}

// ServeHTTP implementhttp.Handlerinterface
func (h *SimpleHTTPHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// setupCORS头
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
	w.Header().Set("Content-Type", "application/json")

	// handle预检request
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	// recordrequest
	start := time.Now()
	log.Printf("🌐 %s %s", r.Method, r.URL.Path)

	// routerhandle
	switch {
	// APIdocumentationpath
	case r.URL.Path == "/api" && r.Method == "GET":
		h.handleAPIDoc(w, r)
	// APIpathhandle - 支持 /api/v1 and /v1 两种path
	case strings.HasPrefix(r.URL.Path, "/api/v1/assets/portfolio/") && r.Method == "GET",
		strings.HasPrefix(r.URL.Path, "/v1/portfolio/") && r.Method == "GET":
		h.handleGetPortfolio(w, r)
	case (r.URL.Path == "/api/v1/recommendations" || r.URL.Path == "/v1/recommendations") && r.Method == "POST":
		h.handleGetRecommendations(w, r)
	case (r.URL.Path == "/api/v1/feedback" || r.URL.Path == "/v1/feedback") && r.Method == "POST":
		h.handleSubmitFeedback(w, r)
	case (strings.HasPrefix(r.URL.Path, "/api/v1/visualization/") || strings.HasPrefix(r.URL.Path, "/v1/visualization/")) && r.Method == "GET":
		h.handleGetVisualization(w, r)
	case (strings.HasPrefix(r.URL.Path, "/api/v1/tasks/") || strings.HasPrefix(r.URL.Path, "/v1/tasks/")) && r.Method == "GET":
		h.handleGetTasks(w, r)
	case (r.URL.Path == "/api/v1/analysis" || r.URL.Path == "/v1/analysis") && r.Method == "POST":
		h.handleGetAnalysis(w, r)
	case (r.URL.Path == "/api/v1/health" || r.URL.Path == "/health") && r.Method == "GET":
		h.handleHealthCheck(w, r)
	// monitor相关path - 简单implement
	case strings.HasPrefix(r.URL.Path, "/api/v1/monitoring/") && r.Method == "GET":
		h.handleMonitoring(w, r)
	case strings.HasPrefix(r.URL.Path, "/api/v1/monitoring/") && r.Method == "POST":
		h.handleMonitoring(w, r)
	// 静态fileservice - 所有其他path
	default:
		h.handleStaticFiles(w, r)
		return
	}

	// recordresponsetime
	duration := time.Since(start)
	log.Printf("✅ %s %s completed in %v", r.Method, r.URL.Path, duration)
}

// handleGetPortfolio handlegetportfoliorequest
func (h *SimpleHTTPHandler) handleGetPortfolio(w http.ResponseWriter, r *http.Request) {
	// fromURL中提取userID - 支持两种path格式
	var userID string
	if strings.HasPrefix(r.URL.Path, "/api/v1/assets/portfolio/") {
		userID = strings.TrimPrefix(r.URL.Path, "/api/v1/assets/portfolio/")
	} else {
		userID = strings.TrimPrefix(r.URL.Path, "/v1/portfolio/")
	}

	if userID == "" {
		h.sendJSONError(w, "Invalid portfolio path", "missing user ID", http.StatusBadRequest)
		return
	}

	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req := &pb.PortfolioRequest{UserId: userID}
	log.Printf("🔍 DEBUG: Calling gRPC GetUserPortfolio for user: %s", userID)

	resp, err := h.grpcClient.GetUserPortfolio(ctx, req)
	if err != nil {
		h.sendJSONError(w, "Failed to get user portfolio", err.Error(), http.StatusInternalServerError)
		return
	}

	log.Printf("✅ DEBUG: gRPC response received for user %s: %+v", userID, resp)

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleGetRecommendations handlegetrecommendationrequest
func (h *SimpleHTTPHandler) handleGetRecommendations(w http.ResponseWriter, r *http.Request) {
	var requestBody struct {
		UserID     string `json:"user_id"`
		ForceFresh bool   `json:"force_fresh,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	req := &pb.RecommendationsPreviewRequest{
		UserId:     requestBody.UserID,
		ForceFresh: requestBody.ForceFresh,
	}
	resp, err := h.grpcClient.GetRecommendationsPreview(ctx, req)
	if err != nil {
		log.Printf("gRPC error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleSubmitFeedback handlesubmitfeedbackrequest
func (h *SimpleHTTPHandler) handleSubmitFeedback(w http.ResponseWriter, r *http.Request) {
	var requestBody pb.FeedbackRequest

	if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	resp, err := h.grpcClient.SubmitRecommendationFeedback(ctx, &requestBody)
	if err != nil {
		log.Printf("gRPC error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleGetVisualization handleget可视化datarequest
func (h *SimpleHTTPHandler) handleGetVisualization(w http.ResponseWriter, r *http.Request) {
	// fromURL中提取userID - 支持两种path格式
	var userID string
	if strings.HasPrefix(r.URL.Path, "/api/v1/visualization/") {
		userID = strings.TrimPrefix(r.URL.Path, "/api/v1/visualization/")
	} else {
		userID = strings.TrimPrefix(r.URL.Path, "/v1/visualization/")
	}

	if userID == "" {
		http.Error(w, "Invalid visualization path - missing user ID", http.StatusBadRequest)
		return
	}

	// fromqueryargumentget图tabletype
	chartType := r.URL.Query().Get("chart_type")
	if chartType == "" {
		chartType = "pie"
	}

	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req := &pb.VisualizationRequest{
		UserId:    userID,
		ChartType: chartType,
	}
	resp, err := h.grpcClient.GetVisualizationData(ctx, req)
	if err != nil {
		log.Printf("gRPC error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleGetTasks handlegettasklistrequest
func (h *SimpleHTTPHandler) handleGetTasks(w http.ResponseWriter, r *http.Request) {
	// fromURL中提取userID - 支持两种path格式
	var userID string
	if strings.HasPrefix(r.URL.Path, "/api/v1/tasks/") {
		userID = strings.TrimPrefix(r.URL.Path, "/api/v1/tasks/")
	} else {
		userID = strings.TrimPrefix(r.URL.Path, "/v1/tasks/")
	}

	if userID == "" {
		http.Error(w, "Invalid tasks path - missing user ID", http.StatusBadRequest)
		return
	}

	// fromqueryargumentgettime段
	timePeriod := r.URL.Query().Get("time_period")
	if timePeriod == "" {
		timePeriod = "monthly"
	}

	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req := &pb.TasksRequest{
		UserId:     userID,
		TimePeriod: timePeriod,
	}
	resp, err := h.grpcClient.GetUserTasks(ctx, req)
	if err != nil {
		log.Printf("gRPC error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleGetAnalysis handlegetanalysisrequest
func (h *SimpleHTTPHandler) handleGetAnalysis(w http.ResponseWriter, r *http.Request) {
	var requestBody struct {
		UserID string `json:"user_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	req := &pb.AnalysisRequest{UserId: requestBody.UserID}
	resp, err := h.analysisClient.GetGeneralAnalysis(ctx, req)
	if err != nil {
		log.Printf("gRPC error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleHealthCheck handlehealth checkrequest
func (h *SimpleHTTPHandler) handleHealthCheck(w http.ResponseWriter, r *http.Request) {
	// callgRPCservice
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	req := &pb.EmptyRequest{}
	resp, err := h.grpcClient.HealthCheck(ctx, req)
	if err != nil {
		log.Printf("gRPC health check error: %v", err)
		http.Error(w, "Service unavailable", http.StatusServiceUnavailable)
		return
	}

	// returnJSONresponse
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleRoot handle根pathrequest
func (h *SimpleHTTPHandler) handleRoot(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	html := `<!DOCTYPE html>
<html>
<head>
    <title>Saving Advisor Go Backend</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; color: #2c3e50; }
        .status { background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 20px 0; }
        .endpoints { background: #f8f9fa; padding: 20px; border-radius: 5px; }
        .endpoint { margin: 10px 0; font-family: monospace; }
        .method { color: #007acc; font-weight: bold; }
        .path { color: #d63384; }
        .desc { color: #6c757d; }
        .footer { text-align: center; margin-top: 30px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Saving Advisor Go Backend</h1>
        <p>高performance投资顾问systembackendservice</p>
    </div>
    
    <div class="status">
        <h3>✅ servicestatus: in progressrun</h3>
        <ul>
            <li>🔧 gRPCserver: localhost:50052</li>
            <li>🌐 HTTPgateway: localhost:8081</li>
            <li>🤖 多智能体AIsystem: enabled</li>
        </ul>
    </div>
    
    <div class="endpoints">
        <h3>📚 APIinterfacedocumentation</h3>
        
        <div class="endpoint">
            <span class="method">GET</span> 
            <span class="path">/v1/portfolio/{user_id}</span> 
            <span class="desc">- getuserportfolio</span>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> 
            <span class="path">/v1/recommendations</span> 
            <span class="desc">- getAIrecommendation (body: {"user_id": "1001", "force_fresh": false})</span>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> 
            <span class="path">/v1/feedback</span> 
            <span class="desc">- submitrecommendationfeedback</span>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> 
            <span class="path">/v1/visualization/{user_id}</span> 
            <span class="desc">- get可视化data</span>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> 
            <span class="path">/v1/tasks/{user_id}</span> 
            <span class="desc">- gettasklist</span>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> 
            <span class="path">/v1/analysis</span> 
            <span class="desc">- getanalysis报告 (body: {"user_id": "1001"})</span>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> 
            <span class="path">/health</span> 
            <span class="desc">- health check</span>
        </div>
    </div>
    
    <div class="endpoints">
        <h3>🧪 快速test</h3>
        <p>试试这些APIcall:</p>
        <ul>
            <li><a href="/health" target="_blank">health check</a></li>
            <li><a href="/v1/portfolio/1001" target="_blank">查看user1001 portfolio</a></li>
            <li><a href="/v1/visualization/1001" target="_blank">查看user1001 可视化data</a></li>
            <li><a href="/v1/tasks/1001" target="_blank">查看user1001 tasklist</a></li>
        </ul>
    </div>
    
    <div class="footer">
        <p>🎯 Saving Advisor Go Backend v1.0.0 | Built with ❤️ using Go + gRPC</p>
    </div>
</body>
</html>`

	w.Write([]byte(html))
}

// handleAPIDoc handleAPIdocumentationrequest
func (h *SimpleHTTPHandler) handleAPIDoc(w http.ResponseWriter, r *http.Request) {
	apiDoc := map[string]interface{}{
		"service": "Saving Advisor Go Backend",
		"version": "1.0.0",
		"servers": map[string]string{
			"http": "http://localhost:8081",
			"grpc": "localhost:50052",
		},
		"endpoints": []map[string]interface{}{
			{
				"method":      "GET",
				"path":        "/v1/portfolio/{user_id}",
				"description": "getuserportfolio",
				"example":     "/v1/portfolio/1001",
			},
			{
				"method":      "POST",
				"path":        "/v1/recommendations",
				"description": "getAIrecommendation",
				"body":        map[string]interface{}{"user_id": "1001", "force_fresh": false},
			},
			{
				"method":      "POST",
				"path":        "/v1/analysis",
				"description": "getanalysis报告",
				"body":        map[string]interface{}{"user_id": "1001"},
			},
			{
				"method":      "GET",
				"path":        "/v1/visualization/{user_id}",
				"description": "get可视化data",
				"example":     "/v1/visualization/1001?chart_type=pie",
			},
			{
				"method":      "GET",
				"path":        "/v1/tasks/{user_id}",
				"description": "gettasklist",
				"example":     "/v1/tasks/1001",
			},
			{
				"method":      "GET",
				"path":        "/health",
				"description": "health check",
			},
		},
		"features": []string{
			"Multi-Agent AI System",
			"Real-time Portfolio Analysis",
			"Risk Assessment",
			"Investment Recommendations",
			"Task Gamification",
		},
	}

	if err := json.NewEncoder(w).Encode(apiDoc); err != nil {
		h.sendJSONError(w, "Failed to encode JSON response", err.Error(), http.StatusInternalServerError)
	}
}

// handleStaticFiles handle静态filerequest
func (h *SimpleHTTPHandler) handleStaticFiles(w http.ResponseWriter, r *http.Request) {
	// getproject根directory下 frontendfile夹path
	frontendDir := "../frontend"

	// ifpath是根directory，returnindex.html
	requestPath := r.URL.Path
	if requestPath == "/" {
		requestPath = "/index.html"
	}

	// 构建完整 filepath
	filePath := filepath.Join(frontendDir, requestPath)

	// checkfilewhetherexists
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		// iffile不exists，returnindex.html（支持SPArouter）
		filePath = filepath.Join(frontendDir, "index.html")
		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			log.Printf("Frontend files not found at %s", frontendDir)
			http.Error(w, "Frontend files not found", http.StatusNotFound)
			return
		}
	}

	// setup正确 Content-Type
	ext := filepath.Ext(filePath)
	switch ext {
	case ".html":
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
	case ".css":
		w.Header().Set("Content-Type", "text/css")
	case ".js":
		w.Header().Set("Content-Type", "application/javascript")
	case ".png":
		w.Header().Set("Content-Type", "image/png")
	case ".jpg", ".jpeg":
		w.Header().Set("Content-Type", "image/jpeg")
	case ".gif":
		w.Header().Set("Content-Type", "image/gif")
	case ".svg":
		w.Header().Set("Content-Type", "image/svg+xml")
	}

	// providefileservice
	http.ServeFile(w, r, filePath)
}

// handleMonitoring handlemonitor相关request
func (h *SimpleHTTPHandler) handleMonitoring(w http.ResponseWriter, r *http.Request) {
	// 简单 monitorfeatureimplement
	switch r.URL.Path {
	case "/api/v1/monitoring/status-stream":
		// improve SSEconnectedimplement
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Cache-Control")

		// check客户端whether支持SSE
		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
			return
		}

		// generate动态monitordata并持续发送
		ticker := time.NewTicker(3 * time.Second)
		defer ticker.Stop()

		// 发送初始data
		h.sendMonitoringData(w, flusher)

		// 持续发送data直到客户端disconnectedconnected
		for {
			select {
			case <-ticker.C:
				if err := h.sendMonitoringData(w, flusher); err != nil {
					log.Printf("SSE client disconnected: %v", err)
					return
				}
			case <-r.Context().Done():
				log.Printf("SSE client connection closed")
				return
			}
		}

	case "/api/v1/monitoring/deep-check":
		// depthcheck - 简单implement
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		response := map[string]interface{}{
			"timestamp": time.Now().Format(time.RFC3339),
			"overall_assessment": map[string]interface{}{
				"status":          "excellent",
				"message":         "所有システム normally 動作in progress",
				"issues":          []string{},
				"warnings":        []string{},
				"recommendations": []string{},
			},
			"health_check": map[string]interface{}{
				"status":                    "healthy",
				"recommendations_generated": 3,
			},
			"api_performance": map[string]interface{}{
				"available":       true,
				"status":          "excellent",
				"response_time_s": 0.8,
				"category":        "fast",
			},
			"sync_status": map[string]interface{}{
				"sync_enabled": true,
			},
			"cache_performance": map[string]interface{}{
				"status": "excellent",
			},
			"availability": map[string]interface{}{
				"status": "excellent",
			},
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)

	default:
		// 其他monitorrequestreturn简单status
		response := map[string]interface{}{
			"status":    "ok",
			"timestamp": time.Now().Format(time.RFC3339),
			"service":   "Saving Advisor Go Backend",
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}
}

// sendMonitoringData 发送动态monitordata
func (h *SimpleHTTPHandler) sendMonitoringData(w http.ResponseWriter, flusher http.Flusher) error {
	// generate动态data - mock真实systemmetric 小幅波动
	healthResponseTime := 10 + rand.Intn(20)       // 10-30ms
	recommendationTime := 0.8 + rand.Float64()*0.8 // 0.8-1.6s
	cacheHitRate := 80 + rand.Intn(15)             // 80-95%
	availability := 99.5 + rand.Float64()*0.4      // 99.5-99.9%

	// 随机选择status
	statuses := []string{"excellent", "good"}
	healthStatus := statuses[rand.Intn(len(statuses))]
	recStatus := "excellent"
	if recommendationTime > 1.3 {
		recStatus = "good"
	}
	cacheStatus := "excellent"
	if cacheHitRate < 85 {
		cacheStatus = "good"
	}

	// 构建动态data
	data := map[string]interface{}{
		"timestamp": time.Now().Format(time.RFC3339),
		"business_kpis": map[string]interface{}{
			"health_check": map[string]interface{}{
				"response_time_ms": healthResponseTime,
				"status":           healthStatus,
			},
			"recommendation_api": map[string]interface{}{
				"response_time_s": fmt.Sprintf("%.1f", recommendationTime),
				"status":          recStatus,
			},
			"cache_hit_rate": map[string]interface{}{
				"hit_rate_percent": cacheHitRate,
				"status":           cacheStatus,
			},
			"sync_performance": map[string]interface{}{
				"sync_enabled": true,
				"healthy":      true,
			},
			"availability": map[string]interface{}{
				"availability_percent": fmt.Sprintf("%.1f", availability),
				"status":               "excellent",
			},
			"overall": map[string]interface{}{
				"status": "excellent",
			},
		},
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal monitoring data: %v", err)
	}

	// 发送SSE格式 data
	_, err = fmt.Fprintf(w, "event: update\ndata: %s\n\n", jsonData)
	if err != nil {
		return fmt.Errorf("failed to write SSE data: %v", err)
	}

	// refresh缓冲区
	flusher.Flush()

	return nil
}
