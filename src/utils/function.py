import yaml


class DotDict(dict):
    """Dictionary that supports dot notation access"""
    
    def __getattr__(self, key):
        value = self[key]
        return DotDict(value) if isinstance(value, dict) else value
    
    def __setattr__(self, key, value):
        self[key] = value


def load_yaml_config(file_path: str) -> DotDict:
    """Load YAML file and return DotDict for dot notation access"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return DotDict(data)


config = load_yaml_config('src/config.yaml')

print(config.dev.variables.project)