import json


class Prompts:
    _instance = None

    @staticmethod
    def instance():
        if Prompts._instance is None:
            Prompts._instance = Prompts._Prompts()
        return Prompts._instance

    class _Prompts:
        prompts = []

        def load(self, file_name):
            try:
                with open(file_name, 'r') as f:
                    self.prompts = json.load(f)
            except FileNotFoundError:
                return {}

        def save(self):
            with open(self.file_name, 'w') as f:
                json.dump(self.prompts, f, indent=2)

        def add_prompt(self, name, prompt):
            self.prompts[name] = prompt

        def get_prompt(self, name: str):
            return self.prompts.get(name)
        

        def remove_prompt(self, name):
            if name in self.prompts:
                del self.prompts[name]
