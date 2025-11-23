# 🧪 Tests Directory

This directory contains test files for the Saving Advisor System.

## 📋 Available Tests

### ✅ Active Tests

#### `test_shared_services.py`
Tests for core business logic services.

**What it tests:**
- `CoreAnalysisService` - Portfolio analysis functionality
- `CoreRecommendationService` - Recommendation generation
- `CoreAssetService` - Asset management
- Service integration and concurrent access

**Usage:**
```bash
python tests/test_shared_services.py
```

**Status:** ✅ Active - All referenced services exist and are functional

#### `test_microservice_abstraction.py`
Tests for data service factory and abstraction layer.

**What it tests:**
- `DataServiceFactory` initialization and configuration
- Mock data service implementations
- Service singleton behavior
- Error handling and fallback mechanisms
- Performance and resilience

**Usage:**
```bash
pytest tests/test_microservice_abstraction.py -v
```

**Status:** ✅ Active - Updated to remove Mercari references (now only supports MOCK data source)

## 🗑️ Removed Tests

### `test_main.py` (Deleted)
**Reason:** This test file was for FastAPI endpoints using `TestClient`, but the application has been migrated to gRPC architecture. The `app/main.py` is now a gRPC server, not a FastAPI application.

**If you need to test gRPC services:**
- Use gRPC testing tools (e.g., `grpc_testing`)
- Test the REST gateway endpoints (`app/gateway/rest_to_grpc.py`) using FastAPI TestClient
- Test core services directly (as in `test_shared_services.py`)

## 🔧 Running Tests

### Run all tests:
```bash
# Using pytest
pytest tests/ -v

# Run specific test file
pytest tests/test_shared_services.py -v
pytest tests/test_microservice_abstraction.py -v
```

### Run test script directly:
```bash
python tests/test_shared_services.py
```

## 📝 Test Coverage

Current test coverage includes:
- ✅ Core business logic services
- ✅ Data service factory and abstraction
- ✅ Mock data implementations
- ✅ Service integration
- ⚠️ gRPC services (not yet covered - needs new tests)
- ⚠️ REST gateway endpoints (not yet covered - needs new tests)

## 🚀 Future Improvements

1. **Add gRPC Service Tests:**
   - Test `AnalysisService` gRPC implementation
   - Test `SavingAdvisorService` gRPC implementation
   - Use `grpc_testing` library

2. **Add REST Gateway Tests:**
   - Test REST to gRPC translation
   - Test error handling and response formatting
   - Use FastAPI `TestClient` on `app/gateway/rest_to_grpc.py`

3. **Add Integration Tests:**
   - End-to-end tests for complete user flows
   - Database integration tests
   - Redis cache tests

## 📚 Related Documentation

- **[README.md](../README.md)** - Main project documentation
- **Batch processing tests** - Use `bash scripts/batch_processing.sh` to test batch processing functionality

---

**Last Updated:** 2025-01-12  
**Maintained by:** Saving Advisor Team

