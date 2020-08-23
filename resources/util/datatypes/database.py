class IdentifierDictionary:
    id_dictionary = dict()
    id_gen_protocol = "infer"
    next_id = 0

    def __init__(self, id_gen_protocol):
        if id_gen_protocol != "infer" and id_gen_protocol != "unique":
            raise ValueError("\"{}\" is not a valid id generation protocol.\nVALID: infer|unique")

    def __nextid__(self):
        self.next_id += 1
        return self.next_id

    def insert(self, data):
        hashable = str(data)
        if self.id_gen_protocol == "infer":
            if hashable not in self.id_dictionary:
                self.id_dictionary[hashable] = self.__nextid__()
        else:
            if hashable in self.id_dictionary:
                raise KeyError("\"{}\" already exists in the relation".format(hashable))
            else:
                self.id_dictionary[hashable] = self.__nextid__()
        return self.id_dictionary[hashable]


class RelationTable:
    schema = dict()
    next_id = 0
    y_dimension_size = 1

    def __nextid__(self):
        next_id = self.next_id + 1
        while next_id in self.schema:
            next_id += 1
        self.next_id = next_id
        return self.next_id

    def insert_row(self, iterable, predefined_id=None):
        from collections.abc import Sequence
        if predefined_id is not None:
            if predefined_id not in self.schema:
                if isinstance(iterable, Sequence) and not isinstance(iterable, (str, bytes, bytearray)):
                    if self.y_dimension_size == -1:
                        self.schema[predefined_id] = iterable
                        self.y_dimension_size = len(iterable)
                    else:
                        if self.y_dimension_size == len(iterable):
                            self.schema[predefined_id] = iterable
                        else:
                            raise TypeError(
                                "New values cannot be fitted in the relation.\nPrevious values length: {}\nCurrent valu"
                                "e length: {}".format(
                                    self.y_dimension_size, len(iterable)))
                else:
                    if self.y_dimension_size == -1:
                        self.schema[predefined_id] = [iterable, ]
                        self.y_dimension_size = 1
                    else:
                        if self.y_dimension_size == 1:
                            self.schema[predefined_id] = [iterable, ]
                        else:
                            raise TypeError(
                                "New values cannot be fitted in the relation.\nPrevious values length: {}\nCurrent valu"
                                "e length: {}".format(
                                    self.y_dimension_size, 1))
            else:
                raise ValueError("Relation ID {} already exists in relation table.".format(predefined_id))
        else:
            elected_id = self.__nextid__()
            self.insert_row(iterable, predefined_id=elected_id)
