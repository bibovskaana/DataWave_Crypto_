class ServiceSubject:
    def init(self):
        self.observers = []

    def attach(self, observer):
        self.observers.append(observer)

    def notify(self, event, data):
        for obs in self.observers:
            getattr(obs, event)(data)