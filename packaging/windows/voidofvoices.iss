; Instalador de Windows (Inno Setup 6.7+). Uso: iscc /DAppVersion=0.2.0 packaging\windows\voidofvoices.iss
; Instala la app y, si falta, descarga VB-Cable de su web oficial y abre su instalador
; al terminar (su licencia no permite incluirlo dentro de este instalador).
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define VBCableUrl "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
#define VBCableSha256 "b950e39f01af1d04ea623c8f6d8eb9b6ea5c477c637295fabf20631c85116bfb"

[Setup]
AppId={{6B0C8F7E-4A43-4C55-9C1E-56A0D2C7B0E1}
AppName=Void of Voices
AppVersion={#AppVersion}
AppPublisher=daetrox
AppPublisherURL=https://github.com/daetrox/void-of-voices
DefaultDirName={localappdata}\Programs\VoidOfVoices
DefaultGroupName=Void of Voices
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..
OutputBaseFilename=VoidOfVoices-{#AppVersion}-Windows-Setup
SetupIconFile=..\..\voidofvoices\assets\icon.ico
UninstallDisplayIcon={app}\VoidOfVoices.exe
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
; Aspecto: oscuro, con el verde de la app (ver art\banner.svg).
WizardStyle=modern dark hidebevels
WizardBackColor=#17181a
WizardImageFile=art\banner.png,art\banner@2x.png
WizardSmallImageFile=art\small.png,art\small@2x.png
; ExtractArchive con .zip (el paquete de VB-Cable).
ArchiveExtraction=full

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
es.VBCableTask=Instalar el micrófono virtual (VB-Cable, gratis, de VB-Audio)
en.VBCableTask=Install the virtual microphone (VB-Cable, free, by VB-Audio)
es.VBCableGroup=Necesario para que Discord, OBS y los juegos oigan tu voz modificada:
en.VBCableGroup=Needed so Discord, OBS and games can hear your modified voice:
es.VBCableRunning=Abriendo el instalador del micrófono virtual: pulsa «Install Driver»…
en.VBCableRunning=Opening the virtual microphone installer: click "Install Driver"…
es.VBCableFailed=No se pudo descargar VB-Cable (%1). Void of Voices se instalará igual; podrás instalarlo luego desde la app.
en.VBCableFailed=Could not download VB-Cable (%1). Void of Voices will be installed anyway; you can install it later from the app.

[Tasks]
Name: "vbcable"; Description: "{cm:VBCableTask}"; GroupDescription: "{cm:VBCableGroup}"; Check: not VBCableInstalled
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\VoidOfVoices\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Void of Voices"; Filename: "{app}\VoidOfVoices.exe"
Name: "{autodesktop}\Void of Voices"; Filename: "{app}\VoidOfVoices.exe"; Tasks: desktopicon

[Run]
; Primero el micrófono virtual (pide permisos de administrador), después abrir la app.
Filename: "{tmp}\vbcable\VBCABLE_Setup_x64.exe"; WorkingDir: "{tmp}\vbcable"; Verb: "runas"; \
  Flags: shellexec waituntilterminated; StatusMsg: "{cm:VBCableRunning}"; Tasks: vbcable; Check: VBCableDownloaded
Filename: "{app}\VoidOfVoices.exe"; Description: "{cm:LaunchProgram,Void of Voices}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DownloadPage: TDownloadWizardPage;

function VBCableInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{sys}\drivers\vbaudio_cable64_win10.sys'));
end;

function VBCableDownloaded: Boolean;
begin
  Result := FileExists(ExpandConstant('{tmp}\vbcable\VBCABLE_Setup_x64.exe'));
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID <> wpReady) or not WizardIsTaskSelected('vbcable') then
    Exit;
  DownloadPage.Clear;
  // La huella SHA-256 garantiza que se ejecuta el instalador publicado por VB-Audio.
  DownloadPage.Add('{#VBCableUrl}', 'vbcable.zip', '{#VBCableSha256}');
  DownloadPage.Show;
  try
    try
      DownloadPage.Download;
      ExtractArchive(ExpandConstant('{tmp}\vbcable.zip'), ExpandConstant('{tmp}\vbcable'), '', True, nil);
    except
      // Sin VB-Cable la app se instala igual (tiene su propio botón para instalarlo).
      if not DownloadPage.AbortedByUser then
        SuppressibleMsgBox(FmtMessage(CustomMessage('VBCableFailed'), [GetExceptionMessage]),
          mbError, MB_OK, IDOK);
    end;
  finally
    DownloadPage.Hide;
  end;
end;
