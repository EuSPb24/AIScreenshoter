#define MyAppName "AIScreenshoter"
#define MyAppVersion "1.2.4"
#define MyAppPublisher "EvGen & Gemini AI Assistant"
#define MyAppExeName "AIScreenshoter.exe"

[Setup]
AppId={{8F4A92C1-5B3E-4D7A-9C12-3E8F1A0B4D6E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist_setup
OutputBaseFilename=AIScreenshoter_Setup_{#MyAppVersion}
SetupIconFile=app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
ShowLanguageDialog=auto
AppMutex=Global\AIScreenshoter_SingleInstance_Mutex
AppPublisherURL=https://github.com/EuSPb24/AIScreenshoter

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
english.StartupTask=Launch {#MyAppName} automatically when Windows starts
english.StartupGroup=Startup:
english.AssocTask=Open .ai project files by double-clicking in {#MyAppName}
english.AssocGroup=File associations:

russian.StartupTask=Запускать {#MyAppName} автоматически при входе в Windows
russian.StartupGroup=Автозагрузка:
russian.AssocTask=Открывать файлы проектов .ai двойным кликом в {#MyAppName}
russian.AssocGroup=Ассоциации файлов:

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "{cm:StartupTask}"; GroupDescription: "{cm:StartupGroup}"
Name: "assoc_ai"; Description: "{cm:AssocTask}"; GroupDescription: "{cm:AssocGroup}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

Root: HKCU; Subkey: "Software\Classes\.ai"; ValueType: string; ValueName: ""; ValueData: "AIScreenshoter.Project"; Flags: uninsdeletevalue; Tasks: assoc_ai
Root: HKCU; Subkey: "Software\Classes\AIScreenshoter.Project"; ValueType: string; ValueName: ""; ValueData: "AIScreenshoter Project File"; Flags: uninsdeletekey; Tasks: assoc_ai
Root: HKCU; Subkey: "Software\Classes\AIScreenshoter.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"",0"; Tasks: assoc_ai
Root: HKCU; Subkey: "Software\Classes\AIScreenshoter.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: assoc_ai

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im AIScreenshoter.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im AIScreenshoter.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
