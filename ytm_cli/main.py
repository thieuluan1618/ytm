"""Main entry point and search functionality for YTM CLI"""

import argparse
import curses
import sys
from curses import wrapper

from rich import print

from .config import auth_manager, get_songs_to_display, ytmusic
from .dislikes import dislike_manager
from .player import play_music_with_controls
from .playlists import playlist_manager
from .ui import selection_ui
from .utils import setup_signal_handler

# Global verbose flag
_VERBOSE = False


def verbose_print(*args, **kwargs):
    """Print only if verbose mode is enabled"""
    if _VERBOSE:
        print(*args, **kwargs)


def search_and_play(query=None, auto_select=None):
    """Search for music and start playback

    Args:
        query: Search query string
        auto_select: If set, auto-select this song number (1-based) without UI
    """
    if query is None:
        query = input("🎵 Search for a song: ")
    else:
        print(f"🎵 Searching for: {query}")

    verbose_print(f"[dim]Sending search query to YouTube Music API...[/dim]")
    results = ytmusic.search(query, filter="songs")
    if not results:
        print("[red]No songs found.[/red]")
        return

    verbose_print(f"[dim]Found {len(results)} results[/dim]")

    # Filter out disliked songs
    original_count = len(results)
    results = dislike_manager.filter_disliked_songs(results)
    filtered_count = original_count - len(results)
    if filtered_count > 0:
        verbose_print(f"[dim]Filtered out {filtered_count} disliked song(s)[/dim]")

    if not results:
        print("[red]No songs found after filtering dislikes.[/red]")
        return

    songs_to_display = get_songs_to_display()

    # Non-interactive mode: auto-select specified song
    if auto_select is not None:
        verbose_print(f"[dim]Auto-selecting song #{auto_select}[/dim]")
        selected_index = auto_select - 1  # Convert to 0-based index

        if selected_index < 0 or selected_index >= len(results):
            print(f"[red]Invalid selection {auto_select}. Valid range: 1-{len(results)}[/red]")
            return

        song = results[selected_index]
        title = song["title"]
        artist = song["artists"][0]["name"] if song.get("artists") else "Unknown Artist"
        print(f"[green]✓ Selected:[/green] {title} - {artist}")

    else:
        # Interactive mode: use curses UI
        def ui_wrapper(stdscr):
            return selection_ui(stdscr, results, query, songs_to_display)

        try:
            selected_index = wrapper(ui_wrapper)
        except curses.error as e:
            print(f"[red]Terminal error: {e}[/red]")
            print(
                "[yellow]Try resizing your terminal or using a different terminal emulator.[/yellow]"
            )
            # Fallback to simple numbered selection
            print(f"\n[cyan]Search Results for: {query}[/cyan]")
            for i, song in enumerate(results[:songs_to_display]):
                title = song["title"]
                artist = song["artists"][0]["name"]
                print(f"[{i + 1}] {title} - {artist}")

            try:
                choice = input("\nEnter song number (or 'q' to quit): ").strip()
                if choice.lower() == "q":
                    return
                selected_index = int(choice) - 1
                if selected_index < 0 or selected_index >= len(results[:songs_to_display]):
                    print("[red]Invalid selection.[/red]")
                    return
            except (ValueError, KeyboardInterrupt):
                return

        if selected_index is None:
            return

    song = results[selected_index]
    playlist = [song]

    print("\n[yellow]🎶 Fetching Radio...[/yellow]")
    verbose_print(f"[dim]Fetching radio playlist for videoId: {song['videoId']}[/dim]")
    try:
        radio = ytmusic.get_watch_playlist(videoId=song["videoId"])
        radio_tracks = radio["tracks"][1:]  # Skip first track (the selected song)
        verbose_print(f"[dim]Radio returned {len(radio_tracks)} tracks[/dim]")

        # Filter out disliked songs from radio
        original_radio_count = len(radio_tracks)
        filtered_radio = dislike_manager.filter_disliked_songs(radio_tracks)
        filtered_radio_count = original_radio_count - len(filtered_radio)

        if filtered_radio_count > 0:
            verbose_print(f"[dim]Filtered out {filtered_radio_count} disliked song(s) from radio[/dim]")

        playlist.extend(filtered_radio)
        verbose_print(f"[dim]Final playlist: {len(playlist)} tracks[/dim]")
    except Exception as e:
        print(f"[red]Error fetching radio: {e}[/red]")
        verbose_print(f"[dim]Exception details: {str(e)}[/dim]")

    play_music_with_controls(playlist)


