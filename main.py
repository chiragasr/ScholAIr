
import threading
# from moviepy.editor import VideoFileClip, AudioFileClip
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
# from speechToText import transcribe_audio
# from recordAudio import record_audio
# from recordVideo import record_video   
# from moviepy.editor import VideoFileClip, AudioFileClip
#from speechToText import extract_audio_from_video, transcribe_audio
from openai import OpenAI
import os
import firebase_admin
from firebase_admin import auth, credentials, firestore


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

cred = credentials.Certificate("hhh2023-a2da1-firebase-adminsdk-h2zwt-5ae5f17a8b.json")
firebase_admin.initialize_app(cred)

db=firestore.client()


# Read the API key from a file
with open("APIKEY", "r") as file:
    api_key = file.read().strip()

# Set the API key as an environment variable
os.environ["OPENAI_API_KEY"] = api_key

client = OpenAI()


# @app.route('/process_media', methods=['POST'])
# def process_media():
#     media_path = request.json.get('media_path')
#     audio_path = media_path.replace('.mp4', '.wav')  # Assuming .mp4, adjust as necessary

#     # Extract audio from the video
#     extract_audio_from_video(media_path, audio_path)

#     # Now you can call your transcription function
#     transcription = transcribe_audio(audio_path)  # Define this function based on your transcription logic

#     return jsonify({"transcription": transcription})

# Endpoint for user registration (sign-up)
@app.route('/signup', methods=['POST'])
def signup():
    try:
        # Get user data from the request
        data = request.json
        email = data.get('email')
        password = data.get('password')

        # Create a new user account with the provided email and password
        user = auth.create_user(
            email=email,
            password=password
        )

        return jsonify({'success': True, 'uid': user.uid}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Endpoint for user login
@app.route('/login', methods=['POST'])
def login():
    try:
        # Get user data from the request
        data = request.json
        email = data.get('email')
        password = data.get('password')

        # Sign in the user with the provided email and password
        user = auth.sign_in_with_email_and_password(email,password)
        user_token = auth.create_custom_token(user.uid)

        return jsonify({'success': True, 'uid': user.uid, 'token': user_token}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/request_chatgpt', methods=['POST'])
def chatgpt():

    request_message_formatted = {'content': request_message, 'role': 'user'}
    messages_to_send = read_chat(username) + [request_message_formatted]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages_to_send
    )

    response_message_formatted = {'content': response.choices[0].message.content, 'role': 'assistant'}
    messages = [request_message_formatted]+[response_message_formatted]

    write_chat(username, messages)


@app.route('/write_chat', methods=['POST'])
def write_chat():
    # Get JSON data from the request
    data = request.json
    
    # Extract username and messages from the JSON data
    username = data.get('username')
    messages = data.get('messages', [])

    # Validate that both username and messages are present
    if not username or not messages:
        return jsonify({'error': 'Invalid request. Missing username or messages.'}), 400

    # Add messages to the chat in the database
    for message in messages:
        db.collection('users').document(username).collection('chat').add({'message': message})

    return jsonify({'success': True})

@app.route('/read_chat', methods=['GET'])
def read_chat():
    # Get username from the query parameters
    username = request.args.get('username')

    # Validate that username is present
    if not username:
        return jsonify({'error': 'Invalid request. Missing username.'}), 400

    # Retrieve messages from the chat in the database
    docs = db.collection('users').document(username).collection('chat').get()
    result = [doc.to_dict()['message'] for doc in docs]

    return jsonify(result)

@app.route('/add_scholarships', methods=['POST'])
def add_scholarships():
    data = request.json
    
    # Extract username and scholarships from the JSON data
    username = data.get('username')
    scholarships = data.get('scholarships', [])

    # Validate that both username and scholarships are present
    if not username or not scholarships:
        return jsonify({'error': 'Invalid request. Missing username or scholarships.'}), 400

    # Add scholarships to the database
    for scholarship in scholarships:
        title = scholarship.get('Title')
        if title:
            db.collection('users').document(username).collection('scholarship').document(title).set(scholarship)
        else:
            return jsonify({'error': 'Invalid scholarship. Missing title.'}), 400

    return jsonify({'success': True})


@app.route('/get_all_scholarships_brief', methods=['GET'])
def get_all_scholarships_brief():
    username = request.args.get('username')

    # Validate that username is present
    if not username:
        return jsonify({'error': 'Invalid request. Missing username.'}), 400

    docs = db.collection('users').document(username).collection('scholarship').get()
    result = []
    for doc in docs:
        scholarship_data = doc.to_dict()
        # Remove "Questions" and "Answers" fields if they exist
        scholarship_data.pop('Questions', None)
        scholarship_data.pop('Answers', None)
        scholarship_data.pop('Description', None)
        result.append(scholarship_data)

    return jsonify(result)


@app.route('/get_all_scholarships', methods=['GET'])
def get_all_scholarships():
    username = request.args.get('username')

    # Validate that username is present
    if not username:
        return jsonify({'error': 'Invalid request. Missing username.'}), 400

    docs = db.collection('users').document(username).collection('scholarship').get()
    result = [doc.to_dict() for doc in docs]

    return jsonify(result)

@app.route('/update_scholarship_answer', methods=['POST'])
def update_scholarship_answer():
    try:
        # Get data from the request
        data = request.json
        username = data.get('username')
        scholarship_title = data.get('title')
        index = data.get('index')
        updated_answer = data.get('updated_answer')

        # Validate required fields
        if not username or not scholarship_title or index is None or updated_answer is None:
            return jsonify({'error': 'Invalid request. Missing required fields.'}), 400

        # Retrieve the scholarship document
        scholarship_ref = db.collection('users').document(username).collection('scholarship').document(scholarship_title)
        scholarship_doc = scholarship_ref.get()

        # Check if the scholarship exists
        if not scholarship_doc.exists:
            return jsonify({'error': 'Scholarship not found.'}), 404

        # Update the 'Answers' field at the specified index
        current_answers = scholarship_doc.get('Answers', [])
        if 0 <= index < len(current_answers):
            current_answers[index] = updated_answer
            scholarship_ref.update({'Answers': current_answers})
            return jsonify({'success': True})

        return jsonify({'error': 'Invalid index.'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)