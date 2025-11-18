#!/usr/bin/env python3
"""Test script for LLM-powered music recommendations"""

import sys

from rich.console import Console
from rich.table import Table

# Add ytm_cli to path
sys.path.insert(0, '.')

from ytm_cli.llm_client import LLMClient

console = Console()


def display_context(client: LLMClient):
    """Display current context from playlists and dislikes"""
    console.print("\n[bold cyan]📊 Current Context[/bold cyan]")

    context = client.get_context_summary()

    # Recent additions
    if context['recent_added']:
        table = Table(title="Recently Added Songs")
        table.add_column("Title", style="cyan")
        table.add_column("Artist", style="magenta")
        table.add_column("Playlist", style="green")

        for song in context['recent_added'][:5]:
            table.add_row(
                song['title'],
                song['artist'],
                song['playlist']
            )

        console.print(table)
    else:
        console.print("[yellow]No recently added songs found[/yellow]")

    # Recent dislikes
    if context['recent_disliked']:
        table = Table(title="Recently Disliked Songs")
        table.add_column("Title", style="cyan")
        table.add_column("Artist", style="magenta")

        for song in context['recent_disliked'][:5]:
            table.add_row(song['title'], song['artist'])

        console.print(table)
    else:
        console.print("[yellow]No disliked songs found[/yellow]")


def test_recommendation(client: LLMClient, user_request: str, verbose: bool = False):
    """Test a single recommendation request"""
    console.print(f"\n[bold green]🎵 User Request:[/bold green] {user_request}")

    response = client.generate(user_request, verbose=verbose)

    if response:
        console.print("\n[bold blue]📋 LLM Response:[/bold blue]")
        console.print(f"  [cyan]Action:[/cyan] {response.action}")
        console.print(f"  [cyan]Query:[/cyan] {response.query}")

        if response.parameters:
            console.print("  [cyan]Parameters:[/cyan]")
            for key, value in response.parameters.items():
                console.print(f"    • {key}: {value}")

        return response
    else:
        console.print("[red]❌ Failed to get recommendation[/red]")
        return None


def main():
    """Run test scenarios"""
    console.print("[bold magenta]🎸 YTM LLM Recommendation System Test[/bold magenta]\n")

    # Initialize client
    try:
        client = LLMClient()
        console.print(f"[green]✓ LLM Client initialized ({client.provider}/{client.model})[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize LLM client: {e}[/red]")
        return

    # Display current context
    display_context(client)

    # Test scenarios
    test_requests = [
        "Play something like what I've been listening to lately",
        "I want some upbeat pop music",
        "Play my chill playlist",
        "Something new but not from artists I've disliked",
        "Recommend me 5 songs based on my recent favorites"
    ]

    console.print("\n[bold yellow]🧪 Running Test Scenarios[/bold yellow]")

    for i, request in enumerate(test_requests, 1):
        console.print(f"\n[dim]{'=' * 60}[/dim]")
        console.print(f"[bold]Test {i}/{len(test_requests)}[/bold]")

        # Show context prompt for first test only
        verbose = (i == 1)
        test_recommendation(client, request, verbose=verbose)

    console.print(f"\n[dim]{'=' * 60}[/dim]")
    console.print("\n[green]✅ All tests completed![/green]")


if __name__ == "__main__":
    main()
