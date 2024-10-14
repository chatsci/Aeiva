import json
import codecs


def prettyformat_json(file_path, output_path) -> None:
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)


def load_json(file_path) -> dict:
    with codecs.open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def dump_json(data, file_path) -> None:
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
