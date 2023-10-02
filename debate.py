class Debater():
    def __init__(self, name, style, avatar='😀'):
        self.name = name
        self.style = style
        self.avatar = avatar

class Debate():
    def __init__(self, debater1: Debater, debater2: Debater, prompt: str, Nrounds: int):
        self.debater1 = debater1
        self.debater2 = debater2
        self.prompt = prompt
        self.Nrounds = Nrounds
        self.messages = []
        
        #order
        self.order = [debater1, debater2]
        random.shuffle(self.order)
        self.order = self.order * Nrounds

    def next_message(self):
        ...