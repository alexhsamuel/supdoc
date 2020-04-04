"""
Supdoc exceptions.
"""

#-------------------------------------------------------------------------------

class ModnameError(RuntimeError):
    """
    The modname could not be imported or otherwise found.
    """

    def __init__(self, modname):
        super().__init__(f"bad modname: {modname}")
        self.modname = modname



class QualnameError(RuntimeError):
    """
    The qualname could not be found.
    """

    def __init__(self, qualname):
        super().__init__(f"bad qualname: {qualname}")
        self.qualname = qualname



class FullNameError(RuntimeError):
    """
    A fully-qualified name could not be located.
    """

    def __init__(self, name):
        super().__init__(f"bad name: {name}")
        self.name = name



class ImportFailure(RuntimeError):
    """
    A module was not successfully imported.
    """

    def __init__(self, modname):
        super().__init__(f"import failed: {modname}")
        self.modname = modname



