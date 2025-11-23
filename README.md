# Saving Advisor System

An AI-powered financial advisory system that helps users optimize their asset allocation and financial decisions using multi-agent AI analysis.

## Features

- Multi-Agent AI System: Specialized AI agents for different asset types (Points, Earnings, Crypto, GIGA, Stablecoin)
- Asset Portfolio Management: Track and manage various asset types with real-time updates
- Smart Recommendations: AI-generated personalized financial recommendations based on portfolio analysis
- Data Analytics: Comprehensive user behavior and market trend analysis with batch processing
- Interactive Visualization: Charts and graphs for portfolio visualization
- Task Management: Personalized financial tasks and goals
- Batch Processing: Automated analytics using Celery for scheduled tasks
- gRPC Architecture: High-performance microservices communication

## Tech Stack

### Backend
- Python 3.11+: Main backend with gRPC services
- Go: High-performance alternative backend
- Database: PostgreSQL (production) / SQLite (development) - configurable via `DB_DRIVER`
- Redis: Caching and task queue
- SQLAlchemy: ORM for database operations (supports both PostgreSQL and SQLite)
- OpenAI GPT-4: AI-powered recommendations
- Celery: Asynchronous task processing
- gRPC: Inter-service communication

### Frontend
- Pure HTML/CSS/JavaScript: No framework dependencies
- Bootstrap 5: Responsive UI components
- Chart.js: Data visualization

## Project Structure

```
saving_advisor_system/
├── app/
│   ├── api/                  # REST API endpoints (gateway)
│   ├── agents/               # Multi-agent AI system
│   ├── core/                 # Core configuration and logging
│   ├── db/                   # Database models and repositories
│   ├── gateway/              # REST to gRPC gateway
│   ├── grpc_services/        # gRPC service implementations
│   │   ├── generated/        # Generated gRPC code
│   │   ├── protos/           # Protocol buffer definitions
│   │   └── services/         # gRPC service implementations
│   ├── models/               # Pydantic models
│   ├── services/             # Business logic services
│   │   ├── core/             # Core business services
│   │   ├── data/             # Data access layer
│   │   └── utils/            # Utility services
│   ├── tasks/                # Celery task definitions
│   └── main.py               # gRPC server entry point
├── go/                       # Go backend (high performance)
│   ├── cmd/server/           # Go server entry point
│   ├── internal/             # Internal packages
│   └── api/proto/            # Generated Go gRPC code
├── frontend/                 # Frontend assets
│   ├── index.html            # Main HTML file
│   ├── js/                   # JavaScript files
│   └── image/                # Image assets
├── scripts/                  # Utility scripts
│   ├── batch_jobs/           # Batch processing scripts
│   ├── generate_sample_data.py
│   └── start_services.sh
├── tests/                    # Test suite
├── docker-compose.yml        # Docker configuration (Python - main)
├── docker-compose.go.yml     # Docker configuration (Go - optional)
├── Dockerfile                # Docker image definition (Python)
├── Dockerfile.go             # Docker image definition (Go - optional)
├── requirements.txt          # Python dependencies
└── env.example                # Environment variables template
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Database: 
  - **SQLite** (default, no setup required) - for quick start and development
  - **PostgreSQL 14+** (optional) - for production and full features
- Redis 7+ (optional, for caching and task queue)
- OpenAI API Key (required)
- Docker and Docker Compose (optional, for containerized deployment)

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/saving_advisor_system.git
cd saving_advisor_system
```

#### 2. Install Python Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended)
pip install uv
uv pip install -r requirements.txt
```

#### 3. Set Up Environment Variables

```bash
# Copy the example environment file
cp env.example .env

# Edit .env and configure the following required variables:
# - OPENAI_API_KEY: Your OpenAI API key (required)
# - DB_DRIVER: "sqlite" for development or "postgres" for production
# - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME: Database credentials (if using postgres)
# - REDIS_URL: Redis connection URL (default: redis://localhost:6379)
```

#### 4. Database Setup

**Option A: SQLite (Quick Start for Development)**

```bash
# In .env file, set:
DB_DRIVER=sqlite
```

**Option B: PostgreSQL (Recommended for Full Features)**

```bash
# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql

# Or using Docker
docker-compose up -d postgres

# In .env file, set:
DB_DRIVER=postgres
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=saving_advisor
```

#### 5. Initialize Database with Sample Data

```bash
# Generate sample data (50 users, assets, transactions, etc.)
python3 scripts/generate_sample_data.py
```

#### 6. Start Services

**Option 1: Using Startup Script (Recommended, Easiest)**

```bash
# Run the startup script, which provides an interactive menu
bash scripts/start_services.sh
```

The script will check port availability and provide the following options:
- Start gRPC server only (port 50051)
- Start REST gateway only (port 8080)
- Start both services (requires different terminal windows)

**Option 2: Manual Startup (Step-by-step)**

**Start gRPC Server (Terminal 1):**

```bash
# Set PYTHONPATH (path to gRPC generated code)
export PYTHONPATH="$PYTHONPATH:$(pwd)/app/grpc_services/generated"

# Start gRPC server (default port: 50051)
python3 app/main.py
```

**Start REST Gateway (Terminal 2, open a new terminal window):**

```bash
# Start REST to gRPC gateway (default port: 8080)
python3 start_web_server.py
```

**Option 3: Using Docker Compose (Full Containerization)**

See the "Using Docker Compose" section below.

#### 7. Access the Application

- Frontend: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- gRPC Server: localhost:50051

### Using Docker Compose

**Using Docker Compose to start all services with one command (Recommended for production):**

```bash
# 1. Configure environment variables
# Copy the example environment file
cp env.example .env
# Edit .env with your settings (especially OPENAI_API_KEY)

