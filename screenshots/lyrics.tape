# vhs tape — lyrics view captured against the demo fixture
# Run locally: vhs screenshots/lyrics.tape
# CI: rendered alongside player.tape by .github/workflows/screenshots.yml

Output screenshots/lyrics.gif
Output screenshots/lyrics.png
Output screenshots/lyrics.webm

Set FontSize 16
Set Width 1300
Set Height 720
Set Padding 30
Set TypingSpeed 40ms
Set Theme "Dracula"

Hide
Type "uv run ytm-cli --demo"
Show

Enter
Sleep 3s

# Open synced lyrics view
Type "l"
Sleep 12s

# Back to player, then quit
Type "q"
Sleep 800ms
Type "q"
Sleep 500ms
