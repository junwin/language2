# Service for chatbots and simple web apps
# install

python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

pip install -r requirements.txt


python -m spacy download en_core_web_sm
python -m spacy download es_core_news_sm

# Virtual environment

To activate:
run: venv\Scripts\activate

# running in flask
python app.py

You can access the Swagger UI at https://localhost:5000/api/docs

The web service will start listening on http://localhost:5000. You can send a POST request to http://localhost:5000/ask with a JSON payload containing the question:

json



The web service will return the response in the following format:

json

{
  "question": "What is the first sentence in the wind in the willows",
  "agentName": "lucy",
  "accountName": "junwin",
  "conversationId": "1"
}


{
  "response": "The first sentence in \"The Wind in the Willows\" by Kenneth Grahame is: \"The Mole had been working very hard all the morning, spring-cleaning his little home.\""
}


## Setting up HTTPS in Flask using mkcert

To enable HTTPS in your Flask application, you can generate a self-signed certificate using mkcert. Follow the steps below to get started:

1. Install mkcert by following the instructions in the official documentation: [https://github.com/FiloSottile/mkcert#installation](https://github.com/FiloSottile/mkcert#installation).
2. Once you have installed mkcert, generate a certificate for your desired domain name(s) by running the following command: `mkcert example.com` (replace example.com with your own domain name if desired).
3. This will generate two files: a `.pem` file and a `-key.pem` file. These files are your SSL certificate and private key, respectively.
4. In your Flask application code, add the following lines to enable HTTPS using the generated certificate and key:

```python
import ssl

if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('example.com.pem', 'example.com-key.pem')
    app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=True)
```

That's it! You should now be able to access your Flask application using HTTPS. Note that because you are using a self-signed certificate, your browser may display a security warning when you try to access it. This is normal and you can safely ignore it - just be sure not to enter any sensitive information on the site until you have verified that the certificate's fingerprint matches the expected value.

