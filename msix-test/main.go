package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"syscall"
	"time"
	"unsafe"
)

func messageBox(title, text string) {
	proc := syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW")
	t, _ := syscall.UTF16PtrFromString(text)
	ti, _ := syscall.UTF16PtrFromString(title)
	proc.Call(0, uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(ti)), 0)
}

func main() {
	addr := "127.0.0.1:8896"
	srvErr := make(chan error, 1)
	http.HandleFunc("/ping", func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, "DOSSIER-LOOPBACK-OK")
	})
	go func() { srvErr <- http.ListenAndServe(addr, nil) }()
	time.Sleep(1500 * time.Millisecond)

	loop := "FALLITO"
	detail := ""
	select {
	case e := <-srvErr:
		detail = "il server locale non e' partito: " + e.Error()
	default:
		resp, err := http.Get("http://" + addr + "/ping")
		if err != nil {
			detail = "il server e' partito ma non risponde: " + err.Error()
		} else {
			b, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			if string(b) == "DOSSIER-LOOPBACK-OK" {
				loop = "OK"
				detail = "il server locale su 127.0.0.1:8896 risponde correttamente."
			} else {
				detail = "risposta inattesa: " + string(b)
			}
		}
	}

	write := "FALLITO"
	if la := os.Getenv("LOCALAPPDATA"); la != "" {
		dir := filepath.Join(la, "DossierMsixTest")
		os.MkdirAll(dir, 0o755)
		p := filepath.Join(dir, "risultato.txt")
		content := fmt.Sprintf("Loopback: %s\r\n%s\r\n", loop, detail)
		if err := os.WriteFile(p, []byte(content), 0o644); err == nil {
			write = "OK"
		} else {
			write = "FALLITO: " + err.Error()
		}
	}

	msg := fmt.Sprintf(
		"PROVA DOSSIER DENTRO MICROSOFT STORE (MSIX)\r\n\r\n"+
			"Server locale (il motore che legge i referti): %s\r\n%s\r\n\r\n"+
			"Scrittura dati nella cartella utente: %s\r\n\r\n"+
			"Se entrambi sono OK, il Dossier puo' funzionare come pacchetto dello Store.",
		loop, detail, write)
	messageBox("Prova Dossier MSIX", msg)
}
