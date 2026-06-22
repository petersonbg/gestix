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
OutputDir=Output
OutputBaseFilename=GESTIX_Instalador
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\GESTIX.exe

[Dirs]
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\backups"; Permissions: users-modify
Name: "{app}\media"; Permissions: users-modify
Name: "{app}\staticfiles"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: ".git\*,.venv\*,venv\*,__pycache__\*,*.pyc,backups\*,logs\*,media\*,launcher\build\*,launcher\dist\*,launcher\*.spec,installer\Output\*"
Source: "{#SourceRoot}\launcher\dist\GESTIX.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\config\.env.example"; DestDir: "{app}\config"; DestName: ".env"; Flags: ignoreversion onlyifdoesntexist
Source: "{#SourceRoot}\config\.env.example"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "{#SourceRoot}\scripts\windows\*"; DestDir: "{app}\scripts\windows"; Flags: recursesubdirs ignoreversion
Source: "{#SourceRoot}\docs\INSTALACAO_PRODUCAO_WINDOWS.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#SourceRoot}\docs\CHECKLIST_EMPACOTAMENTO_WINDOWS.md"; DestDir: "{app}\docs"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\GESTIX"; Filename: "{app}\GESTIX.exe"; WorkingDir: "{app}"
Name: "{group}\GESTIX"; Filename: "{app}\GESTIX.exe"; WorkingDir: "{app}"
Name: "{group}\Iniciar GESTIX"; Filename: "{app}\GESTIX.exe"; WorkingDir: "{app}"
Name: "{group}\Conectar ao servidor GESTIX"; Filename: "{app}\GESTIX.exe"; Parameters: "--client"; WorkingDir: "{app}"
Name: "{group}\Parar GESTIX"; Filename: "{app}\scripts\windows\parar_gestix_sem_docker.bat"; WorkingDir: "{app}"
Name: "{group}\Backup"; Filename: "{app}\scripts\windows\backup_banco_sem_docker.bat"; WorkingDir: "{app}"
Name: "{group}\Instalar servico"; Filename: "{app}\scripts\windows\instalar_servico.bat"; WorkingDir: "{app}"
Name: "{group}\Iniciar servico"; Filename: "{app}\scripts\windows\iniciar_servico.bat"; WorkingDir: "{app}"
Name: "{group}\Parar servico"; Filename: "{app}\scripts\windows\parar_servico.bat"; WorkingDir: "{app}"
Name: "{group}\Remover servico"; Filename: "{app}\scripts\windows\remover_servico.bat"; WorkingDir: "{app}"
Name: "{group}\Desinstalar GESTIX"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\GESTIX.exe"; Description: "Iniciar GESTIX agora"; Flags: postinstall skipifsilent unchecked nowait

[Code]
function CommandExists(Command: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(ExpandConstant('{cmd}'), '/C where ' + Command, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not CommandExists('python.exe') and not CommandExists('py.exe') then
  begin
    MsgBox('Python 3.12+ nao foi encontrado no PATH. Instale o Python ou crie uma venv em C:\GESTIX\.venv antes de iniciar o GESTIX.', mbInformation, MB_OK);
  end;

  if not CommandExists('psql.exe') then
  begin
    MsgBox('Cliente PostgreSQL nao foi encontrado no PATH. Instale o PostgreSQL local e adicione a pasta bin ao PATH antes da homologacao final.', mbInformation, MB_OK);
  end;
end;
