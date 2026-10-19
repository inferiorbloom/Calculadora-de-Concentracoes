; Instalador do CX Rays (Inno Setup 6).
; Gerar: rode build.bat (faz o PyInstaller e depois compila este script), ou abra este arquivo no
; Inno Setup Compiler e clique em Compile. Os caminhos são relativos à pasta deste arquivo.
;
; Para uma versão nova: troque só MyAppVersion. NUNCA troque o AppId: é ele que faz a versão nova
; substituir a anterior (inclusive a 1.1) em vez de instalar outro programa ao lado.
;
; Cadastro de padrões, cores, configuração e log ficam em %APPDATA%\CXCalculator: instalar,
; atualizar ou desinstalar não mexe neles.

#define MyAppName "CX Rays"
#define MyAppVersion "1.2"
#define MyAppPublisher "Cloud Physics"
#define MyAppExeName "CalculadoraConcentracoes.exe"
#define PastaBuild "dist\CalculadoraConcentracoes"

[Setup]
; mesmo AppId do CX Rays 1.1
AppId={{2439FDE6-42C5-4F55-9247-C1E3A2F8329F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
SetupIconFile=imagens\icones\cx_rays.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; numa atualização, o Inno Setup reaproveita a pasta onde a versão anterior foi instalada
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; fecha o programa, se estiver aberto, antes de substituir os arquivos
CloseApplications=yes
OutputDir=instalador
OutputBaseFilename=CX Setup V{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern dynamic

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; arquivos da versão anterior que não existem mais na nova não ficam esquecidos na pasta
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#PastaBuild}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
