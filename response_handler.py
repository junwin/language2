import os
from abc import ABC, abstractmethod


class ResponseHandler(ABC):
    @abstractmethod
    def handle_response(self, response, output_folder="output"):
        pass


class FileResponseHandler(ResponseHandler):
    def __init__(self, max_length=500):
        self.max_length = max_length
    def handle_response(self, response, output_folder="output"):
        if len(response) > self.max_length:
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            output_file_path = os.path.join(output_folder, f"response_{len(os.listdir(output_folder)) + 1}.txt")
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                output_file.write(response)
            return f"Response is too long. It has been saved to {output_file_path}"
        else:
            return response

