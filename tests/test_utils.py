"""Tests for ytm_cli.utils module"""

import os
import signal
import sys
from unittest.mock import Mock, patch, call

import pytest

from ytm_cli.utils import goodbye_message, setup_signal_handler, clear_screen, getch


class TestGoodbyeMessage:
    """Tests for goodbye_message function"""

    def test_goodbye_message_prints_and_exits(self):
        """Test that goodbye_message prints message and exits"""
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            goodbye_message()
            
            mock_print.assert_called_once_with("\n👋 Goodbye! Thanks for using YTM CLI! 💩 💩 💩")
            mock_exit.assert_called_once_with(0)


class TestSetupSignalHandler:
    """Tests for setup_signal_handler function"""

    def test_setup_signal_handler_registers_sigint(self):
        """Test that signal handler is registered for SIGINT"""
        with patch('signal.signal') as mock_signal:
            setup_signal_handler()
            
            # Verify signal.signal was called with SIGINT
            mock_signal.assert_called_once()
            args = mock_signal.call_args[0]
            assert args[0] == signal.SIGINT
            assert callable(args[1])  # Second argument should be a callable

    def test_signal_handler_calls_goodbye_message(self):
        """Test that the registered signal handler calls goodbye_message"""
        with patch('signal.signal') as mock_signal, \
             patch('ytm_cli.utils.goodbye_message') as mock_goodbye:
            
            setup_signal_handler()
            
            # Get the registered handler function
            handler_func = mock_signal.call_args[0][1]
            
            # Call the handler with dummy arguments
            handler_func(signal.SIGINT, None)
            
            mock_goodbye.assert_called_once()


class TestClearScreen:
    """Tests for clear_screen function"""

    def test_clear_screen_windows(self):
        """Test clear_screen on Windows"""
        with patch('os.name', 'nt'), \
             patch('os.system') as mock_system:
            
            clear_screen()
            
            mock_system.assert_called_once_with('cls')

    def test_clear_screen_unix(self):
        """Test clear_screen on Unix-like systems"""
        with patch('os.name', 'posix'), \
             patch('os.system') as mock_system:
            
            clear_screen()
            
            mock_system.assert_called_once_with('clear')

    def test_clear_screen_other_os(self):
        """Test clear_screen on other OS"""
        with patch('os.name', 'other'), \
             patch('os.system') as mock_system:
            
            clear_screen()
            
            mock_system.assert_called_once_with('clear')


class TestGetch:
    """Tests for getch function"""

    def test_getch_returns_character(self):
        """Test that getch returns a character"""
        with patch('sys.stdin.fileno', return_value=0), \
             patch('termios.tcgetattr', return_value='old_settings'), \
             patch('tty.setraw'), \
             patch('sys.stdin.read', return_value='a'), \
             patch('termios.tcsetattr'):
            
            result = getch()
            
            assert result == 'a'

    def test_getch_restores_terminal_settings(self):
        """Test that getch properly restores terminal settings"""
        mock_fd = 0
        mock_old_settings = 'old_settings'
        
        with patch('sys.stdin.fileno', return_value=mock_fd), \
             patch('termios.tcgetattr', return_value=mock_old_settings) as mock_get, \
             patch('tty.setraw') as mock_setraw, \
             patch('sys.stdin.read', return_value='x'), \
             patch('termios.tcsetattr') as mock_set:
            
            getch()
            
            # Verify terminal settings are saved and restored
            mock_get.assert_called_once_with(mock_fd)
            mock_setraw.assert_called_once_with(mock_fd)
            mock_set.assert_called_once_with(mock_fd, 'TCSADRAIN', mock_old_settings)

    def test_getch_restores_settings_on_exception(self):
        """Test that getch restores settings even if an exception occurs"""
        mock_fd = 0
        mock_old_settings = 'old_settings'
        
        with patch('sys.stdin.fileno', return_value=mock_fd), \
             patch('termios.tcgetattr', return_value=mock_old_settings), \
             patch('tty.setraw'), \
             patch('sys.stdin.read', side_effect=KeyboardInterrupt), \
             patch('termios.tcsetattr') as mock_set:
            
            with pytest.raises(KeyboardInterrupt):
                getch()
            
            # Verify settings are restored even after exception
            mock_set.assert_called_once_with(mock_fd, 'TCSADRAIN', mock_old_settings)


class TestUtilsIntegration:
    """Integration tests for utils module"""

    def test_signal_handler_integration(self):
        """Test that signal handler integration works correctly"""
        with patch('signal.signal') as mock_signal, \
             patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            # Setup signal handler
            setup_signal_handler()
            
            # Get the registered handler
            handler_func = mock_signal.call_args[0][1]
            
            # Simulate SIGINT
            handler_func(signal.SIGINT, None)
            
            # Verify goodbye message was printed and exit was called
            mock_print.assert_called_once_with("\n👋 Goodbye! Thanks for using YTM CLI! 💩 💩 💩")
            mock_exit.assert_called_once_with(0)
