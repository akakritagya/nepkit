"""Command-line entry point for nepkit."""

import typer

app = typer.Typer(
    name="nepkit",
    help="Bikram Sambat <-> Gregorian date conversion.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Bikram Sambat <-> Gregorian date conversion."""
