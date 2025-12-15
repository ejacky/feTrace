package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"

	"backend_go/config"
	"backend_go/services"
)

type Server struct {
	config          *config.Config
	cacheService    *services.CacheService
	deepseekService *services.DeepseekService
	excelService    *services.ExcelService
	geocodeService  *services.GeocodeService
	aiAgentService  *services.AIAgentService
}

func NewServer(cfg *config.Config) (*Server, error) {
	geocodeService := services.NewGeocodeService(cfg.GeocodeEnabled, cfg.GeocodeMaxCalls)

	var deepseekService *services.DeepseekService
	s := &Server{
		config:          cfg,
		deepseekService: deepseekService,
		excelService:    services.NewExcelService(),
		geocodeService:  geocodeService,
		aiAgentService:  services.NewAIAgentService(cfg.AIAgentServiceURL, geocodeService),
	}

	// Initialize cache service
	s.cacheService = services.NewCacheService(cfg.PeopleDataFile, cfg.FlushIntervalSec)

	return s, nil
}

func (s *Server) initializeData() error {
	// Load existing data
	if err := s.cacheService.LoadFromDisk(); err != nil {
		return fmt.Errorf("failed to load data from disk: %w", err)
	}

	// Load names from Excel files
	if names, err := s.excelService.ReadNamesFromExcel(s.config.ExcelDir); err != nil {
		log.Printf("Warning: failed to read names from Excel: %v", err)
	} else {
		s.cacheService.AddNamesFromExcel(names)
		log.Printf("Loaded %d unique names from Excel files", len(names))
	}

	// Start background saver
	go s.cacheService.StartBackgroundSaver()

	return nil
}

func (s *Server) setupRoutes() {
	http.HandleFunc("/api/people", s.handlePeople)
	http.HandleFunc("/api/person", s.handlePerson)
	http.HandleFunc("/api/names", s.handleNames)
	http.HandleFunc("/", s.handleStatic)
}

func (s *Server) handlePeople(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		s.httpError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	data := s.cacheService.GetAllPeople()
	s.writeJSON(w, data)
}

func (s *Server) handlePerson(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodOptions {
		s.httpError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Handle CORS preflight
	if r.Method == http.MethodOptions {
		s.writeCORSHeaders(w)
		return
	}

	name := r.URL.Query().Get("name")
	if name == "" {
		s.httpError(w, "Missing name parameter", http.StatusBadRequest)
		return
	}

	// Try to get from cache
	if person, exists := s.cacheService.GetPersonByName(name); exists {
		s.writeJSON(w, person)
		return
	}

	// Try to get from DeepSeek if available

	peopleData, err := s.aiAgentService.GetTimelineData(name)
	if err != nil {
		log.Printf("DeepSeek API error: %v", err)
		s.httpError(w, fmt.Sprintf("Person not found: %s", name), http.StatusNotFound)
		return
	}

	if len(peopleData.Persons) > 0 {
		person := peopleData.Persons[0]
		s.cacheService.AddPerson(person)
		s.writeJSON(w, person)
		return
	}

	s.httpError(w, fmt.Sprintf("Person not found: %s", name), http.StatusNotFound)
}

func (s *Server) handleNames(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodOptions {
		s.httpError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Handle CORS preflight
	if r.Method == http.MethodOptions {
		s.writeCORSHeaders(w)
		return
	}

	names := s.cacheService.GetAllNames()
	s.writeJSON(w, names)
}

func (s *Server) handleStatic(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path[1:] // Remove leading slash

	if path == "" {
		path = "index.html"
	}

	// Security: prevent directory traversal
	if strings.Contains(path, "..") {
		s.httpError(w, "Invalid path", http.StatusBadRequest)
		return
	}

	fullPath := filepath.Join(s.config.FrontendDir, path)

	// Check if file exists
	if _, err := os.Stat(fullPath); os.IsNotExist(err) {
		s.httpError(w, "File not found", http.StatusNotFound)
		return
	}

	// Get MIME type
	contentType := s.getContentType(filepath.Ext(path))
	w.Header().Set("Content-Type", contentType)

	// Write file
	data, err := os.ReadFile(fullPath)
	if err != nil {
		s.httpError(w, "Failed to read file", http.StatusInternalServerError)
		return
	}

	w.Write(data)
}

func (s *Server) writeJSON(w http.ResponseWriter, data interface{}) {
	s.writeCORSHeaders(w)
	w.Header().Set("Content-Type", "application/json")

	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("Failed to encode JSON: %v", err)
		s.httpError(w, "Failed to encode response", http.StatusInternalServerError)
	}
}

func (s *Server) writeCORSHeaders(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
}

func (s *Server) httpError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": message})
}

func (s *Server) getContentType(ext string) string {
	switch strings.ToLower(ext) {
	case ".html", ".htm":
		return "text/html"
	case ".css":
		return "text/css"
	case ".js":
		return "application/javascript"
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".gif":
		return "image/gif"
	case ".svg":
		return "image/svg+xml"
	case ".json":
		return "application/json"
	default:
		return "application/octet-stream"
	}
}

func (s *Server) Stop() {
	log.Println("Shutting down server...")
	if s.cacheService != nil {
		s.cacheService.StopBackgroundSaver()
	}
}

func main() {
	// Parse command line flags
	var (
		configPath = flag.String("config", "config/config.json", "Path to configuration file")
		initConfig = flag.Bool("init-config", false, "Create a sample configuration file")
	)
	flag.Parse()

	// Initialize configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Handle init-config option
	if *initConfig {
		if err := cfg.Save(*configPath); err != nil {
			log.Fatalf("Failed to create sample configuration: %v", err)
		}
		fmt.Printf("Sample configuration created at: %s\n", *configPath)
		fmt.Println("Please edit the file and add your DeepSeek API key.")
		return
	}

	// Create and initialize server
	server, err := NewServer(cfg)
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	// Initialize data
	if err := server.initializeData(); err != nil {
		log.Fatalf("Failed to initialize data: %v", err)
	}

	// Setup graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-sigCh
		log.Println("Received shutdown signal")
		server.Stop()
		os.Exit(0)
	}()

	// Setup routes and start server
	server.setupRoutes()

	addr := fmt.Sprintf(":%d", cfg.Port)
	log.Printf("Starting server on port %d", cfg.Port)

	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
