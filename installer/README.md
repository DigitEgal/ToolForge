# Windows-Installer

`ToolForge.iss` ist die Inno-Setup-6-Definition, `build_installer.ps1` baut und
optional signiert den Installer.

## Voraussetzungen

- Windows 10/11
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) mit `ISCC.exe`
- Node.js nur, wenn `frontend/dist/index.html` fehlt und das Frontend neu gebaut
  werden muss
- Optional: Windows SDK mit `signtool.exe` und ein Code-Signaturzertifikat

## Bauen

```powershell
.\installer\build_installer.ps1
```

Das Ergebnis liegt unter `dist\installer\ToolForge-Setup-1.2.exe`; daneben
entsteht `SHA256SUMS.txt`.

## Signieren

Ohne Zertifikat wird ein unsignierter Installer gebaut. Für eine echte Signatur
entweder einen Zertifikat-Thumbprint aus dem Windows-Zertifikatsspeicher oder
eine PFX-Datei setzen:

```powershell
$env:TOOLFORGE_SIGN_CERT = 'C:\certs\toolforge.pfx'
$env:TOOLFORGE_SIGN_PASSWORD = '...'
.\installer\build_installer.ps1
```

oder:

```powershell
$env:TOOLFORGE_SIGN_CERT = 'AB12CD34...'
.\installer\build_installer.ps1
```

Der Build prüft die Signatur anschließend mit `signtool verify /pa`. Ohne
Zertifikat bleibt der Installer unsigniert; das ist in der Entwicklungsumgebung
erwartbar und wird im Betriebsstatus entsprechend ausgewiesen.

## Installation

Der Installer installiert unter `%LOCALAPPDATA%\Programs\ToolForge` und legt
Startmenü-Verknüpfungen an. Python 3.11 oder neuer muss vorhanden sein; die
eigentliche Einrichtung startet nach der Installation über
`Setup_ToolForge.cmd`, damit die virtuellen Umgebungen im Benutzerprofil
entstehen. Eine Deinstallation entfernt nur ToolForge-eigene Dateien und
Umgebungen; Projektordner bleiben unangetastet.
