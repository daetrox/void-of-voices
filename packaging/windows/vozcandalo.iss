; Instalador de Windows (Inno Setup 6). Uso: iscc /DAppVersion=0.2.0 packaging\windows\vozcandalo.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B0C8F7E-4A43-4C55-9C1E-56A0D2C7B0E1}
AppName=Vozcándalo
AppVersion={#AppVersion}
AppPublisher=daetrox
AppPublisherURL=https://github.com/daetrox/vozcandalo
DefaultDirName={localappdata}\Programs\Vozcandalo
DefaultGroupName=Vozcándalo
PrivilegesRequired=lowest
OutputDir=..\..
OutputBaseFilename=Vozcandalo-{#AppVersion}-Windows-Setup
SetupIconFile=..\..\vozcandalo\assets\icon.ico
UninstallDisplayIcon={app}\Vozcandalo.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
es.VBCable=Para que Discord y otras apps oigan tu voz necesitas el driver gratuito VB-Cable. ¿Abrir su web ahora?
en.VBCable=For Discord and other apps to hear your voice you need the free VB-Cable driver. Open its website now?

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\Vozcandalo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Vozcándalo"; Filename: "{app}\Vozcandalo.exe"
Name: "{autodesktop}\Vozcándalo"; Filename: "{app}\Vozcandalo.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Vozcandalo.exe"; Description: "{cm:LaunchProgram,Vozcándalo}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
begin
  if (CurStep = ssPostInstall) and not WizardSilent then
    if MsgBox(ExpandConstant('{cm:VBCable}'), mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://vb-audio.com/Cable/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;
