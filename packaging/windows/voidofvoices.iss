; Instalador de Windows (Inno Setup 6). Uso: iscc /DAppVersion=0.2.0 packaging\windows\voidofvoices.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B0C8F7E-4A43-4C55-9C1E-56A0D2C7B0E1}
AppName=Void of Voices
AppVersion={#AppVersion}
AppPublisher=daetrox
AppPublisherURL=https://github.com/daetrox/void-of-voices
DefaultDirName={localappdata}\Programs\VoidOfVoices
DefaultGroupName=Void of Voices
PrivilegesRequired=lowest
OutputDir=..\..
OutputBaseFilename=VoidOfVoices-{#AppVersion}-Windows-Setup
SetupIconFile=..\..\voidofvoices\assets\icon.ico
UninstallDisplayIcon={app}\VoidOfVoices.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\VoidOfVoices\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Void of Voices"; Filename: "{app}\VoidOfVoices.exe"
Name: "{autodesktop}\Void of Voices"; Filename: "{app}\VoidOfVoices.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VoidOfVoices.exe"; Description: "{cm:LaunchProgram,Void of Voices}"; Flags: nowait postinstall skipifsilent
