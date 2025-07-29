"""Authentication management for YTM CLI"""

import configparser
import glob
import json
import os
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

from rich import print
from ytmusicapi import YTMusic
from ytmusicapi.setup import setup_oauth

#
try:
    import pyperclip

    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class AuthManager:
    """Manages authentication for YouTube Music API"""

    def __init__(self, config_path: str = "config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        self.oauth_file = "oauth.json"
        self.browser_file = "browser.json"

    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled"""
        return self.config.getboolean("auth", "enabled", fallback=False)

    def get_auth_method(self) -> str:
        """Get the configured authentication method"""
        return self.config.get("auth", "method", fallback="none")

    def scan_for_credential_files(self) -> List[Tuple[str, Dict[str, str]]]:
        """Scan for Google Cloud credential files"""
        credential_files = []

        # Define search patterns
        patterns = [
            "client_secret*.json",
            "auth/client_secret*.json",
            "credentials/client_secret*.json",
            "*client_secret*.json",
        ]

        for pattern in patterns:
            files = glob.glob(pattern)
            for file_path in files:
                try:
                    creds = self.parse_credential_file(file_path)
                    if creds:
                        credential_files.append((file_path, creds))
                except Exception as e:
                    print(f"[yellow]Warning: Could not parse {file_path}: {e}[/yellow]")
                    continue

        # Remove duplicates (same file found by different patterns)
        seen_files = set()
        unique_files = []
        for file_path, creds in credential_files:
            abs_path = os.path.abspath(file_path)
            if abs_path not in seen_files:
                seen_files.add(abs_path)
                unique_files.append((file_path, creds))

        return unique_files

    def parse_credential_file(self, file_path: str) -> Optional[Dict[str, str]]:
        """Parse Google Cloud credential JSON file"""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Handle different credential file formats
            if "installed" in data:
                # Desktop application credentials
                client_info = data["installed"]
            elif "web" in data:
                # Web application credentials
                client_info = data["web"]
            else:
                # Direct format (client_id and client_secret at root level)
                client_info = data

            # Extract required fields
            client_id = client_info.get("client_id")
            client_secret = client_info.get("client_secret")

            if client_id and client_secret:
                # Try to get project_id from different locations
                project_id = (
                    data.get("project_id") or client_info.get("project_id") or "Unknown"
                )
                return {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "project_id": project_id,
                }

            return None

        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return None

    def select_credential_file(
        self, credential_files: List[Tuple[str, Dict[str, str]]]
    ) -> Optional[Dict[str, str]]:
        """Interactive selection of credential file"""
        if not credential_files:
            return None

        if len(credential_files) == 1:
            file_path, creds = credential_files[0]
            print(f"[green]Found credential file: {file_path}[/green]")
            response = input("Use this file? (Y/n): ").strip().lower()
            if response != "n":
                return creds
            return None

        # Multiple files found - let user choose
        print(f"\n[cyan]Found {len(credential_files)} credential files:[/cyan]")
        for i, (file_path, creds) in enumerate(credential_files, 1):
            project_id = creds.get("project_id", "Unknown")
            print(f"[{i}] {file_path} (Project: {project_id})")

        while True:
            try:
                choice = input("\nSelect file number (or 'n' to skip): ").strip()
                if choice.lower() == "n":
                    return None

                index = int(choice) - 1
                if 0 <= index < len(credential_files):
                    return credential_files[index][1]
                else:
                    print("[red]Invalid selection. Please try again.[/red]")
            except ValueError:
                print("[red]Please enter a number or 'n'.[/red]")

    def setup_oauth_auth(
        self, client_id: str, client_secret: str, open_browser: bool = True
    ) -> bool:
        """Setup OAuth authentication"""
        try:
            print("[yellow]Setting up OAuth authentication...[/yellow]")

            # Use ytmusicapi's setup_oauth function
            setup_oauth(
                filepath=self.oauth_file,
                client_id=client_id,
                client_secret=client_secret,
                open_browser=open_browser,
            )

            # Update config
            self._update_auth_config("oauth")
            print("[green]OAuth authentication setup complete![/green]")
            return True

        except Exception as e:
            error_str = str(e).lower()

            # Check for specific OAuth verification error
            if (
                ("verification" in error_str and "process" in error_str)
                or ("access_denied" in error_str)
                or ("not completed" in error_str and "verification" in error_str)
            ):
                print(f"[red]OAuth verification error: {e}[/red]")
                print("\n[yellow]🚨 This is a Google verification issue![/yellow]")
                print("Your OAuth app needs to add test users or be verified.")
                print(
                    "Run: [cyan]python -m ytm_cli auth troubleshoot[/cyan] for solutions"
                )
                print("Quick fix: [cyan]python -m ytm_cli auth setup-browser[/cyan]")
                return False
            else:
                print(f"[red]OAuth setup failed: {e}[/red]")
                return False

    def setup_browser_auth(self, headers_raw: str) -> bool:
        """Setup browser authentication from raw headers"""
        try:
            print("[yellow]Setting up browser authentication...[/yellow]")

            # Use ytmusicapi's setup function to create proper format
            from ytmusicapi.setup import setup

            auth_string = setup(filepath=None, headers_raw=headers_raw)

            # Save the auth string to browser.json
            with open(self.browser_file, "w") as f:
                f.write(auth_string)

            # Update config
            self._update_auth_config("browser")
            print("[green]Browser authentication setup complete![/green]")
            return True

        except Exception as e:
            print(f"[red]Browser setup failed: {e}[/red]")
            return False

    def setup_browser_auth_interactive(self, open_browser: bool = True) -> bool:
        """Browser authentication setup with specific header extraction"""
        print("\n[cyan]Browser Authentication Setup[/cyan]")

        if open_browser:
            print("[yellow]Opening YouTube Music in your browser...[/yellow]")
            try:
                webbrowser.open("https://music.youtube.com")
                print("[green]Browser opened![/green]")
            except Exception as e:
                print(f"[red]Could not open browser: {e}[/red]")
                print("Please manually open: https://music.youtube.com")

        print("\n[yellow]📋 Step-by-Step Instructions:[/yellow]")
        print("1. Make sure you're logged into YouTube Music")
        print("2. Open Developer Tools (F12)")
        print("3. Go to Network tab and clear it")
        print("4. Click on any song or playlist to trigger a request")
        print("5. In Network tab, filter by 'browse'")
        print("6. Find a POST request to '/youtubei/v1/browse'")
        print("7. Right-click the request → Copy → Copy as cURL")

        print(
            "\n[red]⚠️  IMPORTANT: cURL commands are ~5000 characters and will break terminal input![/red]"
        )
        print("[yellow]Instead, extract ONLY these specific headers:[/yellow]")
        print()
        print("From your cURL command, find and copy ONLY these lines:")
        print("[cyan]  -H 'cookie: ...'[/cyan]")
        print("[cyan]  -H 'user-agent: ...'[/cyan]")
        print("[cyan]  -H 'x-goog-visitor-id: ...'[/cyan]")
        print("[cyan]  -H 'x-youtube-client-name: ...'[/cyan]")
        print("[cyan]  -H 'x-youtube-client-version: ...'[/cyan]")

        print("\n[green]✅ Simple clipboard method:[/green]")
        print("1. Copy your cURL command to clipboard (Cmd+C)")
        print("2. Press Enter - we'll read it directly from clipboard")
        print("3. No pasting needed - keeps your terminal clean!")

        choice = (
            input("\nPress Enter when cURL is copied to clipboard (or 'q' to quit): ")
            .strip()
            .lower()
        )
        if choice == "q":
            return False

        return self._setup_browser_from_clipboard()

    def _setup_browser_from_clipboard(self) -> bool:
        """Setup browser auth from clipboard - simple and clean"""
        if not CLIPBOARD_AVAILABLE:
            print(
                "[red]Clipboard not available. Install pyperclip: pip install pyperclip[/red]"
            )
            print("Falling back to file method...")
            return self._setup_browser_from_file_with_guidance()

        try:
            print("[yellow]Reading cURL command from clipboard...[/yellow]")
            clipboard_content = pyperclip.paste().strip()

            if not clipboard_content:
                print("[red]Clipboard is empty[/red]")
                return False

            # Basic validation - should contain curl and music.youtube.com
            if not clipboard_content.startswith("curl"):
                print("[red]Clipboard doesn't contain a cURL command[/red]")
                print("Make sure you copied the full cURL command starting with 'curl'")
                return False

            if "music.youtube.com" not in clipboard_content:
                print("[red]This doesn't look like a YouTube Music cURL command[/red]")
                print("Make sure you copied the cURL from YouTube Music's Network tab")
                return False

            # Show length without showing content
            length = len(clipboard_content)
            print(f"[green]✓ Found cURL command ({length} characters)[/green]")

            if length > 3000:
                print(
                    "[green]✓ Large command detected - perfect for clipboard method![/green]"
                )

            print("[yellow]Processing headers silently...[/yellow]")
            success = self.setup_browser_auth(clipboard_content)

            if success:
                print("[green]✓ Browser authentication setup complete![/green]")
                print(
                    "[dim]Clipboard content was processed securely without display[/dim]"
                )

            return success

        except Exception as e:
            print(f"[red]Error reading clipboard: {e}[/red]")
            print("Falling back to file method...")
            return self._setup_browser_from_file_with_guidance()

    def _setup_browser_with_header_guidance(self) -> bool:
        """Guide user to extract specific headers from cURL command"""
        print("\n[cyan]🎯 Header Extraction Method[/cyan]")
        print("This method guides you to extract only the essential headers.")

        print("\n[yellow]📋 Step-by-step extraction:[/yellow]")
        print("1. Copy your cURL command to a text editor")
        print("2. Look for these specific header lines:")
        print("   [cyan]-H 'cookie: VISITOR_INFO1_LIVE=...; HSID=...; SSID=...'[/cyan]")
        print("   [cyan]-H 'user-agent: Mozilla/5.0...'[/cyan]")
        print("   [cyan]-H 'x-goog-visitor-id: Cgt...'[/cyan]")
        print("   [cyan]-H 'x-youtube-client-name: 67'[/cyan]")
        print("   [cyan]-H 'x-youtube-client-version: 1.20241...'[/cyan]")

        print(
            "\n[green]✅ Enter headers one by one (press Enter twice when done):[/green]"
        )

        headers_lines = []
        empty_count = 0

        while True:
            try:
                line = input("Header: ").strip()

                if not line:
                    empty_count += 1
                    if empty_count >= 2:
                        break
                    continue
                else:
                    empty_count = 0

                # Validate header format
                if line.startswith("-H '") and line.endswith("'"):
                    headers_lines.append(line)
                    print(f"[green]✓ Added header ({len(headers_lines)} total)[/green]")
                elif ":" in line:
                    # Raw header format, convert to cURL format
                    headers_lines.append(f"-H '{line}'")
                    print(f"[green]✓ Added header ({len(headers_lines)} total)[/green]")
                else:
                    print(
                        "[yellow]⚠️  Expected format: -H 'header-name: value' or 'header-name: value'[/yellow]"
                    )

            except (EOFError, KeyboardInterrupt):
                break

        if not headers_lines:
            print("[red]No valid headers provided[/red]")
            return False

        # Create a minimal cURL command with just the headers
        curl_command = "curl 'https://music.youtube.com/youtubei/v1/browse' \\\n"
        curl_command += " \\\n".join(headers_lines)

        print(f"\n[green]Processing {len(headers_lines)} headers...[/green]")
        return self.setup_browser_auth(curl_command)

    def _setup_browser_from_file_with_guidance(self) -> bool:
        """Setup browser auth from file with enhanced guidance"""
        file_path = "curl_command.txt"

        print("\n[yellow]📁 File Method for Large cURL Commands[/yellow]")
        print("This method handles large (~5000 character) cURL commands safely.")

        print("\n[cyan]Instructions:[/cyan]")
        print("1. Copy your FULL cURL command")
        print(f"2. Save it to: [cyan]{file_path}[/cyan]")
        print("3. Come back here and press Enter")

        print("\n[yellow]💡 Pro tip:[/yellow] You can use any text editor:")
        print(f"• nano {file_path}")
        print(f"• vim {file_path}")
        print(f"• code {file_path}")
        print("• Or copy-paste in your favorite editor")

        input(f"\nPress Enter when you've saved the cURL command to {file_path}...")

        try:
            if not os.path.exists(file_path):
                print(f"[red]File {file_path} not found[/red]")
                print(
                    f"Make sure you saved the cURL command to: [cyan]{file_path}[/cyan]"
                )
                return False

            with open(file_path, "r") as f:
                curl_content = f.read().strip()

            if not curl_content:
                print(f"[red]File {file_path} is empty[/red]")
                return False

            if len(curl_content) > 1000:
                print(
                    f"[green]✓ Large command detected ({len(curl_content)} characters)[/green]"
                )
            else:
                print(
                    f"[yellow]⚠️  Small command ({len(curl_content)} characters) - verify it's complete[/yellow]"
                )

            print("[yellow]Processing cURL command...[/yellow]")
            success = self.setup_browser_auth(curl_content)

            if success:
                # Ask if user wants to delete the file for security
                response = (
                    input(
                        f"\n[yellow]Delete {file_path} for security? (Y/n): [/yellow]"
                    )
                    .strip()
                    .lower()
                )
                if response != "n":
                    try:
                        os.remove(file_path)
                        print(f"[green]✓ Deleted {file_path}[/green]")
                    except Exception as e:
                        print(f"[yellow]Could not delete {file_path}: {e}[/yellow]")

            return success

        except Exception as e:
            print(f"[red]Error reading file: {e}[/red]")
            return False

    def _setup_browser_from_file(self) -> bool:
        """Setup browser auth from file"""
        file_path = "headers.txt"
        print("\n[yellow]File Method Selected[/yellow]")
        print(f"1. Save your cURL command or headers to: [cyan]{file_path}[/cyan]")
        print("2. Press Enter when ready")

        input("Press Enter when you've saved the file...")

        try:
            if not os.path.exists(file_path):
                print(f"[red]File {file_path} not found[/red]")
                return False

            with open(file_path, "r") as f:
                headers_raw = f.read().strip()

            if not headers_raw:
                print(f"[red]File {file_path} is empty[/red]")
                return False

            print(f"[green]Read {len(headers_raw.split())} words from file[/green]")

            # Ask if user wants to delete the file
            response = input(f"Delete {file_path} after setup? (Y/n): ").strip().lower()
            success = self.setup_browser_auth(headers_raw)

            if success and response != "n":
                try:
                    os.remove(file_path)
                    print(f"[yellow]Deleted {file_path}[/yellow]")
                except Exception as e:
                    print(f"[yellow]Could not delete {file_path}: {e}[/yellow]")

            return success

        except Exception as e:
            print(f"[red]Error reading file: {e}[/red]")
            return False

    def _setup_browser_interactive(self) -> bool:
        """Interactive browser auth setup with smart paste handling"""
        print("\n[yellow]Interactive Method Selected[/yellow]")
        print("Smart paste detection enabled!")
        print("\n[cyan]Instructions:[/cyan]")
        print("1. Paste your cURL command or headers")
        print("2. After pasting, just press Enter once on an empty line")
        print("3. The system will automatically detect completion")
        print("-" * 60)

        try:
            headers_input = []
            empty_line_count = 0

            print("Ready for input (paste now):")

            while True:
                try:
                    line = input()

                    # Check for manual termination
                    if line.strip().upper() == "END":
                        break

                    # Smart paste detection logic
                    if line.strip() == "":
                        empty_line_count += 1

                        # If we have content and hit an empty line, that's likely end of paste
                        if headers_input and empty_line_count >= 1:
                            print(
                                f"\n[green]Detected end of paste ({len(headers_input)} lines)[/green]"
                            )
                            break
                    else:
                        # Reset empty line counter when we get content
                        empty_line_count = 0
                        headers_input.append(line)

                        # If this looks like a curl command, it might be a single line
                        if line.strip().startswith("curl") and len(line) > 100:
                            print(
                                "\n[cyan]Large cURL command detected. Press Enter to finish.[/cyan]"
                            )

                except EOFError:
                    # Ctrl+D pressed - natural end
                    if headers_input:
                        print(
                            f"\n[green]Input completed ({len(headers_input)} lines)[/green]"
                        )
                    break
                except KeyboardInterrupt:
                    print("\n[yellow]Setup cancelled[/yellow]")
                    return False

            if not headers_input:
                print("[red]No headers provided[/red]")
                return False

            headers_raw = "\n".join(headers_input)

            if not headers_raw.strip():
                print("[red]No valid content provided[/red]")
                return False

            print(f"[green]Processing {len(headers_input)} lines of input...[/green]")
            return self.setup_browser_auth(headers_raw)

        except KeyboardInterrupt:
            print("\n[yellow]Setup cancelled[/yellow]")
            return False

    def _setup_browser_simple(self) -> bool:
        """Simple fallback browser auth setup"""
        print("\n[yellow]Simple Input Mode[/yellow]")
        print("Paste your content and press Enter, then type 'END' and press Enter:")
        print("-" * 50)

        try:
            headers_input = []

            while True:
                try:
                    line = input()

                    if line.strip().upper() == "END":
                        break

                    headers_input.append(line)

                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n[yellow]Setup cancelled[/yellow]")
                    return False

            if not headers_input:
                print("[red]No headers provided[/red]")
                return False

            headers_raw = "\n".join(headers_input)
            return self.setup_browser_auth(headers_raw)

        except KeyboardInterrupt:
            print("\n[yellow]Setup cancelled[/yellow]")
            return False

    def disable_auth(self) -> bool:
        """Disable authentication"""
        try:
            self._update_auth_config("none", enabled=False)

            # Optionally remove auth files
            for auth_file in [self.oauth_file, self.browser_file]:
                if os.path.exists(auth_file):
                    response = input(f"Remove {auth_file}? (y/N): ")
                    if response.lower() == "y":
                        os.remove(auth_file)
                        print(f"[yellow]Removed {auth_file}[/yellow]")

            print("[green]Authentication disabled[/green]")
            return True

        except Exception as e:
            print(f"[red]Error disabling auth: {e}[/red]")
            return False

    def get_ytmusic_instance(self) -> YTMusic:
        """Get YTMusic instance with appropriate authentication"""
        if not self.is_auth_enabled():
            return YTMusic()

        method = self.get_auth_method()

        try:
            if method == "oauth" and os.path.exists(self.oauth_file):
                print("[dim]Using OAuth authentication[/dim]")
                return YTMusic(self.oauth_file)

            elif method == "browser" and os.path.exists(self.browser_file):
                print("[dim]Using browser authentication[/dim]")
                return YTMusic(self.browser_file)

            else:
                print(
                    f"[yellow]Auth method '{method}' configured but credentials not found, using unauthenticated[/yellow]"
                )
                return YTMusic()

        except Exception as e:
            print(f"[red]Authentication failed: {e}[/red]")
            print("[yellow]Falling back to unauthenticated access[/yellow]")
            return YTMusic()

    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status"""
        status = {
            "enabled": self.is_auth_enabled(),
            "method": self.get_auth_method(),
            "oauth_file_exists": os.path.exists(self.oauth_file),
            "browser_file_exists": os.path.exists(self.browser_file),
        }
        return status

    def _update_auth_config(self, method: str, enabled: bool = True):
        """Update authentication configuration"""
        if "auth" not in self.config:
            self.config.add_section("auth")

        self.config.set("auth", "enabled", str(enabled))
        self.config.set("auth", "method", method)

        with open(self.config_path, "w") as f:
            self.config.write(f)

    def _parse_headers(self, headers_raw: str) -> Dict[str, Any]:
        """Parse headers from cURL or raw format"""
        auth_data = {}

        # Check if it's a cURL command
        if headers_raw.strip().startswith("curl"):
            auth_data = self._parse_curl_headers(headers_raw)
        else:
            auth_data = self._parse_raw_headers(headers_raw)

        return auth_data

    def _parse_curl_headers(self, curl_command: str) -> Dict[str, Any]:
        """Parse headers from cURL command"""
        import re

        auth_data = {}

        # Extract headers from cURL command
        header_pattern = r"-H '([^:]+): ([^']+)'"
        matches = re.findall(header_pattern, curl_command)

        for header_name, header_value in matches:
            # Map common headers needed for ytmusicapi
            if header_name.lower() == "cookie":
                auth_data["Cookie"] = header_value
            elif header_name.lower() == "user-agent":
                auth_data["User-Agent"] = header_value
            elif header_name.lower() == "x-goog-visitor-id":
                auth_data["X-Goog-Visitor-Id"] = header_value
            elif header_name.lower() == "x-youtube-client-name":
                auth_data["X-YouTube-Client-Name"] = header_value
            elif header_name.lower() == "x-youtube-client-version":
                auth_data["X-YouTube-Client-Version"] = header_value

        return auth_data

    def _parse_raw_headers(self, headers_raw: str) -> Dict[str, Any]:
        """Parse headers from raw format"""
        auth_data = {}

        lines = headers_raw.strip().split("\n")
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Only include relevant headers
                if key.lower() in [
                    "cookie",
                    "user-agent",
                    "x-goog-visitor-id",
                    "x-youtube-client-name",
                    "x-youtube-client-version",
                ]:
                    auth_data[key] = value

        return auth_data
