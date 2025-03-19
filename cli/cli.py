import click
import json as json_lib
import os
from typing import Dict, Type, List
from .php.base_collector import BaseCollector
from .php.collectors.function_collector import PhpFunctionCollector
from .php.rules.unused_function import UnusedFunctionRule
from .php.base_rule import BaseRule

class RuleSpecParser:
    def __init__(self, rule_name: str):
        self.rule_name = rule_name
        
    def get_required_collectors(self) -> List[str]:
        with open(f'specs/php/{self.rule_name}.rule', 'r') as f:
            content = f.read()
            # Parse the "Depends on collectors" section
            collectors_section = content.split('### Depends on collectors\n')[1].split('\n\n')[0]
            return [collector.strip() for collector in collectors_section.split('\n') if collector.strip()]

class Registry:
    collectors: Dict[str, Type[BaseCollector]] = {
        'php.function': PhpFunctionCollector,
    }

    rules: Dict[str, Type[BaseRule]] = {
        'php.unused_function': UnusedFunctionRule,
    }

    @classmethod
    def get_collector(cls, name: str) -> Type[BaseCollector]:
        return cls.collectors.get(name)

    @classmethod
    def get_rule(cls, name: str) -> Type[BaseRule]:
        return cls.rules.get(name)

@click.command()
@click.argument('path')
@click.option('-r', '--rule', multiple=True, help='Rule name without extension')
@click.option('-c', '--collector', multiple=True, help='Collector name with format language.name')
@click.option('--json', is_flag=True, help='Output as JSON')
@click.option('-l', '--limit', type=int, help='Limit the number of files to process')
@click.option('--php', is_flag=True, help='Process PHP files')
def cli(path, rule, collector, json, limit, php):
    all_results = []

    if php:
        lang = 'php'
    else: 
        raise click.BadParameter('Language not supported')
    
    # Run explicitly requested collectors
    if collector:
        for collector_name in collector:
            collector_class = Registry.get_collector(f"{lang}.{collector_name}")
            if not collector_class:
                raise click.BadParameter(f'Unknown collector: {collector_name}')
                
            files = get_files(path, php, limit)
            collector_instance = collector_class(files)
            result = collector_instance.collect()
            all_results.extend(result)
    
    # Run rules and their dependent collectors
    if rule:
        rule_results = []
        for rule_name in rule:
            # Get required collectors from rule spec
            rule_spec = RuleSpecParser(rule_name)
            required_collectors = rule_spec.get_required_collectors()
            
            collector_results = []
            for collector_name in required_collectors:
                collector_class = Registry.get_collector(f"{lang}.{collector_name}")
                if not collector_class:
                    raise click.BadParameter(f'Unknown collector: {collector_name}')
                    
                files = get_files(path, php, limit)
                collector_instance = collector_class(files)
                result = collector_instance.collect()
                collector_results.extend(result)
            
            # Run rule analysis
            rule_class = Registry.get_rule(f"{lang}.{rule_name}")
            if not rule_class:
                raise click.BadParameter(f'Unknown rule: {rule_name}')
                
            files = get_files(path, php, limit)
            rule_instance = rule_class(collector_results, files)
            result = rule_instance.analyze()
            rule_results.extend(result)
            
        all_results.extend(rule_results)
    
    if json:
        click.echo(json_lib.dumps(all_results, indent=2, sort_keys=True))
    else:
        click.echo(all_results)

def get_files(path: str, php: bool, limit: int) -> List[str]:
    files = []
    for root, dirs, filenames in os.walk(path):
        for filename in filenames:
            if php and filename.endswith('.php'):
                files.append(os.path.join(root, filename))
    
    if limit:
        files = files[:limit]
    return files

if __name__ == '__main__':
    cli()