import click
import json as json_lib
import os
from .php.collectors.function_collector import PhpFunctionCollector

@click.command()
@click.argument('path')
@click.option('-r', '--rule', multiple=True, help='Rule name without extension')
@click.option('-c', '--collector', multiple=True, help='Collector name without extension')
@click.option('--json', is_flag=True, help='Output as JSON')
@click.option('--php', is_flag=True, help='Analyze PHP code')
@click.option('-l', '--limit', type=int, help='Limit the number of files to process')
def cli(path, rule, collector, json, php, limit):
    if php and 'function' in collector:
        # Get all PHP files in the specified path
        php_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.php'):
                    php_files.append(os.path.join(root, file))
        
        if limit:
            php_files = php_files[:limit]
                    
        # Run the collector
        function_collector = PhpFunctionCollector(php_files)
        result = function_collector.collect()
        
        if json:
            # Pretty print with indentation and sorted keys
            click.echo(json_lib.dumps(result, indent=2, sort_keys=True))
        else:
            click.echo(result)
    else:
        if json:
            click.echo(json_lib.dumps({"ok": 'dumb content'}, indent=2))
        else:
            click.echo("ok")

if __name__ == '__main__':
    cli()