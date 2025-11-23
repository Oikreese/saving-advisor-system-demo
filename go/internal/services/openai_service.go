package services

import (
	"context"
	"fmt"

	openai "github.com/sashabaranov/go-openai"

	"saving_advisor_system_go/internal/config"
)

// OpenAIService handles OpenAI API interactions
type OpenAIService struct {
	client *openai.Client
	model  string
}

// NewOpenAIService creates a new OpenAI service
func NewOpenAIService(cfg *config.Config) *OpenAIService {
	client := openai.NewClient(cfg.OpenAIAPIKey)
	return &OpenAIService{
		client: client,
		model:  cfg.OpenAIModel,
	}
}

// ChatCompletionRequest represents a chat completion request
type ChatCompletionRequest struct {
	SystemPrompt string
	UserPrompt   string
	Temperature  float32
	MaxTokens    int
}

// ChatCompletionResponse represents a chat completion response
type ChatCompletionResponse struct {
	Content       string
	TokensUsed    int
	FinishReason  string
}

// CreateChatCompletion sends a chat completion request to OpenAI
func (s *OpenAIService) CreateChatCompletion(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error) {
	messages := []openai.ChatCompletionMessage{
		{
			Role:    openai.ChatMessageRoleSystem,
			Content: req.SystemPrompt,
		},
		{
			Role:    openai.ChatMessageRoleUser,
			Content: req.UserPrompt,
		},
	}

	temperature := req.Temperature
	if temperature == 0 {
		temperature = 0.7
	}

	maxTokens := req.MaxTokens
	if maxTokens == 0 {
		maxTokens = 2000
	}

	resp, err := s.client.CreateChatCompletion(
		ctx,
		openai.ChatCompletionRequest{
			Model:       s.model,
			Messages:    messages,
			Temperature: temperature,
			MaxTokens:   maxTokens,
		},
	)

	if err != nil {
		return nil, fmt.Errorf("chat completion error: %w", err)
	}

	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("no completion choices returned")
	}

	return &ChatCompletionResponse{
		Content:      resp.Choices[0].Message.Content,
		TokensUsed:   resp.Usage.TotalTokens,
		FinishReason: string(resp.Choices[0].FinishReason),
	}, nil
}

// CreateChatCompletionWithJSON sends a chat completion request expecting JSON response
func (s *OpenAIService) CreateChatCompletionWithJSON(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error) {
	messages := []openai.ChatCompletionMessage{
		{
			Role:    openai.ChatMessageRoleSystem,
			Content: req.SystemPrompt + "\n\nPlease respond with valid JSON only.",
		},
		{
			Role:    openai.ChatMessageRoleUser,
			Content: req.UserPrompt,
		},
	}

	temperature := req.Temperature
	if temperature == 0 {
		temperature = 0.3 // Lower temperature for more consistent JSON
	}

	maxTokens := req.MaxTokens
	if maxTokens == 0 {
		maxTokens = 2000
	}

	resp, err := s.client.CreateChatCompletion(
		ctx,
		openai.ChatCompletionRequest{
			Model:        s.model,
			Messages:     messages,
			Temperature:  temperature,
			MaxTokens:    maxTokens,
			ResponseFormat: &openai.ChatCompletionResponseFormat{
				Type: openai.ChatCompletionResponseFormatTypeJSONObject,
			},
		},
	)

	if err != nil {
		return nil, fmt.Errorf("chat completion error: %w", err)
	}

	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("no completion choices returned")
	}

	return &ChatCompletionResponse{
		Content:      resp.Choices[0].Message.Content,
		TokensUsed:   resp.Usage.TotalTokens,
		FinishReason: string(resp.Choices[0].FinishReason),
	}, nil
}

