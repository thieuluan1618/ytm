"""Tests for ytm_cli.auth module"""

import json
import os
from unittest.mock import Mock, patch

from ytm_cli.auth import AuthManager


class TestAuthManagerInit:
    """Tests for AuthManager initialization"""

    def test_init_default_files(self):
        """Test initialization with default file paths"""
        manager = AuthManager()

        assert manager.oauth_file == "oauth.json"
        assert manager.browser_file == "browser.json"
        assert manager.config_file == "config.ini"

    def test_init_custom_files(self):
        """Test initialization with custom file paths"""
        manager = AuthManager(
            oauth_file="custom_oauth.json",
            browser_file="custom_browser.json",
            config_file="custom_config.ini",
        )

        assert manager.oauth_file == "custom_oauth.json"
        assert manager.browser_file == "custom_browser.json"
        assert manager.config_file == "custom_config.ini"


class TestIsAuthEnabled:
    """Tests for is_auth_enabled method"""

    def test_is_auth_enabled_true(self, temp_dir):
        """Test when authentication is enabled in config"""
        config_content = "[auth]\nenabled = true\nmethod = oauth\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.is_auth_enabled() is True

    def test_is_auth_enabled_false(self, temp_dir):
        """Test when authentication is disabled in config"""
        config_content = "[auth]\nenabled = false\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.is_auth_enabled() is False

    def test_is_auth_enabled_no_config(self, temp_dir):
        """Test when config file doesn't exist"""
        config_file = os.path.join(temp_dir, "non_existent.ini")
        manager = AuthManager(config_file=config_file)

        assert manager.is_auth_enabled() is False

    def test_is_auth_enabled_no_auth_section(self, temp_dir):
        """Test when config exists but no auth section"""
        config_content = "[general]\nsongs_to_display = 5\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.is_auth_enabled() is False

    def test_is_auth_enabled_invalid_value(self, temp_dir):
        """Test when enabled value is invalid"""
        config_content = "[auth]\nenabled = invalid\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.is_auth_enabled() is False


class TestGetAuthMethod:
    """Tests for get_auth_method method"""

    def test_get_auth_method_oauth(self, temp_dir):
        """Test getting OAuth auth method"""
        config_content = "[auth]\nenabled = true\nmethod = oauth\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.get_auth_method() == "oauth"

    def test_get_auth_method_browser(self, temp_dir):
        """Test getting browser auth method"""
        config_content = "[auth]\nenabled = true\nmethod = browser\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.get_auth_method() == "browser"

    def test_get_auth_method_default(self, temp_dir):
        """Test default auth method when not specified"""
        config_content = "[auth]\nenabled = true\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        assert manager.get_auth_method() == "oauth"

    def test_get_auth_method_no_config(self, temp_dir):
        """Test auth method when no config exists"""
        config_file = os.path.join(temp_dir, "non_existent.ini")
        manager = AuthManager(config_file=config_file)

        assert manager.get_auth_method() == "oauth"