def show_oauth_manual():
    """Show detailed OAuth setup manual"""
    print("\n[cyan]📚 OAuth Authentication Setup Manual[/cyan]")
    print("=" * 60)

    print("\n[yellow]🎯 What is OAuth Authentication?[/yellow]")
    print("OAuth provides secure, long-term access to YouTube Music without")
    print("needing to copy browser headers. It's the recommended method.")

    print("\n[yellow]📋 Prerequisites:[/yellow]")
    print("• Google account")
    print("• Access to Google Cloud Console")
    print("• YouTube Music subscription (recommended)")

    print("\n[yellow]🔧 Step-by-Step Setup:[/yellow]")

    print("\n[cyan]Step 1: Create Google Cloud Project[/cyan]")
    print("1. Go to: https://console.cloud.google.com")
    print("2. Click 'Select a project' → 'New Project'")
    print("3. Enter project name (e.g., 'YTM CLI')")
    print("4. Click 'Create'")

    print("\n[cyan]Step 2: Enable YouTube Data API[/cyan]")
    print("1. Go to: https://console.cloud.google.com/apis/library")
    print("2. Search for 'YouTube Data API v3'")
    print("3. Click on it and press 'Enable'")

    print("\n[cyan]Step 3: Create OAuth Credentials[/cyan]")
    print("1. Go to: https://console.cloud.google.com/apis/credentials")
    print("2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
    print("3. If prompted, configure OAuth consent screen:")
    print("   • User Type: External")
    print("   • App name: YTM CLI (or your choice)")
    print("   • User support email: your email")
    print("   • Developer contact: your email")
    print("4. For Application type, select: 'TV and Limited Input devices'")
    print("5. Enter name: 'YTM CLI' (or your choice)")
    print("6. Click 'Create'")

    print("\n[cyan]Step 4: Get Your Credentials[/cyan]")
    print("1. Copy the 'Client ID' (looks like: xxxxx.apps.googleusercontent.com)")
    print("2. Copy the 'Client Secret' (random string)")
    print("3. [Optional] Download the JSON file:")
    print("   • Click 'Download JSON' to save client_secret_*.json")
    print("   • Place it in your project directory for auto-detection")
    print("4. Keep these safe - you'll enter them in the next step")

    print("\n[yellow]⚠️  Important Notes:[/yellow]")
    print("• Keep Client ID and Secret private")
    print("• Don't share oauth.json file")
    print("• OAuth tokens last longer than browser auth")
    print("• You may need to verify your app for production use")

    print("\n[yellow]🔍 Troubleshooting:[/yellow]")
    print("• 'Access blocked' error: Check OAuth consent screen config")
    print("• 'Invalid client' error: Verify Client ID/Secret are correct")
    print("• 'Quota exceeded' error: Check API quotas in Cloud Console")
    print(
        "• 'Google verification process' error: Add test users (see troubleshoot command)"
    )
    print(
        "• App verification required: https://support.google.com/cloud/answer/7454865"
    )
    print(
        "• Run: [cyan]python -m ytm_cli auth troubleshoot[/cyan] for verification help"
    )

    print("\n[yellow]📚 Additional Resources:[/yellow]")
    print("• YouTube Data API docs: https://developers.google.com/youtube/v3")
    print("• OAuth 2.0 guide: https://developers.google.com/identity/protocols/oauth2")
    print(
        "• ytmusicapi docs: https://ytmusicapi.readthedocs.io/en/stable/setup/oauth.html"
    )

    print("\n[green]✅ Ready to continue with OAuth setup![/green]")
    print("After getting your credentials, run:")
    print("[cyan]python -m ytm_cli auth setup-oauth[/cyan]")
    print("\n[yellow]💡 Pro Tip:[/yellow]")
    print("If you downloaded the JSON file, just place it in your project")
    print("directory as 'client_secret_*.json' for automatic detection!")
    print("=" * 60)


def setup_oauth_command(open_browser=True):
    """Setup OAuth authentication"""
    print("\n[cyan]OAuth Authentication Setup[/cyan]")

    # First, scan for credential files
    print("[yellow]Scanning for credential files...[/yellow]")
    credential_files = auth_manager.scan_for_credential_files()

    client_id = None
    client_secret = None

    if credential_files:
        print(f"[green]Found {len(credential_files)} credential file(s)![/green]")

        # Try to use a credential file
        selected_creds = auth_manager.select_credential_file(credential_files)
        if selected_creds:
            client_id = selected_creds["client_id"]
            client_secret = selected_creds["client_secret"]
            project_id = selected_creds.get("project_id", "Unknown")

            print(f"[green]Using credentials from file (Project: {project_id})[/green]")
            print(f"Client ID: {client_id[:20]}...")

            # Confirm before proceeding
            response = input("Proceed with these credentials? (Y/n): ").strip().lower()
            if response == "n":
                client_id = None
                client_secret = None

    # If no credentials from file, ask for manual input
    if not client_id or not client_secret:
        print("\n[yellow]Manual credential entry required.[/yellow]")

        # Ask if user wants to see the manual
        show_manual = input("Show detailed setup manual? (y/N): ").strip().lower()
        if show_manual == "y":
            show_oauth_manual()
            input("\nPress Enter to continue with setup...")

        print("\nYou need YouTube Data API credentials from Google Cloud Console.")
        print("See: https://developers.google.com/youtube/registering_an_application")
        print("Or use the manual above for detailed instructions.\n")

        if open_browser:
            response = (
                input("Open Google Cloud Console in browser? (Y/n): ").strip().lower()
            )
            if response != "n":
                try:
                    import webbrowser

                    print("[yellow]Opening Google Cloud Console...[/yellow]")
                    webbrowser.open("https://console.cloud.google.com/apis/credentials")
                    print("[green]Browser opened![/green]")
                except Exception as e:
                    print(f"[red]Could not open browser: {e}[/red]")
                    print(
                        "Please manually open: https://console.cloud.google.com/apis/credentials"
                    )

        print("\n[yellow]Enter your OAuth credentials:[/yellow]")
        client_id = input("Client ID: ").strip()
        if not client_id:
            print("[red]Client ID is required[/red]")
            return

        client_secret = input("Client Secret: ").strip()
        if not client_secret:
            print("[red]Client Secret is required[/red]")
            return

    print("\n[yellow]Setting up OAuth authentication...[/yellow]")
    success = auth_manager.setup_oauth_auth(client_id, client_secret, open_browser)

    if success:
        print("\n[green]🎉 OAuth setup complete![/green]")
        print("You can now use YouTube Music with authenticated access.")
        print("Your credentials are saved in 'oauth.json'")
    else:
        print("\n[red]❌ OAuth setup failed.[/red]")
        print("Common solutions:")
        print("• Verification error: [cyan]python -m ytm_cli auth troubleshoot[/cyan]")
        print("• Quick alternative: [cyan]python -m ytm_cli auth setup-browser[/cyan]")
        print("• Retry OAuth: [cyan]python -m ytm_cli auth setup-oauth[/cyan]")


def setup_browser_command(open_browser=True):
    """Setup browser authentication"""
    auth_manager.setup_browser_auth_interactive(open_browser)


def auth_status_command():
    """Show authentication status"""
    status = auth_manager.get_auth_status()

    print("\n[cyan]Authentication Status[/cyan]")
    print(f"Enabled: {'[green]Yes[/green]' if status['enabled'] else '[red]No[/red]'}")
    print(f"Method: [yellow]{status['method']}[/yellow]")

    if status["method"] == "oauth":
        print(
            f"OAuth file: {'[green]Found[/green]' if status['oauth_file_exists'] else '[red]Missing[/red]'}"
        )
    elif status["method"] == "browser":
        print(
            f"Browser file: {'[green]Found[/green]' if status['browser_file_exists'] else '[red]Missing[/red]'}"
        )

    print()


def scan_credentials_command():
    """Scan for credential files"""
    print("\n[cyan]Credential File Scanner[/cyan]")
    print("[yellow]Scanning for Google Cloud credential files...[/yellow]")

    credential_files = auth_manager.scan_for_credential_files()

    if not credential_files:
        print("[red]No credential files found.[/red]")
        print("\nLooking for files matching these patterns:")
        print("• client_secret*.json")
        print("• auth/client_secret*.json")
        print("• credentials/client_secret*.json")
        print("• *client_secret*.json")
        print(
            "\n[yellow]💡 Download your credentials from Google Cloud Console[/yellow]"
        )
        print("and save as 'client_secret_*.json' in your project directory.")
    else:
        print(f"[green]Found {len(credential_files)} credential file(s):[/green]\n")

        for i, (file_path, creds) in enumerate(credential_files, 1):
            project_id = creds.get("project_id", "Unknown")
            client_id = creds["client_id"]

            print(f"[{i}] [cyan]{file_path}[/cyan]")
            print(f"    Project ID: {project_id}")
            print(f"    Client ID: {client_id[:50]}...")
            print()

        print("[green]✅ All files are ready for OAuth setup![/green]")
        print("Run: [cyan]python -m ytm_cli auth setup-oauth[/cyan]")


def show_oauth_troubleshoot():
    """Show OAuth verification troubleshooting guide"""
    print("\n[red]🚨 OAuth Verification Error Troubleshooting[/red]")
    print("=" * 60)

    print(
        "\n[yellow]❌ Error: 'YTM CLI has not completed the Google verification process'[/yellow]"
    )
    print("This is normal for new OAuth applications and can be fixed!")

    print("\n[cyan]🔧 Solution 1: Add Test Users (Recommended for Personal Use)[/cyan]")
    print("1. Go to: https://console.cloud.google.com/apis/credentials/consent")
    print("2. Click 'EDIT APP' on your OAuth consent screen")
    print("3. Go to 'Test users' section")
    print("4. Click '+ ADD USERS'")
    print("5. Add your Gmail address (and any other users who need access)")
    print("6. Click 'SAVE'")
    print("7. Try OAuth setup again")

    print("\n[yellow]📝 Important: Test users can access unverified apps[/yellow]")
    print("• Up to 100 test users allowed")
    print("• Perfect for personal or small team use")
    print("• No verification process needed")

    print("\n[cyan]🔧 Solution 2: Set App as Internal (Google Workspace Users)[/cyan]")
    print("1. Go to: https://console.cloud.google.com/apis/credentials/consent")
    print("2. Click 'EDIT APP'")
    print("3. Change 'User Type' from 'External' to 'Internal'")
    print("4. Click 'SAVE'")
    print("5. Only works if you have Google Workspace domain")

    print("\n[cyan]🔧 Solution 3: App Verification (For Public Distribution)[/cyan]")
    print("1. Go to: https://console.cloud.google.com/apis/credentials/consent")
    print("2. Complete all required fields in OAuth consent screen")
    print("3. Submit for verification (takes 1-6 weeks)")
    print("4. Required for public apps with >100 users")

    print("\n[yellow]🎯 Quick Fix for Personal Use:[/yellow]")
    print("1. Add your Gmail as a test user (Solution 1)")
    print("2. Use browser authentication as alternative")
    print("   Run: [cyan]python -m ytm_cli auth setup-browser[/cyan]")

    print("\n[yellow]⚠️  Alternative: Browser Authentication[/yellow]")
    print("If OAuth continues to fail, browser authentication works immediately:")
    print("• No Google verification needed")
    print("• Uses your browser session cookies")
    print("• Valid for ~2 years")
    print("• Run: [cyan]python -m ytm_cli auth setup-browser[/cyan]")

    print("\n[green]✅ After fixing, try OAuth setup again:[/green]")
    print("[cyan]python -m ytm_cli auth setup-oauth[/cyan]")
    print("=" * 60)


def disable_auth_command():
    """Disable authentication"""
    auth_manager.disable_auth()


# Playlist Commands


def playlist_list_command():
    """List all playlists"""
    playlists = playlist_manager.list_playlists()

    if not playlists:
        print("[yellow]No playlists found.[/yellow]")
        print(
            "Create your first playlist: [cyan]python -m ytm_cli playlist create[/cyan]"
        )
        return

    print(f"\n[cyan]📁 Local Playlists ({len(playlists)} found)[/cyan]")
    print("=" * 60)

    for i, playlist in enumerate(playlists, 1):
        name = playlist["name"]
        song_count = playlist["song_count"]
        description = playlist["description"]
        created_at = (
            playlist["created_at"][:10] if playlist["created_at"] else "Unknown"
        )

        print(f"\n[{i}] [yellow]{name}[/yellow]")
        print(f"    Songs: {song_count}")
        if description:
            print(f"    Description: {description}")
        print(f"    Created: {created_at}")

    print("\n[green]💡 Commands:[/green]")
    print("• [cyan]python -m ytm_cli playlist show <name>[/cyan] - View playlist songs")
    print("• [cyan]python -m ytm_cli playlist play <name>[/cyan] - Play a playlist")
    print("• [cyan]python -m ytm_cli playlist delete <name>[/cyan] - Delete a playlist")


def playlist_create_command(name, description=""):
    """Create a new playlist"""
    if not name:
        name = input("Enter playlist name: ").strip()
        if not name:
            print("[red]Playlist name is required[/red]")
            return

    if not description:
        description = input("Enter description (optional): ").strip()

    playlist_manager.create_playlist(name, description)


def playlist_show_command(name):
    """Show songs in a playlist"""
    if not name:
        # List available playlists for selection
        playlists = playlist_manager.get_playlist_names()
        if not playlists:
            print("[red]No playlists found[/red]")
            return

        # If only one playlist exists, auto-select it (keep music simple!)
        if len(playlists) == 1:
            name = playlists[0]
            print(f"[cyan]Showing playlist: {name}[/cyan]")
        else:
            print("[cyan]Available playlists:[/cyan]")
            for i, playlist_name in enumerate(playlists, 1):
                print(f"[{i}] {playlist_name}")

            try:
                choice = input("\nSelect playlist number or name: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(playlists):
                        name = playlists[index]
                    else:
                        print("[red]Invalid selection[/red]")
                        return
                else:
                    name = choice
            except (ValueError, KeyboardInterrupt):
                return

    playlist = playlist_manager.get_playlist(name)
    if not playlist:
        print(f"[red]Playlist '{name}' not found[/red]")
        return

    songs = playlist.get("songs", [])

    print(f"\n[cyan]🎵 Playlist: {playlist['name']}[/cyan]")
    if playlist.get("description"):
        print(f"Description: {playlist['description']}")
    print(f"Songs: {len(songs)}")
    print("=" * 60)

    if not songs:
        print("[yellow]No songs in this playlist[/yellow]")
        print("Add songs by searching and pressing 'a' during selection!")
        return

    for i, song in enumerate(songs, 1):
        title = song.get("title", "Unknown")
        artist = song.get("artist", "Unknown Artist")
        duration = song.get("duration", "")
        added_at = song.get("added_at", "")[:10] if song.get("added_at") else ""

        print(f"[{i:2d}] {title} - {artist}")
        if duration:
            print(f"     Duration: {duration}")
        if added_at:
            print(f"     Added: {added_at}")
        print()


def playlist_play_command(name):
    """Play a playlist"""
    if not name:
        # List available playlists for selection
        playlists = playlist_manager.get_playlist_names()
        if not playlists:
            print("[red]No playlists found[/red]")
            return

        # If only one playlist exists, auto-select it (keep music simple!)
        if len(playlists) == 1:
            name = playlists[0]
            print(f"[cyan]Playing playlist: {name}[/cyan]")
        else:
            print("[cyan]Available playlists:[/cyan]")
            for i, playlist_name in enumerate(playlists, 1):
                print(f"[{i}] {playlist_name}")

            try:
                choice = input("\nSelect playlist number or name: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(playlists):
                        name = playlists[index]
                    else:
                        print("[red]Invalid selection[/red]")
                        return
                else:
                    name = choice
            except (ValueError, KeyboardInterrupt):
                return

    playlist = playlist_manager.get_playlist(name)
    if not playlist:
        print(f"[red]Playlist '{name}' not found[/red]")
        return

    songs = playlist.get("songs", [])
    if not songs:
        print(f"[yellow]Playlist '{name}' is empty[/yellow]")
        return

    print(
        f"[green]🎵 Playing playlist: {playlist['name']} ({len(songs)} songs)[/green]"
    )

    # Convert playlist songs to format expected by player
    playable_songs = []
    for song in songs:
        if song.get("videoId"):
            # Create a song object compatible with ytmusicapi format
            playable_song = {
                "title": song.get("title", "Unknown"),
                "artists": [{"name": song.get("artist", "Unknown Artist")}],
                "videoId": song["videoId"],
                "duration_seconds": song.get("duration", ""),
                "album": {"name": song.get("album", "")} if song.get("album") else None,
            }
            playable_songs.append(playable_song)

    # Filter out disliked songs
    playable_songs = dislike_manager.filter_disliked_songs(playable_songs)

    if not playable_songs:
        print("[red]No playable songs found in playlist after filtering dislikes[/red]")
        return

    # Start playback with playlist context
    play_music_with_controls(playable_songs, playlist_name=name)


def playlist_delete_command(name):
    """Delete a playlist"""
    if not name:
        # List available playlists for selection
        playlists = playlist_manager.get_playlist_names()
        if not playlists:
            print("[red]No playlists found[/red]")
            return

        # For deletion, still show selection even with one playlist (safety)
        # but make it clearer if there's only one option
        if len(playlists) == 1:
            print(f"[cyan]Only playlist available: {playlists[0]}[/cyan]")
            name = playlists[0]
        else:
            print("[cyan]Available playlists:[/cyan]")
            for i, playlist_name in enumerate(playlists, 1):
                print(f"[{i}] {playlist_name}")

            try:
                choice = input("\nSelect playlist number or name to delete: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(playlists):
                        name = playlists[index]
                    else:
                        print("[red]Invalid selection[/red]")
                        return
                else:
                    name = choice
            except (ValueError, KeyboardInterrupt):
                return

    # Confirm deletion
    confirm = input(f"Delete playlist '{name}'? (y/N): ").strip().lower()
    if confirm != "y":
        print("Deletion cancelled")
        return

    playlist_manager.delete_playlist(name)


def main():
    """Main CLI entry point"""
    global _VERBOSE
    setup_signal_handler()

    # Handle backward compatibility first by checking command line arguments
    # But we need to check for flags first
    if (
        len(sys.argv) >= 2
        and not sys.argv[1].startswith("-")
        and sys.argv[1] not in ["search", "auth", "playlist"]
        and "--verbose" not in sys.argv
        and "--select" not in sys.argv
    ):
        # This is likely a song query, handle it directly (backward compatible mode)
        search_and_play(sys.argv[1])
        return

    parser = argparse.ArgumentParser(
        description="YouTube Music CLI 🎧 - Search, play, and organize music from YouTube Music",
        epilog="""
Examples:
  %(prog)s "bohemian rhapsody"                    Search and play music
  %(prog)s "phung khanh linh" --select 1          Auto-select first result
  %(prog)s "beatles" --select 2 --verbose         Auto-select with detailed logging
  %(prog)s playlist list                          List all local playlists
  %(prog)s playlist create "Rock Hits"            Create a new playlist
  %(prog)s auth setup-oauth                       Setup OAuth authentication

During song selection:
  • Enter: Play selected song with radio
  • a: Add song to playlist
  • q: Quit to search
  • ↑↓ or j/k: Navigate

During music playback:
  • ⏯️ space: Play/pause
  • ⏭️ n: Next song, ⏮️ b: Previous song
  • 📜 l: Show lyrics, ➕ a: Add to playlist, 👎 d: Dislike (playlist: remove first, then global)
  • 🚪 q: Quit to search
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options (available for all commands)
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        description="Main commands for the YouTube Music CLI",
    )

    # Search command (explicit)
    search_parser = subparsers.add_parser(
        "search",
        help="Search and play music",
        description="Search YouTube Music and play songs with radio playlists",
    )
    search_parser.add_argument(
        "search_query", nargs="?", help="Song, artist, or album to search for"
    )
    search_parser.add_argument(
        "--select", "-s",
        type=int,
        metavar="N",
        help="Auto-select song number N (1-based, non-interactive mode)"
    )
    search_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )

    # Auth commands
    auth_parser = subparsers.add_parser(
        "auth",
        help="Authentication management",
        description="Manage YouTube Music authentication for personalized features",
    )
    auth_subparsers = auth_parser.add_subparsers(
        dest="auth_command", help="Authentication commands"
    )

    oauth_parser = auth_subparsers.add_parser(
        "setup-oauth",
        help="Setup OAuth authentication (recommended)",
        description="Setup OAuth authentication using Google Cloud credentials",
    )
    oauth_parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    browser_parser = auth_subparsers.add_parser(
        "setup-browser",
        help="Setup browser authentication (alternative)",
        description="Setup authentication using browser headers (no Google verification needed)",
    )
    browser_parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    auth_subparsers.add_parser("manual", help="Show detailed OAuth setup guide")
    auth_subparsers.add_parser("scan", help="Scan for Google Cloud credential files")
    auth_subparsers.add_parser(
        "troubleshoot", help="OAuth verification troubleshooting guide"
    )
    auth_subparsers.add_parser("status", help="Show current authentication status")
    auth_subparsers.add_parser(
        "disable", help="Disable authentication and use guest access"
    )

    # Playlist commands
    playlist_parser = subparsers.add_parser(
        "playlist",
        help="Local playlist management",
        description='Create and manage local playlists. Add songs during search by pressing "a".',
    )
    playlist_subparsers = playlist_parser.add_subparsers(
        dest="playlist_command", help="Playlist operations"
    )

    playlist_subparsers.add_parser(
        "list",
        help="List all local playlists",
        description="Show all created playlists with song counts and metadata",
    )

    create_parser = playlist_subparsers.add_parser(
        "create",
        help="Create a new playlist",
        description="Create a new local playlist with optional description",
    )
    create_parser.add_argument(
        "name", nargs="?", help="Playlist name (prompted if not provided)"
    )
    create_parser.add_argument(
        "-d", "--description", help="Optional playlist description"
    )

    show_parser = playlist_subparsers.add_parser(
        "show",
        help="Show songs in a playlist",
        description="Display all songs in a playlist with details",
    )
    show_parser.add_argument(
        "name", nargs="?", help="Playlist name (select from list if not provided)"
    )

    play_parser = playlist_subparsers.add_parser(
        "play",
        help="Play a playlist",
        description="Start playback of all songs in a playlist",
    )
    play_parser.add_argument(
        "name", nargs="?", help="Playlist name (select from list if not provided)"
    )

    delete_parser = playlist_subparsers.add_parser(
        "delete",
        help="Delete a playlist",
        description="Permanently delete a playlist and all its songs",
    )
    delete_parser.add_argument(
        "name", nargs="?", help="Playlist name (select from list if not provided)"
    )

    args = parser.parse_args()

    # Set verbose mode globally
    _VERBOSE = getattr(args, "verbose", False)

    # Handle auth commands
    if args.command == "auth":
        if args.auth_command == "setup-oauth":
            open_browser = not getattr(args, "no_browser", False)
            setup_oauth_command(open_browser)
        elif args.auth_command == "setup-browser":
            open_browser = not getattr(args, "no_browser", False)
            setup_browser_command(open_browser)
        elif args.auth_command == "manual":
            show_oauth_manual()
        elif args.auth_command == "scan":
            scan_credentials_command()
        elif args.auth_command == "troubleshoot":
            show_oauth_troubleshoot()
        elif args.auth_command == "status":
            auth_status_command()
        elif args.auth_command == "disable":
            disable_auth_command()
        else:
            print(
                "Available auth commands: setup-oauth, setup-browser, manual, scan, troubleshoot, status, disable"
            )
    elif args.command == "playlist":
        if args.playlist_command == "list":
            playlist_list_command()
        elif args.playlist_command == "create":
            playlist_create_command(args.name, args.description or "")
        elif args.playlist_command == "show":
            playlist_show_command(args.name)
        elif args.playlist_command == "play":
            playlist_play_command(args.name)
        elif args.playlist_command == "delete":
            playlist_delete_command(args.name)
        else:
            print("Available playlist commands: list, create, show, play, delete")
    elif args.command == "search":
        auto_select = getattr(args, "select", None)
        search_and_play(args.search_query, auto_select=auto_select)
    else:
        # Default behavior: if no command specified, prompt for search
        search_and_play()


if __name__ == "__main__":
    main()
