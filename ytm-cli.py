from ytmusicapi import YTMusic
from rich import print
import subprocess
import time

def play_song(video_id, title):
    url = f"https://music.youtube.com/watch?v={video_id}"
    print(f"[green]▶️ Playing: {title}[/green]")
    subprocess.run(["mpv", url])

def search_and_play():
    query = input("🎵 Search for a song: ")
    ytmusic = YTMusic()

    results = ytmusic.search(query, filter="songs")
    if not results:
        print("[red]Không tìm thấy bài nào.[/red]")
        return

    for i, song in enumerate(results[:5]):
        title = song['title']
        artist = song['artists'][0]['name']
        print(f"[{i}] {title} - {artist}")

    choice = int(input("🎧 Choose a song to play (0-4): "))
    song = results[choice]
    video_id = song['videoId']
    title = f"{song['title']} - {song['artists'][0]['name']}"

    # Phát bài đầu tiên
    play_song(video_id, title)

    # Sau khi xong → phát radio list tiếp theo
    print("[yellow]🎶 Starting Radio...[/yellow]")
    radio = ytmusic.get_watch_playlist(videoId=video_id)
    for item in radio['tracks'][1:]:
        next_id = item['videoId']
        next_title = f"{item['title']} - {item['artists'][0]['name']}"
        play_song(next_id, next_title)

if __name__ == "__main__":
    search_and_play()
