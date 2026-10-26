# Backend Setup for Demo
0) Optional, only if you want the database:
    * from the repo's docker folder run: 'cp .env.example .env' then 'docker compose up -d'. 
    * The backend still runs w/o it, it just cannot save claims w/o it.
1) Make sure you are in the backend directory
2) Install Dependencies, run python -m pip install -r requirements.txt
2b) If it says that pip is not recognized, set up a virtual environment or set the interpreter, I do not understand
why it does this.
3) Start the Flask server, python app.py, you can verify it it is running, check at http://127.0.0.1:5000, the page should
display: "RedFlag backend is running!", if it doesn't, it's not running.
4) Make sure the server keeps running, as for now, the backend only runs locally until we find a hosted backend
5) Happy running the backend

# llm.py

This is a script that simply has 2 functions, get_client() and chat()
- get_client() will simply connect to the API endpoint
- chat() is an abstraction of making a prompt to the API.
- We'll be able to just put prompts into the chat() function inside our backend and it'll spit back out a response

## Testing llm.py
- make sure you have your .env set up, refer to .env.example
- Run the following command and replace Say hi with whatever you want
- python -c "import llm; print(llm.chat('Say hi'))"

## Testing llm backend integration
- Follow the setup instructions to start up the python server
- The function uses HTTP POST requests, so you'll need to use something that supports that, like curl
- You can run this curl command in the terminal, feel free to change the  content of the prompt to test. Note that if the output is too large it'll hit the token limit set by llm.py
- curl -X POST http://127.0.0.1:5000/llm_test -H "Content-Type: application/json" -d '{"prompt":"Tell me a funny joke"}'
- The frontend should be using HTTP POST requests for the api