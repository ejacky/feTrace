package services

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"

	"backend_go/models"
)

type CacheService struct {
	mu         sync.RWMutex
	data       models.PeopleData
	nameCache  map[string]bool
	dirty      bool
	savePath   string
	flushInt   int
	stopCh     chan struct{}
}

func NewCacheService(savePath string, flushInterval int) *CacheService {
	return &CacheService{
		data:      models.PeopleData{Persons: []models.Person{}},
		nameCache: make(map[string]bool),
		savePath:  savePath,
		flushInt:  flushInterval,
		stopCh:    make(chan struct{}),
	}
}

func (c *CacheService) LoadFromDisk() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if _, err := os.Stat(c.savePath); os.IsNotExist(err) {
		log.Printf("People data file %s not found, starting with empty cache", c.savePath)
		return nil
	}

	file, err := os.Open(c.savePath)
	if err != nil {
		return fmt.Errorf("failed to open people data file: %w", err)
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&c.data); err != nil {
		return fmt.Errorf("failed to decode people data: %w", err)
	}

	c.rebuildNameCache()
	log.Printf("Loaded %d people from disk", len(c.data.Persons))
	return nil
}

func (c *CacheService) saveToDisk() error {
	if !c.dirty {
		return nil
	}

	tempFile := c.savePath + ".tmp"
	file, err := os.Create(tempFile)
	if err != nil {
		return fmt.Errorf("failed to create temp file: %w", err)
	}
	defer file.Close()
	
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(c.data); err != nil {
		os.Remove(tempFile)
		return fmt.Errorf("failed to encode data: %w", err)
	}

	if err := os.Rename(tempFile, c.savePath); err != nil {
		os.Remove(tempFile)
		return fmt.Errorf("failed to rename temp file: %w", err)
	}

	c.dirty = false
	log.Printf("Successfully saved %d people to disk", len(c.data.Persons))
	return nil
}

func (c *CacheService) rebuildNameCache() {
	c.nameCache = make(map[string]bool)
	for _, person := range c.data.Persons {
		c.nameCache[person.Name] = true
	}
}

func (c *CacheService) StartBackgroundSaver() {
	if c.flushInt <= 0 {
		log.Println("Background saver disabled (flush interval <= 0)")
		return
	}

	ticker := time.NewTicker(time.Duration(c.flushInt) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			c.mu.Lock()
			if c.dirty {
				if err := c.saveToDisk(); err != nil {
					log.Printf("Failed to save to disk: %v", err)
				}
			}
			c.mu.Unlock()
		case <-c.stopCh:
			log.Println("Background saver stopped")
			return
		}
	}
}

func (c *CacheService) StopBackgroundSaver() {
	close(c.stopCh)
}

func (c *CacheService) GetAllPeople() models.PeopleData {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.data
}

func (c *CacheService) GetPersonByName(name string) (models.Person, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	for _, person := range c.data.Persons {
		if person.Name == name {
			return person, true
		}
	}
	return models.Person{}, false
}

func (c *CacheService) GetAllNames() []string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	names := make([]string, 0, len(c.nameCache))
	for name := range c.nameCache {
		names = append(names, name)
	}
	return names
}

func (c *CacheService) AddPerson(person models.Person) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// Replace existing person if they exist
	for i, existing := range c.data.Persons {
		if existing.Name == person.Name {
			c.data.Persons[i] = person
			log.Printf("Updated existing person: %s", person.Name)
			return
		}
	}

	// Add new person
	c.data.Persons = append(c.data.Persons, person)
	c.nameCache[person.Name] = true
	c.dirty = true
	log.Printf("Added new person: %s", person.Name)
}

func (c *CacheService) AddNamesFromExcel(names []string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	addedCount := 0
	for _, name := range names {
		if !c.nameCache[name] {
			c.nameCache[name] = true
			addedCount++
		}
	}
	if addedCount > 0 {
		log.Printf("Added %d new names from Excel", addedCount)
	}
}

func (c *CacheService) NameExists(name string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.nameCache[name]
}