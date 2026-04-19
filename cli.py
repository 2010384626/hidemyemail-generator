import click
from main import generate_emails

@click.group()
def cli():
    pass

@cli.command()
@click.option('--count', default=5, help='Number of emails to generate.')
@click.option('--cookie-file', default='cookie.txt', help='Path to cookie file.')
def generate(count, cookie_file):
    """Generate HideMyEmail emails."""
    try:
        generate_emails(count, cookie_file)
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == '__main__':
    cli()