class TestEnableAuth:
    """Tests for enable_auth method"""

    def test_enable_auth_oauth(self, temp_dir):
        """Test enabling OAuth authentication"""
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(config_file=config_file)

        with patch("builtins.print") as mock_print:
            result = manager.enable_auth("oauth")

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Authentication enabled with method: oauth[/green]"
            )

            # Verify config was written
            assert os.path.exists(config_file)
            assert manager.is_auth_enabled() is True
            assert manager.get_auth_method() == "oauth"

    def test_enable_auth_browser(self, temp_dir):
        """Test enabling browser authentication"""
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(config_file=config_file)

        with patch("builtins.print") as mock_print:
            result = manager.enable_auth("browser")

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Authentication enabled with method: browser[/green]"
            )
            assert manager.get_auth_method() == "browser"

    def test_enable_auth_invalid_method(self, temp_dir):
        """Test enabling auth with invalid method"""
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(config_file=config_file)

        with patch("builtins.print") as mock_print:
            result = manager.enable_auth("invalid")

            assert result is False
            mock_print.assert_called_with(
                "[red]Invalid auth method. Use 'oauth' or 'browser'[/red]"
            )

    def test_enable_auth_file_error(self, temp_dir):
        """Test enabling auth with file write error"""
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(config_file=config_file)

        with patch("builtins.open", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.enable_auth("oauth")

            assert result is False
            mock_print.assert_called_with(
                "[red]Error enabling authentication: Permission denied[/red]"
            )

    def test_enable_auth_preserves_existing_config(self, temp_dir):
        """Test that enabling auth preserves existing config sections"""
        config_content = "[general]\nsongs_to_display = 10\n[mpv]\nflags = --no-video\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        with patch("builtins.print"):
            manager.enable_auth("oauth")

        # Verify existing sections are preserved
        import configparser

        config = configparser.ConfigParser()
        config.read(config_file)

        assert config.has_section("general")
        assert config.has_section("mpv")
        assert config.has_section("auth")
        assert config.get("general", "songs_to_display") == "10"
        assert config.get("mpv", "flags") == "--no-video"


class TestDisableAuth:
    """Tests for disable_auth method"""

    def test_disable_auth_success(self, temp_dir):
        """Test successfully disabling authentication"""
        config_content = "[auth]\nenabled = true\nmethod = oauth\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        with patch("builtins.print") as mock_print:
            result = manager.disable_auth()

            assert result is True
            mock_print.assert_called_with("[green]✅ Authentication disabled[/green]")
            assert manager.is_auth_enabled() is False

    def test_disable_auth_no_config(self, temp_dir):
        """Test disabling auth when no config exists"""
        config_file = os.path.join(temp_dir, "non_existent.ini")
        manager = AuthManager(config_file=config_file)

        with patch("builtins.print") as mock_print:
            result = manager.disable_auth()

            assert result is True
            mock_print.assert_called_with("[green]✅ Authentication disabled[/green]")

    def test_disable_auth_file_error(self, temp_dir):
        """Test disabling auth with file write error"""
        config_content = "[auth]\nenabled = true\n"
        config_file = os.path.join(temp_dir, "config.ini")

        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        with patch("builtins.open", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.disable_auth()

            assert result is False
            mock_print.assert_called_with(
                "[red]Error disabling authentication: Permission denied[/red]"
            )


class TestSetupOauthAuth:
    """Tests for setup_oauth_auth method"""

    def test_setup_oauth_auth_success(self, temp_dir):
        """Test successful OAuth setup"""
        oauth_file = os.path.join(temp_dir, "oauth.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(oauth_file=oauth_file, config_file=config_file)

        mock_oauth_data = {"access_token": "test_token", "refresh_token": "test_refresh"}

        with patch("ytmusicapi.setup.setup_oauth", return_value=mock_oauth_data), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.setup_oauth_auth("client_id", "client_secret")

            assert result is True

            # Verify OAuth file was created
            assert os.path.exists(oauth_file)
            with open(oauth_file) as f:
                data = json.load(f)
                assert data == mock_oauth_data

            # Verify auth was enabled
            assert manager.is_auth_enabled() is True
            assert manager.get_auth_method() == "oauth"

    def test_setup_oauth_auth_failure(self, temp_dir):
        """Test OAuth setup failure"""
        oauth_file = os.path.join(temp_dir, "oauth.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(oauth_file=oauth_file, config_file=config_file)

        with patch("ytmusicapi.setup.setup_oauth", side_effect=Exception("OAuth failed")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.setup_oauth_auth("client_id", "client_secret")

            assert result is False
            mock_print.assert_called_with("[red]OAuth setup failed: OAuth failed[/red]")

            # Verify no files were created
            assert not os.path.exists(oauth_file)

    def test_setup_oauth_auth_file_write_error(self, temp_dir):
        """Test OAuth setup with file write error"""
        oauth_file = os.path.join(temp_dir, "oauth.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(oauth_file=oauth_file, config_file=config_file)

        mock_oauth_data = {"access_token": "test_token"}

        with patch("ytmusicapi.setup.setup_oauth", return_value=mock_oauth_data), patch(
            "builtins.open", side_effect=OSError("Permission denied")
        ), patch("builtins.print") as mock_print:
            result = manager.setup_oauth_auth("client_id", "client_secret")

            assert result is False
            mock_print.assert_called_with(
                "[red]Error saving OAuth credentials: Permission denied[/red]"
            )


class TestSetupBrowserAuth:
    """Tests for setup_browser_auth method"""

    def test_setup_browser_auth_success(self, temp_dir):
        """Test successful browser auth setup"""
        browser_file = os.path.join(temp_dir, "browser.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(browser_file=browser_file, config_file=config_file)

        mock_browser_data = {"session_data": "test_session"}

        with patch("ytmusicapi.YTMusic.setup", return_value=mock_browser_data), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.setup_browser_auth()

            assert result is True

            # Verify browser file was created
            assert os.path.exists(browser_file)
            with open(browser_file) as f:
                data = json.load(f)
                assert data == mock_browser_data

            # Verify auth was enabled
            assert manager.is_auth_enabled() is True
            assert manager.get_auth_method() == "browser"

    def test_setup_browser_auth_failure(self, temp_dir):
        """Test browser auth setup failure"""
        browser_file = os.path.join(temp_dir, "browser.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(browser_file=browser_file, config_file=config_file)

        with patch("ytmusicapi.YTMusic.setup", side_effect=Exception("Browser auth failed")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.setup_browser_auth()

            assert result is False
            mock_print.assert_called_with(
                "[red]Browser authentication setup failed: Browser auth failed[/red]"
            )

    def test_setup_browser_auth_file_error(self, temp_dir):
        """Test browser auth setup with file write error"""
        browser_file = os.path.join(temp_dir, "browser.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(browser_file=browser_file, config_file=config_file)

        mock_browser_data = {"session_data": "test_session"}

        with patch("ytmusicapi.YTMusic.setup", return_value=mock_browser_data), patch(
            "builtins.open", side_effect=OSError("Permission denied")
        ), patch("builtins.print") as mock_print:
            result = manager.setup_browser_auth()

            assert result is False
            mock_print.assert_called_with(
                "[red]Error saving browser credentials: Permission denied[/red]"
            )


class TestGetYtmusicInstance:
    """Tests for get_ytmusic_instance method"""

    def test_get_ytmusic_instance_unauthenticated(self, temp_dir):
        """Test getting YTMusic instance when auth is disabled"""
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(config_file=config_file)

        with patch("ytmusicapi.YTMusic") as mock_ytmusic_class:
            mock_instance = Mock()
            mock_ytmusic_class.return_value = mock_instance

            result = manager.get_ytmusic_instance()

            assert result == mock_instance
            mock_ytmusic_class.assert_called_once_with()

    def test_get_ytmusic_instance_oauth(self, temp_dir):
        """Test getting YTMusic instance with OAuth"""
        oauth_file = os.path.join(temp_dir, "oauth.json")
        config_file = os.path.join(temp_dir, "config.ini")

        # Create OAuth file
        oauth_data = {"access_token": "test_token"}
        with open(oauth_file, "w") as f:
            json.dump(oauth_data, f)

        # Create config with OAuth enabled
        config_content = "[auth]\nenabled = true\nmethod = oauth\n"
        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(oauth_file=oauth_file, config_file=config_file)

        with patch("ytmusicapi.YTMusic") as mock_ytmusic_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_instance = Mock()
            mock_ytmusic_class.return_value = mock_instance

            result = manager.get_ytmusic_instance()

            assert result == mock_instance
            mock_ytmusic_class.assert_called_once_with(oauth_file)
            mock_print.assert_called_with("[dim]Using OAuth authentication[/dim]")

    def test_get_ytmusic_instance_browser(self, temp_dir):
        """Test getting YTMusic instance with browser auth"""
        browser_file = os.path.join(temp_dir, "browser.json")
        config_file = os.path.join(temp_dir, "config.ini")

        # Create browser file
        browser_data = {"session_data": "test_session"}
        with open(browser_file, "w") as f:
            json.dump(browser_data, f)

        # Create config with browser auth enabled
        config_content = "[auth]\nenabled = true\nmethod = browser\n"
        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(browser_file=browser_file, config_file=config_file)

        with patch("ytmusicapi.YTMusic") as mock_ytmusic_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_instance = Mock()
            mock_ytmusic_class.return_value = mock_instance

            result = manager.get_ytmusic_instance()

            assert result == mock_instance
            mock_ytmusic_class.assert_called_once_with(browser_file)
            mock_print.assert_called_with("[dim]Using browser authentication[/dim]")

    def test_get_ytmusic_instance_auth_failure_fallback(self, temp_dir):
        """Test fallback to unauthenticated when auth fails"""
        oauth_file = os.path.join(temp_dir, "oauth.json")
        config_file = os.path.join(temp_dir, "config.ini")

        # Create OAuth file
        oauth_data = {"access_token": "test_token"}
        with open(oauth_file, "w") as f:
            json.dump(oauth_data, f)

        # Create config with OAuth enabled
        config_content = "[auth]\nenabled = true\nmethod = oauth\n"
        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(oauth_file=oauth_file, config_file=config_file)

        with patch("ytmusicapi.YTMusic") as mock_ytmusic_class, patch(
            "builtins.print"
        ) as mock_print:
            # First call (with auth file) raises exception, second call (without) succeeds
            mock_instance = Mock()
            mock_ytmusic_class.side_effect = [Exception("Auth failed"), mock_instance]

            result = manager.get_ytmusic_instance()

            assert result == mock_instance
            assert mock_ytmusic_class.call_count == 2
            mock_ytmusic_class.assert_any_call(oauth_file)
            mock_ytmusic_class.assert_any_call()

            mock_print.assert_any_call("[red]Authentication failed: Auth failed[/red]")
            mock_print.assert_any_call("[yellow]Falling back to unauthenticated access[/yellow]")

    def test_get_ytmusic_instance_missing_credentials(self, temp_dir):
        """Test when auth is enabled but credential files are missing"""
        config_file = os.path.join(temp_dir, "config.ini")

        # Create config with OAuth enabled but no OAuth file
        config_content = "[auth]\nenabled = true\nmethod = oauth\n"
        with open(config_file, "w") as f:
            f.write(config_content)

        manager = AuthManager(config_file=config_file)

        with patch("ytmusicapi.YTMusic") as mock_ytmusic_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_instance = Mock()
            mock_ytmusic_class.return_value = mock_instance

            result = manager.get_ytmusic_instance()

            assert result == mock_instance
            mock_ytmusic_class.assert_called_once_with()
            mock_print.assert_called_with(
                "[yellow]Auth method 'oauth' configured but credentials not found, using unauthenticated[/yellow]"
            )


class TestAuthManagerIntegration:
    """Integration tests for AuthManager"""

    def test_full_oauth_workflow(self, temp_dir):
        """Test complete OAuth workflow"""
        oauth_file = os.path.join(temp_dir, "oauth.json")
        config_file = os.path.join(temp_dir, "config.ini")
        manager = AuthManager(oauth_file=oauth_file, config_file=config_file)

        # Initially no auth
        assert manager.is_auth_enabled() is False

        # Setup OAuth
        mock_oauth_data = {"access_token": "test_token"}
        with patch("ytmusicapi.setup.setup_oauth", return_value=mock_oauth_data), patch(
            "builtins.print"
        ):
            result = manager.setup_oauth_auth("client_id", "client_secret")
            assert result is True

        # Verify auth is enabled
        assert manager.is_auth_enabled() is True
        assert manager.get_auth_method() == "oauth"

        # Get authenticated instance
        with patch("ytmusicapi.YTMusic") as mock_ytmusic_class, patch("builtins.print"):
            mock_instance = Mock()
            mock_ytmusic_class.return_value = mock_instance

            instance = manager.get_ytmusic_instance()
            assert instance == mock_instance
            mock_ytmusic_class.assert_called_once_with(oauth_file)

        # Disable auth
        with patch("builtins.print"):
            result = manager.disable_auth()
            assert result is True

        assert manager.is_auth_enabled() is False
