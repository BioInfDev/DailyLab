class ARRInterface:
    def __init__(self):
        #выполнять проверку наличия методов для ARR
        pass
    def add(self):
        pass
    def rename(self):
        self.setEnabled(True)
    def remove(self):
        self.setParent(None)
        self.deleteLater()

class DnDInterface:
    pass