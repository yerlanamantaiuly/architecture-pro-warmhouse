package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

type temperatureResponse struct {
	Value       float64   `json:"value"`
	Unit        string    `json:"unit"`
	Timestamp   time.Time `json:"timestamp"`
	Location    string    `json:"location"`
	Status      string    `json:"status"`
	SensorID    string    `json:"sensor_id"`
	SensorType  string    `json:"sensor_type"`
	Description string    `json:"description"`
}

var (
	delayMS      = getEnvInt("TEMPERATURE_DELAY_MS", 0)
	failureRate  = getEnvFloat("TEMPERATURE_FAILURE_RATE", 0)
	tempMin      = getEnvFloat("TEMPERATURE_MIN", 18)
	tempMax      = getEnvFloat("TEMPERATURE_MAX", 29)
	defaultPort  = getEnv("PORT", "8081")
	roomBySensor = map[string]string{
		"1": "Living Room",
		"2": "Bedroom",
		"3": "Kitchen",
	}
	sensorByRoom = map[string]string{
		"living room": "1",
		"bedroom":     "2",
		"kitchen":     "3",
	}
)

func main() {
	rand.Seed(time.Now().UnixNano())

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/temperature", temperatureByLocationHandler)
	mux.HandleFunc("/temperature/", temperatureByIDHandler)

	addr := ":" + strings.TrimPrefix(defaultPort, ":")
	log.Printf("temperature-api listening on %s", addr)
	if err := http.ListenAndServe(addr, loggingMiddleware(mux)); err != nil {
		log.Fatalf("server stopped: %v", err)
	}
}

func healthHandler(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func temperatureByLocationHandler(w http.ResponseWriter, r *http.Request) {
	location := strings.TrimSpace(r.URL.Query().Get("location"))
	sensorID := strings.TrimSpace(r.URL.Query().Get("sensorId"))

	if location == "" {
		location = roomBySensor[sensorID]
	}
	if location == "" {
		location = "Unknown"
	}

	if sensorID == "" {
		sensorID = sensorIDForLocation(location)
	}

	respondWithTemperature(w, location, sensorID)
}

func temperatureByIDHandler(w http.ResponseWriter, r *http.Request) {
	sensorID := strings.TrimPrefix(r.URL.Path, "/temperature/")
	if sensorID == "" {
		http.Error(w, "sensor ID is required", http.StatusBadRequest)
		return
	}

	location := roomBySensor[sensorID]
	if location == "" {
		location = "Unknown"
	}

	respondWithTemperature(w, location, sensorID)
}

func respondWithTemperature(w http.ResponseWriter, location, sensorID string) {
	if delayMS > 0 {
		time.Sleep(time.Duration(delayMS) * time.Millisecond)
	}

	if failureRate > 0 && rand.Float64() < failureRate {
		http.Error(w, "simulated upstream failure", http.StatusServiceUnavailable)
		return
	}

	response := temperatureResponse{
		Value:       randomTemperature(),
		Unit:        "C",
		Timestamp:   time.Now().UTC(),
		Location:    location,
		Status:      "active",
		SensorID:    sensorID,
		SensorType:  "temperature",
		Description: fmt.Sprintf("Live temperature for %s", location),
	}

	writeJSON(w, http.StatusOK, response)
}

func randomTemperature() float64 {
	minTemp := tempMin
	maxTemp := tempMax
	if maxTemp < minTemp {
		minTemp, maxTemp = maxTemp, minTemp
	}
	raw := minTemp + rand.Float64()*(maxTemp-minTemp)
	return math.Round(raw*10) / 10
}

func sensorIDForLocation(location string) string {
	if id, ok := sensorByRoom[strings.ToLower(location)]; ok {
		return id
	}
	return "0"
}

func writeJSON(w http.ResponseWriter, statusCode int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("failed to write response: %v", err)
	}
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s completed in %s", r.Method, r.URL.Path, time.Since(start))
	})
}

func getEnv(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func getEnvInt(key string, fallback int) int {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvFloat(key string, fallback float64) float64 {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.ParseFloat(value, 64)
	if err != nil {
		return fallback
	}
	return parsed
}
