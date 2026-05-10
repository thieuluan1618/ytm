# vhs tape — player UI with synthetic spectrum visualizer
# Run locally: vhs screenshots/player.tape
# Run in CI: charmbracelet/vhs-action@v2 with path=screenshots/player.tape

Output screenshots/player.gif
Output screenshots/player.png
Output screenshots/player.webm

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
Sleep 4s

# Pause/resume to capture both states
Type " "
Sleep 1s
Type " "
Sleep 2s

# Skip to next track
Type "n"
Sleep 3s

# Quit cleanly
Type "q"
Sleep 500ms
