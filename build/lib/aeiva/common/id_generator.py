class IDGenerator:
    """
    A simple class to generate unique IDs for distinct names.
    
    Attributes:
        name_to_id (dict): A dictionary to map names to IDs.
        next_id (int): The next ID to be assigned.
    """

    def __init__(self):
        """
        Constructs all the necessary attributes for the IDGenerator object.
        
        Attributes:
            name_to_id (dict): Initializes an empty dictionary to map names to IDs.
            next_id (int): Initializes the next ID to be assigned as 0.
        """
        self.name_to_id = {}
        self.next_id = 0

    def get_id(self, name: str) -> int:
        """
        Returns the ID of the 'name'. If 'name' does not exist, assigns a new ID.
        
        Parameters:
            name (str): The name for which the ID is required.
        
        Returns:
            int: The ID associated with the 'name'.
        """
        if name not in self.name_to_id:
            self.name_to_id[name] = self.next_id
            self.next_id += 1
        return self.name_to_id[name]
