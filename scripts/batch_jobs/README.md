# 📊 Batch Processing Task System

Open-source replacement for BigQuery batch processing

## 🎯 System Architecture

```
PostgreSQL (Database)
    ↓ SQL queries + aggregation
Python analysis scripts (Pandas/NumPy)
    ↓ Celery scheduled tasks
Redis (Task queue + result cache)
    ↓ API queries
FastAPI + Frontend
```

## 📋 Batch Processing Task List

### 1. User Behavior Analysis (`user_behavior_analysis.py`)
**Schedule**: Daily at 2:00 AM  
**Features**:
- Active user statistics
- Transaction behavior analysis
- Asset change analysis
- User engagement analysis

**Manual execution**:
```bash
python scripts/batch_jobs/user_behavior_analysis.py
```

### 2. Recommendation Performance Analysis (`recommendation_analysis.py`)
**Schedule**: Every 4 hours  
**Features**:
- Recommendation acceptance rate analysis
- AI session statistics
- Recommendation quality scoring

**Manual execution**:
```bash
python scripts/batch_jobs/recommendation_analysis.py
```

### 3. Market Trends Analysis (`market_trend_analysis.py`)
**Schedule**: Daily at 3:00 AM  
**Features**:
- Asset type trends
- Transaction volume trends
- Price trend analysis

**Manual execution**:
```bash
python scripts/batch_jobs/market_trend_analysis.py
```

## 🚀 Quick Start

### Method 1: Using Celery (Recommended)

#### 1. Ensure Redis is running
```bash
# Check Redis
redis-cli ping

# Or start Docker Redis
docker-compose up -d redis
```

#### 2. Start batch processing system
Use the unified batch processing management script:

```bash
bash scripts/batch_processing.sh
```

Select option 7 to start the complete system (Worker + Beat + Flower) with one click, or select separately:
- Option 1: Start Celery Worker
- Option 2 or 3: Start Celery Beat (foreground/background)
- Option 4 or 5: Start Flower monitoring (foreground/background)

#### 4. Verify tasks
```bash
# Check Celery status
celery -A app.tasks.batch_tasks inspect active

# Check scheduled tasks
celery -A app.tasks.batch_tasks inspect scheduled
```

### Method 2: Docker Compose

Celery services are already configured in `docker-compose.yml` (if needed):

```yaml
celery-worker:
  build: .
  command: celery -A app.tasks.batch_tasks worker --loglevel=info
  depends_on:
    - redis
    - postgres

celery-beat:
  build: .
  command: celery -A app.tasks.batch_tasks beat --loglevel=info
  depends_on:
    - redis
    - postgres
```

Start:
```bash
docker-compose up celery-worker celery-beat
```

### Method 3: Manual Execution (for testing)

Use the unified script:

```bash
bash scripts/batch_processing.sh
# Select option 6: Manually run all batch jobs
```

Or run individually:

```bash
python scripts/batch_jobs/user_behavior_analysis.py
python scripts/batch_jobs/recommendation_analysis.py
python scripts/batch_jobs/market_trend_analysis.py
```

## 📊 Accessing Analysis Results

### Get results from Redis

```python
import redis
import json

# Connect to Redis
r = redis.from_url('redis://localhost:6379', decode_responses=True)

# Get latest user behavior analysis
result = r.get('batch_analysis:user_behavior_analysis:latest')
data = json.loads(result)

print(f"Active users: {data['active_users']['count']}")
print(f"Analysis time: {data['analyzed_at']}")
```

### Access via API

```bash
# Get latest analysis results (API endpoint to be implemented)
curl http://localhost:8080/api/v1/analytics/batch/user-behavior
```

## 📅 Scheduled Task Configuration

Current configuration (in `app/tasks/batch_tasks.py`):

