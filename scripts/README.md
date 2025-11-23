# 📜 Scripts Directory

This directory contains utility scripts for the Saving Advisor System.

## 🔧 Available Scripts

### 1. Service Management

#### `start_services.sh`
Unified startup script for starting gRPC server and REST gateway.

**Usage:**
```bash
bash scripts/start_services.sh
```

**Features:**
- Automatically checks port availability
- Supports starting gRPC server or REST gateway separately
- Automatically reads port settings from configuration file

#### `check_port.sh`
Check port availability and configuration.

**Usage:**
```bash
# Check configured ports (gRPC and REST gateway)
bash scripts/check_port.sh

# Check specified port
bash scripts/check_port.sh 8080
```

**Features:**
- Validates port configuration (gRPC and REST gateway use different ports)
- Shows port usage status
- Provides cleanup suggestions

#### `kill_port.sh`
Kill processes using the specified port.

**Usage:**
```bash
bash scripts/kill_port.sh 8080
```

**Features:**
- Interactive confirmation
- Safely terminates processes

### 2. Data Generation

#### `generate_sample_data.py`
Generate sample data for development and testing.

**Usage:**
```bash
python scripts/generate_sample_data.py
```

**What it generates:**
- 👥 **50 users** with realistic profiles
- 💰 **~200 asset records** (4 types per user)
- 📊 **~4,500 daily balance records** (90 days per user)
- 💳 **~1,500 transactions** (20-50 per user)
- 🤖 **~500 AI sessions** (5-15 per user)
- ⭐ **~1,000 recommendations** (1-3 per session)

**Features:**
- Realistic data distribution
- Time-series data with trends
- Cross-referenced relationships
- Business logic validation
- Progress tracking

**Data Structure:**
Based on the original `data_generation/` module but adapted for PostgreSQL/SQLite:
- User IDs: `user_1001` to `user_1050`
- Date range: Past 90 days
- Asset types: POINTS, EARNINGS, CRYPTO, GIGA_ASSET
- Transaction categories: 1-8
- Payment methods: credit_card, points, sales_balance, mixed

### 3. Batch Processing

#### `batch_processing.sh` ⭐ (Unified Script)
Unified batch processing system management script that consolidates all batch processing functionality.

**Usage:**
```bash
bash scripts/batch_processing.sh
```

**Features:**
- Interactive menu for unified management of all batch processing services
- Supports foreground/background startup of Celery Worker, Beat, and Flower
- One-click startup of complete batch processing system
- Check service status
- Stop all services
- Manually run batch processing tasks

**Available Options:**
1. Start Celery Worker (foreground)
2. Start Celery Beat (foreground)
3. Start Celery Beat (background)
4. Start Flower monitoring (foreground)
5. Start Flower monitoring (background)
6. Manually run all batch jobs
7. Start complete batch processing system (Worker + Beat + Flower, background)
8. Check service status
9. Stop all batch processing services
0. Exit

**Note:** The old individual scripts (`start_celery_worker.sh`, `start_celery_beat.sh`, `start_flower.sh`, `run_all_batch_jobs.sh`) have been removed, and all functionality has been consolidated into this unified script.

### 4. Cleanup

#### `cleanup.sh`
Clean temporary files and caches.

**Usage:**
```bash
bash scripts/cleanup.sh
```

**What it cleans:**
- `__pycache__/` directories
- `*.pyc`, `*.pyo` files
- `*.tmp`, `*.temp`, `*.bak` files
- Log files (`*.log`, `logs/`)
- Test coverage files
- Build artifacts
- Go binaries

**Interactive:**
Prompts before deleting SQLite databases.

## 📋 Script Development Guidelines

### Adding New Scripts

1. **Naming Convention:**
   - Use descriptive names: `generate_*.py`, `cleanup_*.sh`
   - Use snake_case for Python scripts
   - Use kebab-case for shell scripts

2. **Documentation:**
   - Add docstring/comments at the top
   - Include usage examples
   - Document dependencies

3. **Error Handling:**
   - Always include try/except blocks
   - Provide helpful error messages
   - Return appropriate exit codes

4. **Progress Feedback:**
   - Show progress for long-running operations
   - Use emojis for visual clarity (✅, ❌, ⚠️)
   - Print summary at the end

### Script Template (Python)

```python
#!/usr/bin/env python3
"""
Script Description
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def main():
    """Main function"""
    print("=" * 60)
    print("  Script Name")
    print("=" * 60)
    
    # Your code here
    
    print("✅ Complete!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Script Template (Shell)

```bash
#!/bin/bash
# Script Description

echo "🚀 Starting script..."

# Your code here

echo "✅ Complete!"
```

## 🔍 Troubleshooting

### Permission Denied
```bash
chmod +x scripts/*.sh
```

### Module Not Found (Python)
```bash
# Ensure you're in the project root
cd /path/to/saving_advisor_system
python scripts/script_name.py
```

### Database Connection Issues
```bash
# Check if database is accessible
# For PostgreSQL
psql -U postgres -d saving_advisor -c "\dt"

# For SQLite
sqlite3 saving_advisor.db ".tables"
```

## 📊 Script Execution Order

For a fresh setup:

1. **Database Setup:**
   ```bash
   # Docker Compose will create the database
   docker-compose up -d postgres
   ```

2. **Generate Sample Data:**
   ```bash
   python scripts/generate_sample_data.py
   ```

3. **Start Application:**
   ```bash
   # Start gRPC server
   python3 app/main.py
   
   # Start REST gateway (in another terminal)
   python3 start_web_server.py
   
   # Or use the unified startup script
   bash scripts/start_services.sh
   ```

4. **Cleanup (when needed):**
   ```bash
   bash scripts/cleanup.sh
   ```

## 🎯 Best Practices

### DO ✅
- Add progress indicators for long operations
- Include error handling
- Document expected outcomes
- Test scripts before committing
- Use project utilities (like `get_db_session()`)
- Print helpful completion messages

### DON'T ❌
- Hard-code sensitive information
- Skip error handling
- Create files in unexpected locations
- Leave temporary files behind
- Use absolute paths
- Assume dependencies are installed

## 📝 Notes

### Data Generation
- Default user IDs: 1001-1050 (following original convention)
- Date range: 90 days (configurable)
- All data follows business logic rules
- Safe to run multiple times (uses unique IDs)

### Cleanup
- `__pycache__` will regenerate automatically (normal behavior)
- Deleting SQLite database requires confirmation
- Doesn't affect source code or Git history

## 🔗 Related Documentation

- **[README.md](../README.md)** - Main project documentation

---

**Last Updated:** 2025-01-12  
**Maintained by:** Saving Advisor Team

