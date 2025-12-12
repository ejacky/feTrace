# Go Backend Implementation

This is the Go implementation of the backend APIs, converting the original Python backend to a faster, more concurrent service.

## Features

- **Same APIs as Python version**: 
  - `GET /api/people` - Returns all person data
  - `GET /api/person?name={name}` - Returns specific person data with DeepSeek fallback
  - `GET /api/names` - Returns list of all available names
  - `/` - Serves frontend static files

- **Configuration Management**: Custom Go config with environment variable overrides
- **Concurrent Caching**: Thread-safe in-memory cache with background persistence
- **Geolocation Integration**: Automatic coordinate lookup for locations
- **DeepSeek API Integration**: External data fetching for unknown people

## Installation

```bash
# Install dependencies
go mod tidy

# Build the application
go build -o backend_go main.go

# Run with config file
./backend_go -config config/config.json
```

## Configuration

Create a configuration file at `config/config.json`:

```json
{
  "PORT": 8001,
  "FLUSH_INTERVAL_SEC": 30,
  "DEEPSEEK_API_KEY": "your-api-key-here",
  "DEEPSEEK_CONNECT_TIMEOUT": 15,
  "DEEPSEEK_READ_TIMEOUT": 40,
  "GEOCODE_ENABLED": true,
  "GEOCODE_MAX_CALLS": 3
}
```

Or use environment variables:
```bash
export PORT=8001
export DEEPSEEK_API_KEY=your-api-key-here
export GEOCODE_ENABLED=true
```

## Directory Structure

```
backend_go/
├── config/
│   └── config.go      # Configuration management
├── models/
│   └── person.go      # Data models and API schemas
├── services/
│   ├── cache.go       # In-memory cache with persistence
│   ├── deepseek.go    # DeepSeek API integration
│   ├── geocode.go     # Geocoding service
│   └── excel.go       # Excel file parsing
├── sample_people.json # Sample data file
├── main.go           # Main application
└── go.mod            # Go module file
```

## Data Storage

- Main data file: `people.json` (atomically updated)
- Excel files: Processed from `data/` directory
- Cache: In-memory with optional disk persistence

## Performance

- **Concurrent**: Thread-safe operations for better scaling
- **In-memory caching**: Fast responses for cached data
- **Background persistence**: Non-blocking disk writes
- **Atomic files writes**: Safe concurrent file updates

Usage examples:

```bash
# Initialize sample config
./backend_go -init-config

# Run with sample data
cp sample_people.json people.json
./backend_go

# Run with custom config
./backend_go -config myconfig.json
```

Environment variables override config file:
- `PORT` - Server port
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `GEOCODE_ENABLED` - Enable geocoding
- `FLUSH_INTERVAL_SEC` - Cache flush interval