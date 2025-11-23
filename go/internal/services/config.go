package services

import (
	"time"
)

// ServiceConfig serviceconfigure结构
type ServiceConfig struct {
	Firestore FirestoreConfig `json:"firestore"`
	BigQuery  BigQueryConfig  `json:"bigquery"`
	OpenAI    OpenAIConfig    `json:"openai"`
	Server    ServerConfig    `json:"server"`
}

// FirestoreConfig Firestoreconfigure
type FirestoreConfig struct {
	Enabled         bool   `json:"enabled"`
	ProjectID       string `json:"project_id"`
	CredentialsPath string `json:"credentials_path,omitempty"`
}

// BigQueryConfig BigQueryconfigure
type BigQueryConfig struct {
	Enabled         bool   `json:"enabled"`
	ProjectID       string `json:"project_id"`
	DatasetID       string `json:"dataset_id"`
	CredentialsPath string `json:"credentials_path,omitempty"`
}

// OpenAIConfig OpenAIconfigure
type OpenAIConfig struct {
	APIKey  string        `json:"api_key"`
	BaseURL string        `json:"base_url"`
	Timeout time.Duration `json:"timeout"`
}

// ServerConfig serverconfigure
type ServerConfig struct {
	HTTPPort string        `json:"http_port"`
	GRPCPort string        `json:"grpc_port"`
	Timeout  time.Duration `json:"timeout"`
}

// DefaultServiceConfig return默认configure
func DefaultServiceConfig() *ServiceConfig {
	return &ServiceConfig{
		Firestore: FirestoreConfig{
			Enabled:   true,                            // enabledFirestore，andPythonbackend保持一致
			ProjectID: "merpay-credit-score-in-jp-dev", // useandPython相同 projectID
		},
		BigQuery: BigQueryConfig{
			Enabled:   false, // 默认close，avoidingdevelopmentenvironmentconfigure问题
			ProjectID: "your-project-id",
			DatasetID: "saving_advisor",
		},
		OpenAI: OpenAIConfig{
			APIKey:  "", // fromenvironment变量get
			BaseURL: "https://api.openai.com/v1",
			Timeout: 60 * time.Second,
		},
		Server: ServerConfig{
			HTTPPort: ":8081",
			GRPCPort: ":50052",
			Timeout:  30 * time.Second,
		},
	}
}
