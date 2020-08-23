from abc import ABCMeta, abstractmethod
import os
import bz2
import inspect
import pickle
import logging
import importlib
import sys


class BaseReader(metaclass=ABCMeta):

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def read_batch(self, batch_size):
        pass


class Bz2BagReader(BaseReader):
    """
    Bz2BagReader documentation
    """

    def __init__(self, *file_paths, logger=None):
        self.file_paths = tuple(os.path.abspath(os.path.expanduser(file_path)) for file_path in file_paths if
                                os.path.exists(os.path.abspath(os.path.expanduser(file_path))))
        assert len(self.file_paths) > 0, "No valid files could be located"

        self.file_obj = None

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())

    def __iter__(self):
        if self.file_obj is not None:
            self.file_obj.close()
        self.file_index = 0
        self.object_index = 0
        self.file_obj = bz2.BZ2File(self.file_paths[self.file_index], "r")
        self.unpickler = pickle.Unpickler(self.file_obj)
        return self

    def __next__(self):
        read_further = True
        while read_further:
            try:
                object_value = self.unpickler.load()
            except EOFError:
                self.file_index += 1
                self.file_obj.close()
                self.file_obj = None
                if self.file_index == len(self.file_paths):
                    raise StopIteration
                else:
                    self.file_obj = bz2.BZ2File(self.file_paths[self.file_index], "r")
                    self.unpickler = pickle.Unpickler(self.file_obj)
                    continue
            except OSError:
                self.logger.error(
                    "An error occurred while attempting to read from the file {}.\nEnsure that the file can be read by "
                    "the provided reader: Bz2BagReader".format(self.file_paths[self.file_index])
                )
                self.file_index += 1
                continue

            self.object_index += 1
            return object_value

    def read(self):
        if self.file_obj is None:
            iter(self)
        val = next(self)
        return val

    def read_batch(self, batch_size):
        return tuple(next(self) for _ in range(batch_size))


class DblpV10Reader(BaseReader):
    """
    This is an implementation of the underlying BaseReader focused on reading the files of DBLP Citation Network,
    provided by ArnetMiner.

    It can be created given the paths to the text files consisting the dataset. Optional keyword arguments are:
        * logger: pass an existing logger to log information about which files are ignored and possible errors

    The reader can read from text files that contain records from scientific articles. Each line has to be a JSON object
    and must contain the fields of "id" (identifier of the article) and "abstract" (text of the article abstract). Apart
    from these field the reader also attempts to fetch the fields of title and year, returning an empty string "" if
    these are not available.

    Lines that are not in valid JSON representation are ignored. Records that also do not contain the mandatory JSON
    properties of "id" and "abstract" are also ignored.

    DblpV10Reader treats all the text files as a whole virtual file and can be treated as text file handle over this
    virtual file. It opens the files in read mode but still it is advised that the reader is closed when reading is
    finished.
    """

    def __init__(self, *file_paths, logger=None):
        self.file_paths = tuple(os.path.abspath(os.path.expanduser(file_path)) for file_path in file_paths if
                                os.path.exists(os.path.abspath(os.path.expanduser(file_path))))
        assert len(self.file_paths) > 0, "No valid files could be located"

        self.file_obj = None
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())

    def __iter__(self):
        if self.file_obj is not None:
            self.file_obj.close()
        self.file_index = 0
        self.line_index = 0
        self.file_obj = open(self.file_paths[self.file_index], "r", encoding="utf-8")
        return self

    def __next__(self):
        read_further = True
        while read_further:
            line = self.file_obj.readline()
            if line == "":
                self.file_index += 1
                self.file_obj.close()
                self.file_obj = None
                if self.file_index == len(self.file_paths):
                    raise StopIteration
                else:
                    self.file_obj = open(self.file_paths[self.file_index], "r", encoding="utf-8")
                    continue
            self.line_index += 1
            try:
                line_dictionary = json.loads(line.strip())
            except json.decoder.JSONDecodeError:
                self.logger.debug("File {}, line {}: Line did not satisfy the JSON validity"
                                  .format(self.file_paths[self.file_index], self.line_index))
                continue
            try:
                identifier = line_dictionary["id"]
                abstract = line_dictionary["abstract"]
            except KeyError:
                self.logger.debug("File {}, line {}: Line is missing the mandatory JSON properties (id, abstract)"
                                  .format(self.file_paths[self.file_index], self.line_index))
                continue
            title = line_dictionary.get("title", None)
            year = int(line_dictionary.get("year", -1))
            return identifier, abstract, {"title": title, "year": year}

    def read(self):
        if not hasattr(self, "file_obj"):
            iter(self)
        val = next(self)
        return val

    def read_batch(self, batch_size):
        return tuple(next(self) for _ in range(batch_size))


available_readers = {
    (cl[0].lower()[:-len("Reader")] if cl[0].endswith("Reader") else cl[0].lower()): cl[1]
    for cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if
    (issubclass(cl[1], BaseReader) and cl[0] != "BaseReader" and cl[0].endswith("Reader"))
}
