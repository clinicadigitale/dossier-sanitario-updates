package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"
)

// Finestrella Sì/No di Windows.
func ask(title, text string) bool {
	u := syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW")
	t, _ := syscall.UTF16PtrFromString(text)
	ti, _ := syscall.UTF16PtrFromString(title)
	// MB_YESNO (4) | MB_ICONQUESTION (0x20)
	ret, _, _ := u.Call(0, uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(ti)), uintptr(0x24))
	return ret == 6 // IDYES
}

// Crea un collegamento sul desktop che apre l'app impacchettata.
func createShortcut() {
	home := os.Getenv("USERPROFILE")
	if home == "" {
		return
	}
	lnk := filepath.Join(home, "Desktop", "Dossier Sanitario PROVA.lnk")
	aumid := `ClinicaDigitale.DossierSanitario_jg1xxf87v0t26!DossierSanitario`
	ps := `$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('` + lnk + `'); $s.TargetPath='explorer.exe'; $s.Arguments='shell:AppsFolder\` + aumid + `'; $s.Save()`
	exec.Command("powershell", "-NoProfile", "-Command", ps).Run()
}

func main() {
	// 1) Avvia subito il programma vero (motore + interfaccia).
	exe, _ := os.Executable()
	dir := filepath.Dir(exe)
	real := filepath.Join(dir, "payload", "ClinicaDigitaleAppLauncher.exe")
	cmd := exec.Command(real)
	cmd.Dir = filepath.Dir(real)
	cmd.Start()

	// 2) Solo al primo avvio, chiedi se creare l'icona sul desktop.
	la := os.Getenv("LOCALAPPDATA")
	marker := filepath.Join(la, "DossierProvaFirstRun.txt")
	if _, err := os.Stat(marker); err != nil {
		if ask("Dossier Sanitario - PROVA", "Vuoi creare un collegamento sul desktop per aprire piu' comodamente questa prova?") {
			createShortcut()
		}
		os.WriteFile(marker, []byte("1"), 0o644)
	}
}
