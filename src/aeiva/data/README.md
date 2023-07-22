


# Data Package
In this package, we include source files related to processing datasets. 

## Core Concepts
The core concepts in this package include:

* **Formatter:** a `Formatter` is a class that takes into *raw dataset* and turn it into *formatted dataset*.
* **Processor:** a `Processor` is a class that transforms a formatted dataset into desired features or tensors. Note that a Formatter only re-organizes the information in the raw dataset without generating new information, but a Processor can transform and generate new information.
* **Dataset:** a PyTorch `Dataset` is an abstract class representing a dataset, which could be anything from a text file, a directory of images, a CSV file, etc. The Dataset class requires the overriding of two methods:
	*  **\_\_len\_\_:** so that `len(dataset)` returns the size of the dataset.
	* **\_\_getitem\_\_:** to support indexing such that `dataset[i]` can be used to get the i-th sample of the data.

	In our project, we will extend PyTorch Dataset.
* **DataLoader:** a PyTorch `DataLoader` wraps a Dataset and provides mini-batches of data. It is an iterable over a dataset, with support for:

	* batching the data
	* shuffling the data
	* loading the data in parallel using `multiprocessing` workers

	The `DataLoader` is typically used in a for-in loop. For each iteration, it returns a batch of data which are processed by the model.
	
	So, in short, a `Dataset` retrieves our dataset’s features and labels one sample at a time. While a `DataLoader` wraps a Dataset and provides mini-batches of the samples from the dataset. The `DataLoader` can also provide other functionalities, such as data shuffling and multiprocess data loading.

More specifically, we mainly include the following parts:

## Code Architecture
### bases/
This is the location where we define different base classes for the core concepts. It guides the framework design and helps us to easily understand the core concepts.

### processors/
This is the location where we define different processor classes for processing different modalities. They will extend the base processor class defined in `bases/`.

### dataloaders/
This is the location where we define general `Dataset` and `DataLoader` classes based one data modality or task type.

### ./
We put the dataset classes for different specific datasets in this directory. Each single file contains the `Formatter`, `Processor`, `Dataset`, and `DataLoader` classes for one specific dataset, e.g., alpaca dataset, avsd dataset, etc.

## From Raw Dataset to Data Loader
Basically, we will need to define the following:

1. in `aeiva/data/__init__.py`, we put things related to global environment settings and so on.
2. in `aeiva/data/constants.py`, we have package-level constants.
3. in `xxx_utils.py` within the `aeiva/util/` directory, we group different types of util functions.
4. in `aeiva/data/processor/xxx_processor.py` module, we define different formatters for different modalities.
5. in `aeiva/data/dataloader/xxx_data.py` module, we define different `DataSet` and `DataLoader` for different modalities or tasks.
6. in `aeiva/data/`, we put the `xxx_dataset.py` to include the formatter, processor, dataset, and dataloader definitions for each specific dataset.

NOTE: each formatted dataset and processed dataset should be a dict looks like 
```
{'data': [e1, e2, ...], 'metadata': {'version': 'xxx', ...}}
```

The data part of a dataset should be a list of examples. 

Each example should be a dict containing different fields.

`Formatter` turns the raw dataset (maybe composed of several files) into the above standard format: get a list of examples, and record potential meta infomation.

`Processor` transforms each dict example into a processed dict example and potentially revised the meta information.

`Dataset` knows how to retrieve each sample.

`DataLoader` knows how to prepare batches for `Trainer`.


## Naming Convension
* **raw dataset:** we keep their original file names.
* **formatted dataset:** we can name them as `datasetname.formatted.split.suffix`.
* **processed dataset:** we can name them as `datasetname.processed.split.suffix`.
* We can also separately save data part and meta part if we need to use meta info frequently without having access to data part. E.g., we replace `datasetname` with `datasetname.data` and `datasetname.metadata`.



 
