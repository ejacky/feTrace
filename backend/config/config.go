package config

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	Port              int    `json:"PORT"`
	FlushIntervalSec  int    `json:"FLUSH_INTERVAL_SEC"`
	GeocodeEnabled    bool   `json:"GEOCODE_ENABLED"`
	GeocodeMaxCalls   int    `json:"GEOCODE_MAX_CALLS"`
	FrontendDir       string `json:"FRONTEND_DIR"`
	PeopleDataFile    string `json:"PEOPLE_DATA_FILE"`
	ExcelDir          string `json:"EXCEL_DIR"`
	UseAIAgentService bool   `json:"USE_AI_AGENT_SERVICE"`
	AIAgentServiceURL string `json:"AI_AGENT_SERVICE_URL"`
}

var defaultConfig = Config{
	Port:             8001,
	FlushIntervalSec: 30,

	GeocodeEnabled:    true,
	GeocodeMaxCalls:   3,
	FrontendDir:       "../frontend",
	PeopleDataFile:    "people.json",
	ExcelDir:          "data",
	UseAIAgentService: false,
	AIAgentServiceURL: "http://localhost:8002",
}

func Load() (*Config, error) {
	cfg := defaultConfig

	// Load from config.json if exists
	if err := loadFromJSON("config/config.json", &cfg); err == nil {
		fmt.Println("Loaded configuration from config.json")
	}

	// Override with environment variables
	loadFromEnv(&cfg)

	return &cfg, nil
}

func loadFromJSON(path string, cfg *Config) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	return decoder.Decode(cfg)
}

func loadFromEnv(cfg *Config) {
	if port := os.Getenv("PORT"); port != "" {
		if p, err := strconv.Atoi(port); err == nil {
			cfg.Port = p
		}
	}

	if flushInterval := os.Getenv("FLUSH_INTERVAL_SEC"); flushInterval != "" {
		if f, err := strconv.Atoi(flushInterval); err == nil {
			cfg.FlushIntervalSec = f
		}
	}

	if geocodeEnabled := os.Getenv("GEOCODE_ENABLED"); geocodeEnabled != "" {
		cfg.GeocodeEnabled = geocodeEnabled == "true" || geocodeEnabled == "1"
	}

	if geocodeMaxCalls := os.Getenv("GEOCODE_MAX_CALLS"); geocodeMaxCalls != "" {
		if g, err := strconv.Atoi(geocodeMaxCalls); err == nil {
			cfg.GeocodeMaxCalls = g
		}
	}

	if frontendDir := os.Getenv("FRONTEND_DIR"); frontendDir != "" {
		cfg.FrontendDir = frontendDir
	}

	if peopleDataFile := os.Getenv("PEOPLE_DATA_FILE"); peopleDataFile != "" {
		cfg.PeopleDataFile = peopleDataFile
	}

	if excelDir := os.Getenv("EXCEL_DIR"); excelDir != "" {
		cfg.ExcelDir = excelDir
	}

	if useAIAgent := os.Getenv("USE_AI_AGENT_SERVICE"); useAIAgent != "" {
		cfg.UseAIAgentService = useAIAgent == "true" || useAIAgent == "1"
	}

	if aiAgentURL := os.Getenv("AI_AGENT_SERVICE_URL"); aiAgentURL != "" {
		cfg.AIAgentServiceURL = aiAgentURL
	}
}

func (c *Config) Save(path string) error {
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(c)
}
