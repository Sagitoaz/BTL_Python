Param(
  [string]$Server = "http://100.109.118.90:9000",
  [string]$Token  = "5conmeo"
)

Write-Host "[Start quick-test]" -ForegroundColor Yellow

Write-Host "== /health ==" -ForegroundColor Cyan
Invoke-RestMethod "$Server/health" | ConvertTo-Json -Depth 8

$headers = @{ Authorization = "Bearer $Token" }

Write-Host "== /models ==" -ForegroundColor Cyan
Invoke-RestMethod "$Server/models" -Headers $headers | ConvertTo-Json -Depth 8

Write-Host "== /complete (sync) ==" -ForegroundColor Cyan
$body = @{
  prefix      = "def two_sum(nums, target):`n    "
  suffix      = "`n"
  language    = "python"
  max_tokens  = 64
  temperature = 0.2
} | ConvertTo-Json
Invoke-RestMethod "$Server/complete" -Headers $headers -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8

Write-Host "== /complete_stream (SSE) ==" -ForegroundColor Cyan
$req = [System.Net.HttpWebRequest]::Create("$Server/complete_stream")
$req.Method = "POST"
$req.Headers.Add("Authorization", "Bearer $Token")
$req.ContentType = "application/json"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$req.ContentLength = $bytes.Length
$stream = $req.GetRequestStream(); $stream.Write($bytes,0,$bytes.Length); $stream.Close()
$resp = $req.GetResponse(); $rs = $resp.GetResponseStream()
$sr = New-Object System.IO.StreamReader($rs, [System.Text.Encoding]::UTF8)
while (($line = $sr.ReadLine()) -ne $null) { if ($line.Trim().Length -gt 0) { $line } }
$sr.Close(); $resp.Close()

Write-Host "[Done]" -ForegroundColor Yellow
