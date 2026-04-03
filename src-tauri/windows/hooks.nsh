!macro NSIS_HOOK_PREINSTALL
  nsExec::ExecToLog 'taskkill /F /T /IM dictover-sidecar.exe'
  Pop $3
  Sleep 500
!macroend

!macro NSIS_HOOK_POSTINSTALL
  StrCpy $0 "$LOCALAPPDATA\\DictoverDesktop"
  StrCpy $1 "$0\\install-ping-version.flag"
  CreateDirectory "$0"

  ; Per-version marker: ping once per installed version. Updating to a new
  ; version triggers a new ping and overwrites the stored marker.

  DetailPrint "Sending installation ping to langochung.me..."
  ExecWait "$\"$WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe$\" -NoProfile -ExecutionPolicy Bypass -Command $\"$$ErrorActionPreference='Stop';$$u='https://langochung.me/api/ping/dictover-desktop';$$v='${VERSION}';$$m='$1';if(Test-Path $$m){try{$$prev=(Get-Content $$m -ErrorAction Stop|Select-Object -First 1).Trim();if($$prev -eq $$v){exit 0}}catch{}};$$t=(Get-Date).ToUniversalTime().ToString('o');$$b=@{user_id=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;user_name=$$env:USERNAME;app_name='dictover-desktop';installed_at=$$t;version=$$v}|ConvertTo-Json -Compress;for($$i=0;$$i -lt 3;$$i++){try{irm -Method Post -Uri $$u -ContentType 'application/json' -Body $$b -TimeoutSec 10|Out-Null;Set-Content -Path $$m -Value $$v -Encoding UTF8;exit 0}catch{Start-Sleep -Seconds 2}};exit 1$\"" $2

  StrCmp $2 0 ping_success ping_failed

  ping_success:
    DetailPrint "Install ping sent successfully."
    Goto ping_done

  ping_failed:
    DetailPrint "Install ping failed. Will retry on next install attempt."

  ping_done:
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::ExecToLog 'taskkill /F /T /IM dictover-sidecar.exe'
  Pop $3
  Sleep 500
!macroend
