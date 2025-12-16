package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"time"

	"backend_go/models"
)

// AIAgentService 提供与 Python AI Agent 服务的通信
type AIAgentService struct {
	baseURL        string
	httpClient     *http.Client
	geocodeService *GeocodeService
}

// NewAIAgentService 创建新的 AI Agent 服务客户端
func NewAIAgentService(baseURL string, geocodeService *GeocodeService) *AIAgentService {
	return &AIAgentService{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		geocodeService: geocodeService,
	}
}

// GetTimelineData 通过 AI Agent 服务获取人物时间线数据
func (a *AIAgentService) GetTimelineData(name string) (models.PeopleData, error) {
	if a.baseURL == "" {
		return models.PeopleData{}, fmt.Errorf("AI Agent service URL is not configured")
	}

	// 构建请求 URL
	apiURL := fmt.Sprintf("%s/api/timeline?name=%s", a.baseURL, url.QueryEscape(name))

	log.Printf("Calling AI Agent service for person: %s", name)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return models.PeopleData{}, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Accept", "application/json")

	resp, err := a.httpClient.Do(req)
	if err != nil {
		return models.PeopleData{}, fmt.Errorf("AI Agent service request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return models.PeopleData{}, fmt.Errorf("AI Agent service returned status %d: %s", resp.StatusCode, string(body))
	}

	var aiResponse models.Person
	if err := json.NewDecoder(resp.Body).Decode(&aiResponse); err != nil {
		return models.PeopleData{}, fmt.Errorf("failed to decode AI Agent response: %w", err)
	}

	// 检查是否有错误信息
	if aiResponse.Name == "" && aiResponse.Events == nil {
		return models.PeopleData{}, fmt.Errorf("AI Agent service returned empty response")
	}

	// 转换为 PeopleData 格式（兼容多种响应格式）
	if aiResponse.Events == nil {
		aiResponse.Events = []models.Event{}
	}

	// Add geocoding to events if enabled
	if a.geocodeService != nil {
		for i := range aiResponse.Events {
			if aiResponse.Events[i].Place != "" && (aiResponse.Events[i].Lat == "" || aiResponse.Events[i].Lon == "") {
				lat, lon, err := a.geocodeService.Geocode(aiResponse.Events[i].Place)
				if err != nil {
					log.Printf("Failed to geocode place '%s': %v", aiResponse.Events[i].Place, err)
				} else {
					aiResponse.Events[i].Lat = lat
					aiResponse.Events[i].Lon = lon
				}
			}
		}
	}

	// Create person from results with random styling colors
	style := models.Style{
		MarkerColor: "#FF6B6B",
		LineColor:   "#4ECDC4",
	}
	aiResponse.Style = style
	aiResponse.Name = name

	log.Printf("Successfully retrieved timeline data for %s with %d events", name, len(aiResponse.Events))
	return models.PeopleData{Persons: []models.Person{aiResponse}}, nil
}

// GetTimelineBatch 批量获取多个人的时间线数据
func (a *AIAgentService) GetTimelineBatch(names []string) ([]models.Person, error) {
	if a.baseURL == "" {
		return nil, fmt.Errorf("AI Agent service URL is not configured")
	}

	if len(names) == 0 {
		return []models.Person{}, nil
	}

	if len(names) > 10 {
		return nil, fmt.Errorf("batch size too large, maximum 10 names allowed")
	}

	apiURL := fmt.Sprintf("%s/api/batch-timeline", a.baseURL)

	requestBody := struct {
		Names []string `json:"names"`
	}{
		Names: names,
	}

	jsonBody, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create batch request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := a.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("AI Agent batch request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("AI Agent batch service returned status %d: %s", resp.StatusCode, string(body))
	}

	var response struct {
		Results []models.Person `json:"results"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode batch response: %w", err)
	}

	return response.Results, nil
}

// HealthCheck 检查 AI Agent 服务的健康状态
func (a *AIAgentService) HealthCheck() (map[string]interface{}, error) {
	if a.baseURL == "" {
		return map[string]interface{}{
			"error":  "AI Agent service URL is not configured",
			"status": "unhealthy",
		}, fmt.Errorf("service not configured")
	}

	apiURL := fmt.Sprintf("%s/health", a.baseURL)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create health check request: %w", err)
	}

	resp, err := a.httpClient.Do(req)
	if err != nil {
		return map[string]interface{}{
			"error":  fmt.Sprintf("health check request failed: %v", err),
			"status": "unhealthy",
		}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return map[string]interface{}{
			"error":  fmt.Sprintf("health check returned status %d: %s", resp.StatusCode, string(body)),
			"status": "unhealthy",
		}, fmt.Errorf("unhealthy service")
	}

	var healthStatus map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&healthStatus); err != nil {
		return nil, fmt.Errorf("failed to decode health response: %w", err)
	}

	return healthStatus, nil
}

// IsConfigured 检查服务是否已配置
func (a *AIAgentService) IsConfigured() bool {
	return a.baseURL != ""
}

// GetServiceURL 获取服务 URL
func (a *AIAgentService) GetServiceURL() string {
	return a.baseURL
}
