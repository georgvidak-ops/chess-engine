class TranspositionTable:

    def __init__(self):
        self.tt = {}

    def probe(self, key):
        return self.tt.get(key)

    def store(self, key, entry):
        self.tt[key] = entry

    def clear(self):
        self.tt.clear()