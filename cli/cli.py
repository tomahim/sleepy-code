import click

@click.command()
@click.argument('path')
@click.option('-php', is_flag=True, help='Analyze PHP files')
def cli(path, php):
    click.echo(f"ok")

if __name__ == '__main__':
    cli()