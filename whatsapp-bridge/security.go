package main

import (
	"crypto/sha256"
	"crypto/subtle"
	"fmt"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

func loadAPIToken() (string, error) {
	path := os.Getenv("WHATSAPP_API_TOKEN_FILE")
	info, err := os.Stat(path)
	if err != nil || info == nil || !info.Mode().IsRegular() || info.Mode().Perm()&0077 != 0 {
		return "", fmt.Errorf("WHATSAPP_API_TOKEN_FILE must be an owner-only regular file")
	}
	data, err := os.ReadFile(path)
	token := strings.TrimSpace(string(data))
	if err != nil || len(token) < 32 {
		return "", fmt.Errorf("API token must contain at least 32 characters")
	}
	return token, nil
}

func secureAPI(next http.Handler, token string, port int, allowSend bool) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		if (r.Host != fmt.Sprintf("127.0.0.1:%d", port) && r.Host != fmt.Sprintf("localhost:%d", port)) || r.Header.Get("Origin") != "" {
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}
		if len(token) < 32 || subtle.ConstantTimeCompare([]byte(r.Header.Get("Authorization")), []byte("Bearer "+token)) != 1 {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		if r.URL.Path == "/api/send" && !allowSend {
			http.Error(w, "Sending is disabled; explicitly enable WHATSAPP_ENABLE_SEND=1", http.StatusForbidden)
			return
		}
		mediaType, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
		if err != nil || mediaType != "application/json" {
			http.Error(w, "JSON required", http.StatusUnsupportedMediaType)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
		next.ServeHTTP(w, r)
	})
}

// Do not use sender-controlled filenames or IDs as filesystem paths.
func mediaRelativePath(chatJID, messageID, filename string) (string, error) {
	if chatJID == "" || messageID == "" || filename == "" || filename == "." || filename == ".." || strings.ContainsAny(filename, "/\\\x00") || strings.Contains(filename, ":") {
		return "", fmt.Errorf("invalid media identifiers or filename")
	}
	chatHash := sha256.Sum256([]byte(chatJID))
	messageHash := sha256.Sum256([]byte(messageID))
	return filepath.Join("media", fmt.Sprintf("%x", chatHash), fmt.Sprintf("%x", messageHash), filename), nil
}
