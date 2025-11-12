import yaml
import json


class DotDict(dict):
    
    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, key):
        value = self[key]
        return DotDict(value) if isinstance(value, dict) else value

    def __str__(self):
        # 利用json.dumps自动生成双引号的字符串表示
        return json.dumps(self)


def load_yaml_config(file_path: str) -> DotDict:
    """
    Load YAML file and return DotDict for dot notation access
    """

    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    return DotDict(data)


config = load_yaml_config('src/config.yaml')
variables = config.dev.variables
print(variables)
print(variables.project)
