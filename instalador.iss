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
#define MyAppVersion "1.5"
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
; pasta sem número de versão. UsePreviousAppDir=no: sem isso, a atualização reaproveitaria a pasta
; "CX Rays 1.1" da primeira instalação (que é apagada em [InstallDelete])
DefaultDirName={autopf}\{#MyAppName}
UsePreviousAppDir=no
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; fecha o programa, se estiver aberto, antes de substituir os arquivos
CloseApplications=yes
; avisa o Windows no fim da instalação que os ícones mudaram: o .exe fica no mesmo caminho a cada versão
; e, sem isso, o Windows continua mostrando o ícone guardado em cache (o da versão anterior)
ChangesAssociations=yes
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
; pasta da 1.1 (as atualizações seguintes eram instaladas nela)
Type: filesandordirs; Name: "{autopf}\CX Rays 1.1"
; atalhos de versões anteriores ("CX Rays", "CX Rays 1.1", ...): o Inno Setup não apaga atalho que mudou de nome.
; O desta versão é criado depois, em [Icons].
Type: files; Name: "{autoprograms}\{#MyAppName}*.lnk"
Type: files; Name: "{autodesktop}\{#MyAppName}*.lnk"
Type: files; Name: "{userprograms}\{#MyAppName}*.lnk"
Type: files; Name: "{userdesktop}\{#MyAppName}*.lnk"

[Files]
Source: "{#PastaBuild}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; o atalho leva a versão no nome ("CX Rays 1.5"); os das versões anteriores são apagados em [InstallDelete]
Name: "{autoprograms}\{#MyAppName} {#MyAppVersion}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName} {#MyAppVersion}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
