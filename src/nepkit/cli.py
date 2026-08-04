"""Command-line entry point for nepkit."""

import typer

app = typer.Typer(
    name="nepkit",
    help="Nepal-specific developer utilities.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Nepal-specific developer utilities."""
