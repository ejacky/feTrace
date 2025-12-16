package models

// Event represents a timeline event for a person
type Event struct {
	Year   interface{} `json:"year"` // Can be int or string
	Age    interface{} `json:"age"`  // Can be int or string
	Place  string      `json:"place"`
	Lat    interface{} `json:"lat"` // Can be float64, string, or null
	Lon    interface{} `json:"lon"` // Can be float64, string, or null
	Title  string      `json:"title"`
	Detail string      `json:"detail"`
}

// Style represents the visual styling for a person
type Style struct {
	MarkerColor string `json:"markerColor"`
	LineColor   string `json:"lineColor"`
}

// Person represents a person with timeline data
type Person struct {
	Name   string  `json:"name"`
	Style  Style   `json:"style"`
	Events []Event `json:"events"`
}

// PeopleData represents the root data structure
type PeopleData struct {
	Persons []Person `json:"persons"`
}

// DeepseekFunction represents the function schema for DeepSeek API
type DeepseekFunction struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Parameters  struct {
		Type       string `json:"type"`
		Properties struct {
			Events struct {
				Type        string `json:"type"`
				Description string `json:"description"`
				Items       struct {
					Type       string `json:"type"`
					Properties struct {
						Year struct {
							Type        string `json:"type"`
							Description string `json:"description"`
						} `json:"year"`
						Age struct {
							Type        string `json:"type"`
							Description string `json:"description"`
						} `json:"age"`
						Place struct {
							Type        string `json:"type"`
							Description string `json:"description"`
						} `json:"place"`
						Title struct {
							Type        string `json:"type"`
							Description string `json:"description"`
						} `json:"title"`
						Detail struct {
							Type        string `json:"type"`
							Description string `json:"description"`
						} `json:"detail"`
					} `json:"properties"`
				} `json:"items"`
			} `json:"events"`
		} `json:"properties"`
		Required []string `json:"required"`
	} `json:"parameters"`
}

// DeepseekRequest represents the request to DeepSeek API
type DeepseekRequest struct {
	Model    string `json:"model"`
	Messages []struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	} `json:"messages"`
	Temperature  float64            `json:"temperature"`
	Functions    []DeepseekFunction `json:"functions"`
	FunctionCall string             `json:"function_call"`
}

// DeepseekResponse represents the response from DeepSeek API
type DeepseekResponse struct {
	Choices []struct {
		Message struct {
			FunctionCall struct {
				Name      string `json:"name"`
				Arguments string `json:"arguments"`
			} `json:"function_call"`
		} `json:"message"`
	} `json:"choices"`
}

// GeocodeResponse represents the geocoding API response
type GeocodeResponse struct {
	DisplayName string `json:"display_name"`
	Lat         string `json:"lat"`
	Lon         string `json:"lon"`
}

// EventWithLocation extends Event with calculated coordinates
type EventWithLocation struct {
	Event
	CalculatedLat interface{}
	CalculatedLon interface{}
}