| Task | Schedule | Cron Expression |
|------|---------|----------------|
| User behavior analysis | Daily at 2:00 AM | `0 2 * * *` |
| Recommendation performance | Every 4 hours | `0 */4 * * *` |
| Market trends analysis | Daily at 3:00 AM | `0 3 * * *` |
| User segmentation | Every Monday at 4:00 AM | `0 4 * * 1` |

### Modify Schedule

Edit `app/tasks/batch_tasks.py`:

```python
# Example: Change to every 2 hours
sender.add_periodic_task(
    crontab(minute=0, hour='*/2'),  # Modify here
    analyze_recommendation_performance_task.s(),
)
```

## 🔍 Monitoring and Logs

### View Logs

```bash
# Celery Worker logs
tail -f logs/celery_worker.log

# Celery Beat logs
tail -f logs/celery_beat.log

# Application main logs
tail -f logs/app.log
```

### Monitor Task Execution

```bash
# View active tasks
celery -A app.tasks.batch_tasks inspect active

# View registered tasks
celery -A app.tasks.batch_tasks inspect registered

# View worker statistics
celery -A app.tasks.batch_tasks inspect stats
```

### Using Flower (Web Monitoring Interface)

```bash
# Install Flower
pip install flower

# Start Flower
celery -A app.tasks.batch_tasks flower

# Access at http://localhost:5555
```

## 🛠️ Development Guide

### Adding New Batch Processing Tasks

1. **Create analysis script**:
```python
# scripts/batch_jobs/my_new_analysis.py
async def my_analysis():
    async with get_db_session() as session:
        # Implement analysis logic
        pass
```

2. **Add Celery task**:
```python
# app/tasks/batch_tasks.py
@celery_app.task(name='batch.my_new_analysis')
def my_new_analysis_task(self):
    from scripts.batch_jobs.my_new_analysis import my_analysis
    return asyncio.run(my_analysis())
```

3. **Configure scheduled execution**:
```python
sender.add_periodic_task(
    crontab(hour=5, minute=0),  # Daily at 5:00 AM
    my_new_analysis_task.s(),
)
```

### Testing Tasks

```python
# Test script
python scripts/batch_jobs/my_new_analysis.py

# Test Celery task
from app.tasks.batch_tasks import my_new_analysis_task
result = my_new_analysis_task.delay()
print(result.get(timeout=60))
```

## 🐛 Troubleshooting

### Issue: Celery worker cannot start
**Solution**:
```bash
# Check Redis connection
redis-cli ping

# Check environment variables
echo $REDIS_URL
```

### Issue: Task execution fails
**Solution**:
```bash
# View detailed logs
celery -A app.tasks.batch_tasks inspect active

# Check database connection
psql -U postgres -d saving_advisor -c "SELECT 1"
```

### Issue: Scheduled tasks not executing
**Solution**:
```bash
# Ensure Celery Beat is running
ps aux | grep celery

# Check schedule status
celery -A app.tasks.batch_tasks inspect scheduled
```

## 📈 Performance Optimization

### Database Indexes

```sql
-- Add indexes for common queries
CREATE INDEX idx_transactions_created ON transactions(created);
CREATE INDEX idx_transactions_buyer_id ON transactions(buyer_id);
CREATE INDEX idx_daily_balance_date ON daily_user_balance(date);
CREATE INDEX idx_ai_sessions_created ON ai_sessions(created_at);
```

### Batch Processing

```python
# Process large amounts of data in batches
BATCH_SIZE = 1000
for offset in range(0, total, BATCH_SIZE):
    batch = await get_batch(offset, BATCH_SIZE)
    await process_batch(batch)
```

### Caching Strategy
- User behavior analysis results cached for 24 hours
- Recommendation performance analysis results cached for 6 hours
- Market trends analysis results cached for 24 hours

## 🔗 Related Documentation

- [README.md](../../README.md) - Main project documentation
- [Celery Official Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/docs/)

---

**Created**: 2025-01-12  
**Status**: ✅ Production Ready  
**Replaces**: BigQuery Batch Processing
