#define AppName "GESTIX"
#define AppVersion "1.0.0"
#define AppPublisher "GESTIX"
#define SourceRoot ".."

[Setup]
AppId={{B7D14D6B-3A9F-4D37-8C60-6E57A1000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName=C:\GESTIX
DefaultGroupName={#AppName}
OutputBaseFilename=GESTIX_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: ".git\*,.venv\*,venv\*,__pycache__\*,*.pyc,backups\*,launcher\build\*,launcher\dist\*,launcher\*.spec"
Source: "{#SourceRoot}\launcher\dist\GESTIX.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\docker-compose.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\scripts\windows\*"; DestDir: "{app}\scripts\windows"; Flags: recursesubdirs ignoreversion
Source: "{#SourceRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\GESTIX"; Filename: "{app}\GESTIX.exe"; WorkingDir: "{app}"
Name: "{group}\GESTIX"; Filename: "{app}\GESTIX.exe"; WorkingDir: "{app}"
Name: "{group}\Iniciar GESTIX"; Filename: "{app}\scripts\windows\iniciar_gestix.bat"; WorkingDir: "{app}"
Name: "{group}\Parar GESTIX"; Filename: "{app}\scripts\windows\parar_gestix.bat"; WorkingDir: "{app}"
Name: "{group}\Desinstalar GESTIX"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\scripts\windows\iniciar_gestix.bat"; Description: "Iniciar GESTIX agora"; Flags: postinstall skipifsilent unchecked

[Code]
function DockerDesktopInstalled(): Boolean;
var
  InstallLocation: String;
begin
  Result := False;

  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Docker Desktop', 'InstallLocation', InstallLocation) then
    Result := True;

  if RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Docker Desktop', 'InstallLocation', InstallLocation) then
    Result := True;

  if FileExists(ExpandConstant('{commonpf}\Docker\Docker\Docker Desktop.exe')) then
    Result := True;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not DockerDesktopInstalled() then
  begin
    MsgBox('O GESTIX utiliza Docker Desktop para executar seus serviços. Instale o Docker Desktop antes de iniciar o sistema.', mbInformation, MB_OK);
  end;
end;
