# Datasets

This is the folder where we prepare the datasets.

## Principles

1. We name the data online (download via url) or in local folder as "raw_data";
2. Each dataset will be in a subfolder of this folder, and the folder name will be the dataset name;
3. Within each dataset's subfolder, we will have a "prepare.py". The script aims to transform the "raw_data" to "formatted_data";
4. The "formatted_data" follows specifc formats (see descriptions below). It was prepared for further processing by tokenizers or embedders.


## Data formats for formatted data

1. Pure text corpus

	{
   	 "data": [corpus 1, corpus 2],
   	 "meta": {meta info}
	}

2. Data with multiple fields

	{
   	 "data": [{item 1}, {item 2}, ...],
   	 "meta": {meta info}
	}

## TODO

Define more standard formats for different types of datasets.
