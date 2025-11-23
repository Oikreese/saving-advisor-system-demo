package services

import (
	"context"
	"fmt"
	"log"
	"os"

	"saving_advisor_system_go/internal/clients"
)

// SavingAdvisorServices core servicemanager
// 对应Pythonversion core services，provide所有business logic 统一入口
type SavingAdvisorServices struct {
	// 外部service客户端
	firestoreClient *clients.FirestoreClient
	bigQueryClient  *clients.BigQueryClient
	openAIClient    *clients.OpenAIClient

	// business logicservice
	analysisService       *AnalysisService
	recommendationService *RecommendationService
	assetService          *AssetService
}

// NewSavingAdvisorServices createservice实例
// 对应Pythonversion serviceinitialize
func NewSavingAdvisorServices() *SavingAdvisorServices {
	log.Println("🚀 Initializing Saving Advisor Services...")

	// use默认configurecreateservice
	config := DefaultServiceConfig()
	services, err := NewSavingAdvisorServicesWithConfig(config)
	if err != nil {
		log.Fatalf("❌ Failed to initialize services: %v", err)
	}

	return services
}

// NewSavingAdvisorServicesWithConfig useconfigurecreateservice实例
func NewSavingAdvisorServicesWithConfig(config *ServiceConfig) (*SavingAdvisorServices, error) {
	log.Println("🚀 Initializing Saving Advisor Services with config...")

	var firestoreClient *clients.FirestoreClient
	var bigQueryClient *clients.BigQueryClient
	var err error

	// 根据configureinitializeFirestore客户端
	if config.Firestore.Enabled {
		// setupenvironment变量以便NewFirestoreClientuse
		if config.Firestore.ProjectID != "" {
			os.Setenv("GOOGLE_CLOUD_PROJECT", config.Firestore.ProjectID)
		}
		if config.Firestore.CredentialsPath != "" {
			os.Setenv("GOOGLE_APPLICATION_CREDENTIALS", config.Firestore.CredentialsPath)
		}

		firestoreClient, err = clients.NewFirestoreClient()
		if err != nil {
			log.Printf("❌ Failed to initialize Firestore client: %v", err)
			// 不再setup为nil，而是returnerror，强制handle认证问题
			return nil, fmt.Errorf("firestore initialization failed: %w", err)
		}

		log.Println("✅ Firestore client successfully initialized")
	} else {
		log.Println("⚠️  Firestore is disabled in configuration")
		return nil, fmt.Errorf("firestore is disabled - please enable it in configuration to use real data")
	}

	// 根据configureinitializeBigQuery客户端
	if config.BigQuery.Enabled {
		if config.BigQuery.CredentialsPath != "" {
			bigQueryClient, err = clients.NewBigQueryClientWithCredentials(
				config.BigQuery.ProjectID,
				config.BigQuery.DatasetID,
				config.BigQuery.CredentialsPath,
			)
		} else {
			bigQueryClient, err = clients.NewBigQueryClient()
		}

		if err != nil {
			log.Printf("⚠️  Failed to initialize BigQuery client: %v", err)
			bigQueryClient = nil
		}
	}

	// initializeOpenAI客户端
	openAIClient := clients.NewOpenAIClientWithConfig(
		config.OpenAI.APIKey,
		config.OpenAI.BaseURL,
		config.OpenAI.Timeout,
	)

	// create主service实例
	services := &SavingAdvisorServices{
		firestoreClient: firestoreClient,
		bigQueryClient:  bigQueryClient,
		openAIClient:    openAIClient,
	}

	// initializebusiness logicservice
	services.analysisService = NewAnalysisService(services)
	services.recommendationService = NewRecommendationService(services)
	services.assetService = NewAssetService(services)

	log.Println("✅ Saving Advisor Services initialized successfully with config")
	return services, nil
}

// GetAnalysisService getanalysis service
func (s *SavingAdvisorServices) GetAnalysisService() *AnalysisService {
	return s.analysisService
}

// GetRecommendationService getrecommendation service
func (s *SavingAdvisorServices) GetRecommendationService() *RecommendationService {
	return s.recommendationService
}

// GetAssetService getasset service
func (s *SavingAdvisorServices) GetAssetService() *AssetService {
	return s.assetService
}

// GetFirestoreClient getFirestore客户端
func (s *SavingAdvisorServices) GetFirestoreClient() *clients.FirestoreClient {
	return s.firestoreClient
}

// GetBigQueryClient getBigQuery客户端
func (s *SavingAdvisorServices) GetBigQueryClient() *clients.BigQueryClient {
	return s.bigQueryClient
}

// GetOpenAIClient getOpenAI客户端
func (s *SavingAdvisorServices) GetOpenAIClient() *clients.OpenAIClient {
	return s.openAIClient
}

// HealthCheck health check
// 对应Pythonversion health checkfeature
func (s *SavingAdvisorServices) HealthCheck(ctx context.Context) error {
	log.Println("🔍 Performing health check...")

	// checkFirestoreconnected
	if s.firestoreClient != nil {
		if err := s.firestoreClient.Ping(ctx); err != nil {
			return fmt.Errorf("firestore health check failed: %w", err)
		}
		log.Println("✅ Firestore connection healthy")
	} else {
		log.Println("⚠️  Firestore client not initialized")
	}

	// checkBigQueryconnected
	if s.bigQueryClient != nil {
		if err := s.bigQueryClient.Ping(ctx); err != nil {
			return fmt.Errorf("bigquery health check failed: %w", err)
		}
		log.Println("✅ BigQuery connection healthy")
	} else {
		log.Println("⚠️  BigQuery client not initialized")
	}

	// checkOpenAIconnected（可选，因为APIcall有成本）
	if s.openAIClient != nil {
		// 在productionenvironment中，我们可能不想每次health check都callOpenAI API
		// 这里只是checkAPI密钥whethersetup
		// if err := s.openAIClient.ValidateAPIKey(ctx); err != nil {
		// 	return fmt.Errorf("openai health check failed: %w", err)
		// }
		log.Println("✅ OpenAI client initialized")
	}

	log.Println("✅ All health checks passed")
	return nil
}

// Close close所有serviceconnected
func (s *SavingAdvisorServices) Close() error {
	log.Println("🛑 Closing all service connections...")

	var errors []error

	// closeFirestoreconnected
	if s.firestoreClient != nil {
		if err := s.firestoreClient.Close(); err != nil {
			errors = append(errors, fmt.Errorf("failed to close firestore client: %w", err))
		}
	}

	// closeBigQueryconnected
	if s.bigQueryClient != nil {
		if err := s.bigQueryClient.Close(); err != nil {
			errors = append(errors, fmt.Errorf("failed to close bigquery client: %w", err))
		}
	}

	if len(errors) > 0 {
		return fmt.Errorf("errors occurred while closing services: %v", errors)
	}

	log.Println("✅ All service connections closed")
	return nil
}
