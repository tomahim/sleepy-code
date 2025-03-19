import click
import json as json_lib
import os
from typing import Dict, Type
from .php.base_collector import BaseCollector
from .php.collectors.function_collector import PhpFunctionCollector

class Registry:
    collectors: Dict[str, Type[BaseCollector]] = {
        'php.function': PhpFunctionCollector,
    }

    @classmethod
    def get_collector(cls, name: str) -> Type[BaseCollector]:
        return cls.collectors.get(name)

@click.command()
@click.argument('path')
@click.option('-r', '--rule', multiple=True, help='Rule name without extension')
@click.option('-c', '--collector', multiple=True, help='Collector name with format language.name')
@click.option('--json', is_flag=True, help='Output as JSON')
@click.option('-l', '--limit', type=int, help='Limit the number of files to process')
@click.option('--php', is_flag=True, help='Process PHP files')
def cli(path, rule, collector, json, limit, php):
    results = []
    if php:
        lang = 'php'
    else:
        raise click.BadParameter('Language not supported')
    
    for collector_name in collector:
        collector_class = Registry.get_collector(f"{lang}.{collector_name}")
        if not collector_class:
            raise click.BadParameter(f'Unknown collector: {collector_name}')
            
        # Get files based on collector's supported extension
        files = []
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith('.php'):
                    files.append(os.path.join(root, filename))
        
        if limit:
            files = files[:limit]
            
        collector_instance = collector_class(files)
        result = collector_instance.collect()
        results.extend(result)
    
    if json:
        click.echo(json_lib.dumps(results, indent=2, sort_keys=True))
    else:
        click.echo(results)

if __name__ == '__main__':
    cli()