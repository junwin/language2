# Service for chatbots and simple web apps
# insatll

python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

pip install -r requirements.txt


python -m spacy download en_core_web_sm
python -m spacy download es_core_news_sm


# running in flask
python app.py

You can access the Swagger UI at https://localhost:5000/api/docs

The web service will start listening on http://localhost:5000. You can send a POST request to http://localhost:5000/ask with a JSON payload containing the question:

json

{
  "question": "Your question here"
}

The web service will return the response in the following format:

json

{
  "response": "AI assistant's response"
}
