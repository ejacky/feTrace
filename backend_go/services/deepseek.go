package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"backend_go/models"
)

type DeepseekService struct {
	apiKey          string
	httpClient      *http.Client
	geocodeService  *GeocodeService
	aiAgentService  *AIAgentService
	useAIAgent      bool
}

func NewDeepseekService(apiKey string, connectTimeout, readTimeout time.Duration, geocodeService *GeocodeService) *DeepseekService {
	return &DeepseekService{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: readTimeout,
		},
		geocodeService: geocodeService,
		aiAgentService: nil,
		useAIAgent:     false,
	}
}

func NewDeepseekServiceWithAIAgent(apiKey string, connectTimeout, readTimeout time.Duration, geocodeService *GeocodeService, aiAgentService *AIAgentService) *DeepseekService {
	return &DeepseekService{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: readTimeout,
		},
		geocodeService: geocodeService,
		aiAgentService: aiAgentService,
		useAIAgent:     aiAgentService != nil && aiAgentService.IsConfigured(),
	}
}

func (d *DeepseekService) GetTimelineData(name string) (models.PeopleData, error) {
	// 优先使用 AI Agent 服务（如果配置且可用）
	if d.useAIAgent && d.aiAgentService != nil {
		log.Printf("Using AI Agent service for person: %s", name)
		return d.getTimelineViaAIAgent(name)
	}

	// 回退到原始的 DeepSeek API 调用
	log.Printf("Using original DeepSeek API for person: %s", name)
	return d.getTimelineViaDeepSeekAPI(name)
}

func (d *DeepseekService) getTimelineViaAIAgent(name string) (models.PeopleData, error) {
	if d.aiAgentService == nil {
		return models.PeopleData{}, fmt.Errorf("AI Agent service not configured")
	}

	peopleData, err := d.aiAgentService.GetTimelineData(name)
	if err != nil {
		return models.PeopleData{}, fmt.Errorf("AI Agent service failed: %w", err)
	}

	// AI Agent 服务已经处理了地理编码，这里不需要额外处理
	return peopleData, nil
}

func (d *DeepseekService) getTimelineViaDeepSeekAPI(name string) (models.PeopleData, error) {
	function := models.DeepseekFunction{
		Name:        "get_timeline_data",
		Description: "获取人物生平事件时间线数据",
	}

	function.Parameters.Type = "object"
	function.Parameters.Properties.Events.Type = "array"
	function.Parameters.Properties.Events.Description = "时间线事件列表"
	function.Parameters.Properties.Events.Items.Type = "object"

	properties := &function.Parameters.Properties.Events.Items.Properties

	properties.Year.Type = "integer"
	properties.Year.Description = "事件发生年份"

	properties.Age.Type = "integer"
	properties.Age.Description = "年龄 (可为空)"

	properties.Place.Type = "string"
	properties.Place.Description = "地点"

	properties.Title.Type = "string"
	properties.Title.Description = "事件标题"

	properties.Detail.Type = "string"
	properties.Detail.Description = "事件详细描述"

	function.Parameters.Required = []string{"events"}

	request := models.DeepseekRequest{
		Model:       "deepseek-chat",
		Temperature: 0.2,
		Functions:   []models.DeepseekFunction{function},
		FunctionCall: "get_timeline_data",
	}

	request.Messages = []struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	}{
		{
			Role:    "user",
			Content: fmt.Sprintf("请生成%s的生平事件时间线数据。返回一个事件数组，每个事件包含年份、年龄、地点、标题和详细描述。", name),
		},
	}

	jsonData, err := json.Marshal(request)
	if err != nil {
		return models.PeopleData{}, fmt.Errorf("failed to marshal request: %w", err)
	}

	log.Printf("Calling DeepSeek API for person: %s", name)

	req, err := http.NewRequest("POST", "https://api.deepseek.com/v1/chat/completions", bytes.NewBuffer(jsonData))
	if err != nil {
		return models.PeopleData{}, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+d.apiKey)

	client := &http.Client{
		Timeout: d.httpClient.Timeout,
	}

	resp, err := client.Do(req)
	if err != nil {
		if connectErr, ok := err.(interface{ Timeout() bool }); ok && connectErr.Timeout() {
			return models.PeopleData{}, fmt.Errorf("DeepSeek API timeout: %w", err)
		}
		return models.PeopleData{}, fmt.Errorf("DeepSeek API request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return models.PeopleData{}, fmt.Errorf("DeepSeek API returned status %d: %s", resp.StatusCode, string(body))
	}

	var response models.DeepseekResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return models.PeopleData{}, fmt.Errorf("failed to decode response: %w", err)
	}

	if len(response.Choices) == 0 || response.Choices[0].Message.FunctionCall.Name == "" {
		return models.PeopleData{}, fmt.Errorf("unexpected DeepSeek API response format")
	}

	var functionResult struct {
		Events []models.Event `json:"events"`
	}
	if err := json.Unmarshal([]byte(response.Choices[0].Message.FunctionCall.Arguments), &functionResult); err != nil {
		return models.PeopleData{}, fmt.Errorf("failed to parse function call arguments: %w", err)
	}

	// Add geocoding to events if enabled
	if d.geocodeService != nil {
		for i := range functionResult.Events {
			if functionResult.Events[i].Place != "" {
				lat, lon, err := d.geocodeService.Geocode(functionResult.Events[i].Place)
				if err != nil {
					log.Printf("Failed to geocode place '%s': %v", functionResult.Events[i].Place, err)
				} else {
					functionResult.Events[i].Lat = lat
					functionResult.Events[i].Lon = lon
				}
			}
		}
	}

// Create person from results with random styling colors
	style := models.Style{
		MarkerColor: "#FF6B6B",
		LineColor:   "#4ECDC4",
	}

	person := models.Person{
		Name:   name,
		Style:  style,
		Events: functionResult.Events,
	}

	log.Printf("Successfully retrieved timeline data for %s with %d events", name, len(functionResult.Events))
	return models.PeopleData{Persons: []models.Person{person}}, nil
}

func (d *DeepseekService) IsConfigured() bool {
	return d.apiKey != ""
}