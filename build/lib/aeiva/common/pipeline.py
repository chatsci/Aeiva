class Pipeline:
    r"""This class is used to rurn a list of functions into a pipeline."""
    def __init__(self, functions):
        self.functions = functions

    def run(self, *args, **kwargs):
        result = self.functions[0](*args, **kwargs)
        for f in self.functions[1:]:
            if isinstance(result, tuple):
                result = f(*result)
            else:
                result = f(result)
        return result
    
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
