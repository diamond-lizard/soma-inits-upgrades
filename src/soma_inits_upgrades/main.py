"""Click CLI definition for soma-inits-upgrades."""

import click


@click.command()
@click.argument("stale_inits_file", type=click.Path(exists=False))
@click.option(
    "--output-dir",
    default="~/.emacs.d/soma/inits-upgrades/",
    help="Output directory for reports and state.",
)
def cli(stale_inits_file: str, output_dir: str) -> None:
    """Automate security review and upgrade planning for stale elpaca pins."""
    click.echo(f"Stale inits file: {stale_inits_file}")
    click.echo(f"Output directory: {output_dir}")
