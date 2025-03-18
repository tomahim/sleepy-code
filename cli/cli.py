import click
import json as json_lib

@click.command()
@click.argument('path')
@click.option('-r', '--rule', multiple=True, help='Rule name without extension')
@click.option('-c', '--collector', multiple=True, help='Collector name without extension')
@click.option('--json', is_flag=True, help='Output as JSON')
@click.option('--php', is_flag=True, help='Analyze PHP code')
def cli(path, rule, collector, json, php):
    if json:
        click.echo(json_lib.dumps({"ok": 'dumb content'}))
    else:
        click.echo("ok")

if __name__ == '__main__':
    cli()
