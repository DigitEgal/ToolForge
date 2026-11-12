; ToolForge V1.3 – Inno Setup 6 definition.
; Build: installer\build_installer.ps1 (optionally signs with TOOLFORGE_SIGN_CERT).
#ifndef MyAppVersion
  #define MyAppVersion "1.3"
#endif
#define MyAppName "ToolForge"
#define MyAppPublisher "DigitEgal"
#define MyAppURL "https://digitegal.de"
#define MyAppExeName "Start_ToolForge.cmd"

[Setup]
AppId={{8E1E7B7A-6E0B-4A0B-9A78-4C6A9F5D1B11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} V{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\ToolForge
DefaultGroupName=ToolForge
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=ToolForge-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayName={#MyAppName} V{#MyAppVersion}
LicenseFile=..\LICENSE
SetupLogging=yes
UsePreviousAppDir=yes
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.py,*.cmd
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktopverknüpfung erstellen"; GroupDescription: "Zusätzliche Verknüpfungen:"; Flags: unchecked

[Files]
Source: "..\backend\*"; DestDir: "{app}\backend"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "data\*,__pycache__\*,*.pyc"
Source: "..\toolforge_pilot\*"; DestDir: "{app}\toolforge_pilot"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "__pycache__\*,*.pyc"
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\frontend\logos\*"; DestDir: "{app}\frontend\logos"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\acceptance\*"; DestDir: "{app}\acceptance"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "__pycache__\*,*.pyc"
Source: "..\examples\*"; DestDir: "{app}\examples"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\help\*"; DestDir: "{app}\help"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\schemas\*"; DestDir: "{app}\schemas"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\specification\*"; DestDir: "{app}\specification"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ToolForge starten"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\ToolForge einrichten"; Filename: "{app}\Setup_ToolForge.cmd"; WorkingDir: "{app}"
Name: "{group}\ToolForge beenden"; Filename: "{app}\Stop_ToolForge.cmd"; WorkingDir: "{app}"
Name: "{group}\ToolForge deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ToolForge"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/c ""{app}\Setup_ToolForge.cmd"""; WorkingDir: "{app}"; Description: "ToolForge jetzt einrichten (Python 3.11 oder neuer erforderlich)"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c ""{app}\Stop_ToolForge.cmd"" /quiet"; Flags: runhidden skipifdoesntexist

[Code]
function PythonAvailable(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{cmd}'), '/c python --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
            and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not PythonAvailable() then
  begin
    if MsgBox('Python 3.11 oder neuer wurde nicht gefunden. ToolForge kann installiert werden,'
              + #13#10 + 'die Einrichtung benötigt Python aber später. Trotzdem fortfahren?',
              mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;
