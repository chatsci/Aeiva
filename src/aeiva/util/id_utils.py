class IDGenerator:
    def __init__(self):
        self.file_to_id = {}
        self.next_id = 0

    def get_id(self, file_name):
        if file_name not in self.file_to_id:
            self.file_to_id[file_name] = self.next_id
            self.next_id += 1
        return self.file_to_id[file_name]
