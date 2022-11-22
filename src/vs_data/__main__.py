"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """Vs Data."""


if __name__ == "__main__":
    main(prog_name="vs-data")  # pragma: no cover
