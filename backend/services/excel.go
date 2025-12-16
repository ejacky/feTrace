package services

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
)

type ExcelService struct {
	nameColumnKeywords []string
}

func NewExcelService() *ExcelService {
	return &ExcelService{
		nameColumnKeywords: []string{"姓名", "人物", "人名", "name", "Name", "NAME"},
	}
}

func (e *ExcelService) ReadNamesFromExcel(directory string) ([]string, error) {
	var allNames []string
	seen := make(map[string]bool)

	files, err := filepath.Glob(filepath.Join(directory, "*.xls"))
	if err != nil {
		return nil, fmt.Errorf("failed to find Excel files: %w", err)
	}

	for _, file := range files {
		names, err := e.readNamesFromFile(file)
		if err != nil {
			log.Printf("Failed to read from Excel file %s: %v", file, err)
			continue
		}

		fileCount := 0
		for _, name := range names {
			if !seen[name] {
				seen[name] = true
				allNames = append(allNames, name)
				fileCount++
			}
		}

		log.Printf("Read %d unique names from Excel file %s (total: %d)", fileCount, file, len(allNames))
	}

	return allNames, nil
}

func (e *ExcelService) readNamesFromFile(filename string) ([]string, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to open Excel file: %w", err)
	}
	defer file.Close()

	return e.parseXLSFile(file)
}

func (e *ExcelService) parseXLSFile(file *os.File) ([]string, error) {
	var names []string
	seen := make(map[string]bool)

	scanner := bufio.NewScanner(file)
	lineNum := 0
	nameColIndex := -1

	for scanner.Scan() {
		line := scanner.Text()
		lineNum++

		// Very basic XLS parsing - just look for text that contains name keywords
		fields := strings.Split(line, "\t")
		
		// Look for header row with name column
		if nameColIndex == -1 {
			for i, field := range fields {
				for _, keyword := range e.nameColumnKeywords {
					if strings.Contains(strings.ToLower(field), strings.ToLower(keyword)) {
						nameColIndex = i
						break
					}
				}
				if nameColIndex != -1 {
					break
				}
			}
			continue
		}

		// Extract name from the name column
		if nameColIndex < len(fields) {
			name := strings.TrimSpace(fields[nameColIndex])
			if name != "" && !seen[name] {
				seen[name] = true
				names = append(names, name)
			}
		}

		// Limit to first 1000 rows for safety
		if lineNum > 1000 {
			break
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading file: %w", err)
	}

	if nameColIndex == -1 {
		log.Printf("No name column found in Excel file %s", file.Name())
	}

	return names, nil
}

func (e *ExcelService) parseXLSXFile(reader io.Reader) ([]string, error) {
	// For now, return empty for .xlsx files as it needs the full excelize library
	log.Printf("XLSX parsing not implemented, skipping file")
	return []string{}, nil
}