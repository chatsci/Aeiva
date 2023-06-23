"""
Prepare the Stanford Alpaca dataset for instruction-following language modeling.
"""
import orjson, json

# download the stanford alpaca dataset by running the following or directly download from the link
# filename = wget.download('https://github.com/tatsu-lab/stanford_alpaca/blob/main/alpaca_data.json') 

# load the dataset
raw_data = orjson.loads(open('alpaca_data.json', 'rb').read())
print(f"length of dataset in characters: {len(raw_data):,}")

# format the data
formatted_data = {}
formatted_data['data'] = raw_data
formatted_data['meta'] = {
    "length": len(raw_data)
    }

# dump the data
with open('alpaca_data.formatted.json', 'wb') as f:
    f.write(orjson.dumps(formatted_data, option=orjson.OPT_INDENT_2))
