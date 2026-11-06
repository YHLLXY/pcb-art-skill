$exe="F:\嘉立创\lceda-pro\lceda-pro.exe"
$sid="558395c1-d175-4f26-861f-06d89835a77d"
$dir="E:/homework/开发/嘉立创电路板开发/skill测试/gen"
$log="C:/Users/32447/AppData/Local/Temp/dsh/apply_cq.log"
"" | Out-File -Encoding utf8 $log
$i=0
foreach($f in (Get-Content "C:/Users/32447/AppData/Local/Temp/dsh/order_cq.txt")){
  if(-not $f){ continue }
  $i++
  $ok=$false
  for($t=1; $t -le 3 -and -not $ok; $t++){
    $c = Get-Content -Raw -Encoding UTF8 (Join-Path $dir $f)
    $out = (& $exe invoke --ext-uuid eda --session $sid --code $c 2>&1 | Out-String).Trim()
    if($out -match '"ok":true'){ $ok=$true }
    else {
      $c0 = Get-Content -Raw "C:/Users/32447/AppData/Local/Temp/dsh/open_cq.js"
      (& $exe invoke --ext-uuid eda --session $sid --code $c0 2>&1 | Out-String) | Out-Null
      Start-Sleep -Seconds 2
    }
    $snip=$out; if($snip.Length -gt 60){ $snip=$snip.Substring(0,60) }
    ($i.ToString()+"/") | Out-Null
    ($f + " try" + $t + " " + $snip) | Out-File -Append -Encoding utf8 $log
    Start-Sleep -Milliseconds 900
  }
}
"DONECQ" | Out-File -Append -Encoding utf8 $log