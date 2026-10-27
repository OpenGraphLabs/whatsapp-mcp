package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestAPIBoundary(t *testing.T) {
	token := strings.Repeat("x", 64)
	for _, tc := range []struct {
		name, host, origin, auth, content, path string
		allowSend                               bool
		want                                    int
	}{
		{"missing token", "127.0.0.1:8080", "", "", "application/json", "/api/download", false, 401},
		{"bad token", "127.0.0.1:8080", "", "Bearer bad", "application/json", "/api/download", false, 401},
		{"host rebinding", "attacker.example:8080", "", "Bearer " + token, "application/json", "/api/download", false, 403},
		{"browser origin", "127.0.0.1:8080", "https://attacker.example", "Bearer " + token, "application/json", "/api/download", false, 403},
		{"form post", "127.0.0.1:8080", "", "Bearer " + token, "text/plain", "/api/download", false, 415},
		{"send disabled", "127.0.0.1:8080", "", "Bearer " + token, "application/json", "/api/send", false, 403},
		{"download allowed", "127.0.0.1:8080", "", "Bearer " + token, "application/json", "/api/download", false, 204},
		{"send opted in", "localhost:8080", "", "Bearer " + token, "application/json", "/api/send", true, 204},
	} {
		t.Run(tc.name, func(t *testing.T) {
			called := false
			h := secureAPI(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true; w.WriteHeader(204) }), token, 8080, tc.allowSend)
			r := httptest.NewRequest("POST", "http://"+tc.host+tc.path, strings.NewReader("{}"))
			r.Header.Set("Origin", tc.origin)
			r.Header.Set("Authorization", tc.auth)
			r.Header.Set("Content-Type", tc.content)
			w := httptest.NewRecorder()
			h.ServeHTTP(w, r)
			if w.Code != tc.want || called != (tc.want == 204) {
				t.Fatalf("status=%d called=%v", w.Code, called)
			}
		})
	}
}

func TestDownloadRejectsTraversalAndSymlink(t *testing.T) {
	t.Chdir(t.TempDir())
	store, err := NewMessageStore()
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	chat := "123@g.us"
	if err := store.StoreChat(chat, "fixture", time.Now()); err != nil {
		t.Fatal(err)
	}
	put := func(id, filename string) {
		t.Helper()
		if err := store.StoreMessage(id, chat, "fixture", "", time.Now(), false, "document", filename, "", nil, nil, nil, 0); err != nil {
			t.Fatal(err)
		}
	}
	for _, filename := range []string{"../../outside", "/tmp/outside", `..\outside`, ".", "..", "C:outside"} {
		put("bad", filename)
		if ok, _, _, _, err := downloadMedia(nil, store, "bad", chat); ok || err == nil {
			t.Fatalf("accepted %q", filename)
		}
	}
	put("good", "sample.txt")
	rel, err := mediaRelativePath(chat, "good", "sample.txt")
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join("store", rel)
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(t.TempDir(), "secret"), path); err != nil {
		t.Fatal(err)
	}
	if ok, _, _, _, err := downloadMedia(nil, store, "good", chat); ok || err == nil {
		t.Fatal("accepted symlink")
	}
	os.Remove(path)
	if err := os.WriteFile(path, []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	if ok, _, _, _, err := downloadMedia(nil, store, "good", chat); !ok || err != nil {
		t.Fatalf("valid cached file failed: %v", err)
	}
	other, _ := mediaRelativePath(chat, "another-message", "sample.txt")
	if other == rel {
		t.Fatal("message filenames collide")
	}
}

func TestTokenFilePermissions(t *testing.T) {
	path := filepath.Join(t.TempDir(), "api-token")
	t.Setenv("WHATSAPP_API_TOKEN_FILE", path)
	if _, err := loadAPIToken(); err == nil {
		t.Fatal("missing token accepted")
	}
	os.WriteFile(path, []byte(strings.Repeat("x", 64)), 0600)
	if _, err := loadAPIToken(); err != nil {
		t.Fatal(err)
	}
	os.Chmod(path, 0644)
	if _, err := loadAPIToken(); err == nil {
		t.Fatal("public token accepted")
	}
}