# 2. Start all services (including PostgreSQL, Redis, gRPC server, REST gateway, etc.)
docker-compose up -d

# 3. Generate sample data (run inside container or locally)
python scripts/generate_sample_data.py

# 4. View logs
docker-compose logs -f

# 5. Stop all services
docker-compose down
```

**Services included in Docker Compose:**
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- gRPC server (port 50051)
- REST gateway (port 8080)
- Celery Worker (batch processing tasks)
- Celery Beat (scheduled tasks scheduler)
- Flower monitoring interface (port 5555, optional)

**Note:** For Go backend (high-performance alternative), use `docker-compose -f docker-compose.go.yml up`

## Configuration

### Required Environment Variables

```env
# OpenAI API (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DB_DRIVER=sqlite  # or "postgres" for production
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=saving_advisor

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Server Ports
SERVER_PORT=50051    # gRPC server port
GATEWAY_PORT=8080   # REST gateway port
```

**Note:** Copy `env.example` to `.env` and update the values as needed:
```bash
cp env.example .env
```

### Optional Configuration

```env
# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Security
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI Model
OPENAI_MODEL=gpt-4

# Feature Flags
ENABLE_ANALYTICS=true
ENABLE_ANALYTICS_SYNC=true
```

## Running Batch Processing (Optional)

The system includes batch processing capabilities for analytics using Celery.

### Quick Start (Unified Script)

Use the unified batch processing management script:

```bash
# Interactive menu for all batch processing operations
bash scripts/batch_processing.sh
```

**Available options:**
- Start Celery Worker (foreground/background)
- Start Celery Beat scheduler (foreground/background)
- Start Flower monitoring interface (foreground/background)
- Manually run all batch jobs
- Start complete batch processing system (all services)
- Check service status
- Stop all batch processing services

### Manual Commands

All batch processing operations are now managed through the unified script. The old individual scripts have been removed in favor of the unified management interface.

### What is Batch Processing?

Batch processing is used for:
- **User behavior analysis** - Daily analysis of user activity patterns
- **Recommendation performance** - Track how well recommendations perform
- **Market trends analysis** - Analyze market trends and patterns
- **User segmentation** - Weekly user segmentation analysis

**Note:** Batch processing requires Redis to be running. It's optional and only needed for analytics features.

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_shared_services.py -v

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Port Management

If you encounter port conflicts:

```bash
# Check port usage
bash scripts/check_port.sh 8080

# Kill process on port
bash scripts/kill_port.sh 8080
```

## API Usage

### REST API Endpoints

The REST gateway provides the following endpoints:

**Assets:**
- `GET /api/v1/assets/portfolio/{user_id}` - Get user portfolio

**Analysis:**
- `GET /api/v1/analysis/general/{user_id}` - Get general portfolio analysis
- `GET /api/v1/analysis/enhanced-portfolio/{user_id}` - Get enhanced portfolio analysis
- `GET /api/v1/analysis/user-profile/{user_id}` - Get user profile analysis
- `GET /api/v1/analysis/general-grpc/{user_id}` - Get analysis via gRPC (alternative endpoint)

**Recommendations:**
- `GET /api/v1/tasks/recommendations/preview/{user_id}` - Get recommendations preview
- `GET /api/v1/recommendations-firestore-primary/analyze/{user_id}` - Analyze user portfolio and get recommendations
- `POST /api/v1/recommendations/feedback` - Submit recommendation feedback
- `POST /api/v1/recommendations/regenerate` - Regenerate recommendation

**Visualization:**
- `GET /api/v1/visualization/pie-chart/{user_id}` - Get pie chart visualization data
- `GET /api/v1/visualization/{user_id}` - Get visualization data (supports chart_type parameter)

**Tasks:**
- `GET /api/v1/tasks/recommendations/preview/{user_id}` - Get recommendations preview
- `POST /api/v1/tasks/comprehensive/{user_id}` - Get comprehensive recommendations
- `POST /api/v1/tasks/monthly/{user_id}` - Get monthly tasks

**Health & Monitoring:**
- `GET /api/v1/health` - API health check
- `GET /api/v1/monitoring/status-stream` - Real-time system monitoring (SSE)

**Note:** For a complete list of all available endpoints, visit http://localhost:8080/docs when the server is running.

### gRPC Services

The gRPC server provides:

- `SavingAdvisorService`: Main service for portfolio, recommendations, analysis
- `AnalysisService`: Portfolio analysis service

Use gRPC clients or tools like `grpcurl` to interact with the gRPC server.

## Troubleshooting

### Common Issues

**Database Connection Failed:**
```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -U postgres -d saving_advisor -c "SELECT 1"
```

**Redis Connection Failed:**
```bash
# Check Redis is running
redis-cli ping
```

**Port Already in Use:**
```bash
# Check and kill process on port
bash scripts/check_port.sh 8080
bash scripts/kill_port.sh 8080
```

**Module Import Errors:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="$PYTHONPATH:$(pwd)/app/grpc_services/generated"
```

## Additional Resources

- Scripts Documentation: `scripts/README.md` - Utility scripts and batch processing
- Tests Documentation: `tests/README.md` - Test suite documentation

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For support, please:
1. Review this README and check the troubleshooting section
2. Review existing GitHub issues
3. Open a new issue with detailed information


