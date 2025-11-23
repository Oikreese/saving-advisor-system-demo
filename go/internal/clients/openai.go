package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

// OpenAIClient OpenAI API客户端
// 对应Pythonversion OpenAI客户端
type OpenAIClient struct {
	apiKey  string
	client  *http.Client
	baseURL string
}

// OpenAIRequest OpenAI APIrequest结构
type OpenAIRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	MaxTokens   int       `json:"max_tokens"`
	Temperature float32   `json:"temperature,omitempty"`
}

// Message 消息结构
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// OpenAIResponse OpenAI APIresponse结构
type OpenAIResponse struct {
	ID      string   `json:"id"`
	Object  string   `json:"object"`
	Created int64    `json:"created"`
	Model   string   `json:"model"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}

// Choice response选择
type Choice struct {
	Index   int     `json:"index"`
	Message Message `json:"message"`
	Finish  string  `json:"finish_reason"`
}

// Usage usestatistics
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// NewOpenAIClient createnew OpenAI客户端
func NewOpenAIClient() *OpenAIClient {
	return &OpenAIClient{
		apiKey: os.Getenv("OPENAI_API_KEY"),
		client: &http.Client{
			Timeout: 60 * time.Second,
		},
		baseURL: "https://api.openai.com/v1",
	}
}

// NewOpenAIClientWithConfig useconfigurecreateOpenAI客户端
func NewOpenAIClientWithConfig(apiKey, baseURL string, timeout time.Duration) *OpenAIClient {
	return &OpenAIClient{
		apiKey: apiKey,
		client: &http.Client{
			Timeout: timeout,
		},
		baseURL: baseURL,
	}
}

// GenerateAnalysis generateanalysis报告
// 对应Pythonversion generate_analysismethod
func (c *OpenAIClient) GenerateAnalysis(ctx context.Context, prompt string) (string, error) {
	request := OpenAIRequest{
		Model:       "gpt-4",
		MaxTokens:   1000,
		Temperature: 0.7,
		Messages: []Message{
			{
				Role:    "user",
				Content: prompt,
			},
		},
	}

	response, err := c.makeRequest(ctx, "/chat/completions", request)
	if err != nil {
		return "", fmt.Errorf("failed to generate analysis: %w", err)
	}

	if len(response.Choices) == 0 {
		return "", fmt.Errorf("no response choices received")
	}

	return response.Choices[0].Message.Content, nil
}

// GenerateRecommendation generaterecommendation
func (c *OpenAIClient) GenerateRecommendation(ctx context.Context, agentName, prompt string) (string, error) {
	// 根据不同 智能体adjusttip词
	systemPrompt := c.getAgentSystemPrompt(agentName)

	request := OpenAIRequest{
		Model:       "gpt-4",
		MaxTokens:   1500,
		Temperature: 0.8,
		Messages: []Message{
			{
				Role:    "system",
				Content: systemPrompt,
			},
			{
				Role:    "user",
				Content: prompt,
			},
		},
	}

	response, err := c.makeRequest(ctx, "/chat/completions", request)
	if err != nil {
		return "", fmt.Errorf("failed to generate recommendation for agent %s: %w", agentName, err)
	}

	if len(response.Choices) == 0 {
		return "", fmt.Errorf("no response choices received")
	}

	return response.Choices[0].Message.Content, nil
}

// getAgentSystemPrompt get不同智能体 systemtip词
func (c *OpenAIClient) getAgentSystemPrompt(agentName string) string {
	prompts := map[string]string{
		"PortfolioAnalysisAgent": "你是一个专业 portfolioanalysis师。请analysisuser assetconfigure并provideoptimize建议。",
		"RiskAssessmentAgent":    "你是一个risk评估专家。请评估portfolio risk水平并providerisk管理建议。",
		"MarketAnalysisAgent":    "你是一个市场analysis专家。请analysiscurrent市场trend并provide投资时机建议。",
	}

	if prompt, exists := prompts[agentName]; exists {
		return prompt
	}

	return "你是一个专业 金融顾问，请provide专业 投资建议。"
}

// makeRequest 发送request到OpenAI API
func (c *OpenAIClient) makeRequest(ctx context.Context, endpoint string, request OpenAIRequest) (*OpenAIResponse, error) {
	if c.apiKey == "" {
		return nil, fmt.Errorf("OpenAI API key is not set")
	}

	jsonData, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+endpoint, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("OpenAI API returned status code %d", resp.StatusCode)
	}

	var response OpenAIResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &response, nil
}

// ValidateAPIKey validateAPI密钥whethervalid
func (c *OpenAIClient) ValidateAPIKey(ctx context.Context) error {
	request := OpenAIRequest{
		Model:     "gpt-3.5-turbo",
		MaxTokens: 5,
		Messages: []Message{
			{
				Role:    "user",
				Content: "Hello",
			},
		},
	}

	_, err := c.makeRequest(ctx, "/chat/completions", request)
	return err
}
