package services

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"
)

type GeocodeService struct {
	cache       map[string][2]interface{} // latitude, longitude
	cacheMutex  sync.RWMutex
	enabled     bool
	maxCalls    int
	httpClient  *http.Client
}

func NewGeocodeService(enabled bool, maxCalls int) *GeocodeService {
	return &GeocodeService{
		cache:      make(map[string][2]interface{}),
		enabled:    enabled,
		maxCalls:   maxCalls,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (g *GeocodeService) Geocode(place string) (interface{}, interface{}, error) {
	if !g.enabled {
		return nil, nil, nil
	}

	place = strings.TrimSpace(place)
	if place == "" {
		return nil, nil, nil
	}

	// Check cache first
	g.cacheMutex.RLock()
	if coords, exists := g.cache[place]; exists {
		g.cacheMutex.RUnlock()
		return coords[0], coords[1], nil
	}
	g.cacheMutex.RUnlock()

	// Make API call if not cached
	lat, lon, err := g.callNominatim(place)
	if err != nil {
		return nil, nil, err
	}

	// Cache the result
	g.cacheMutex.Lock()
	g.cache[place] = [2]interface{}{lat, lon}
	g.cacheMutex.Unlock()

	log.Printf("Geocoded place '%s': %v, %v", place, lat, lon)
	return lat, lon, nil
}

func (g *GeocodeService) callNominatim(place string) (interface{}, interface{}, error) {
	// Limit API calls per function call
	if g.maxCalls <= 0 {
		return nil, nil, fmt.Errorf("geocoding calls limit reached")
	}
	g.maxCalls--

	encodedPlace := url.QueryEscape(place)
	apiURL := fmt.Sprintf("https://nominatim.openstreetmap.org/search?q=%s&format=json&limit=1", encodedPlace)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create geocoding request: %w", err)
	}

	req.Header.Set("User-Agent", "TimelineApp/1.0")

	resp, err := g.httpClient.Do(req)
	if err != nil {
		return nil, nil, fmt.Errorf("geocoding request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, nil, fmt.Errorf("geocoding API returned status %d: %s", resp.StatusCode, string(body))
	}

	var results []struct {
		DisplayName string `json:"display_name"`
		Lat         string `json:"lat"`
		Lon         string `json:"lon"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&results); err != nil {
		return nil, nil, fmt.Errorf("failed to decode geocoding response: %w", err)
	}

	if len(results) == 0 {
		return nil, nil, fmt.Errorf("no geocoding results found for '%s'", place)
	}

	// Parse coordinates
	latFloat, latErr := strconv.ParseFloat(results[0].Lat, 64)
	lonFloat, lonErr := strconv.ParseFloat(results[0].Lon, 64)

	if latErr != nil || lonErr != nil {
		return results[0].Lat, results[0].Lon, nil // Return as strings if parsing fails
	}

	return latFloat, lonFloat, nil
}

func (g *GeocodeService) ResetCallLimit() {
	// This can be called to reset the max calls counter for new requests
	// For now, we'll reset to the original maxCalls
	// In a real implementation, you might want to track this per-request
}