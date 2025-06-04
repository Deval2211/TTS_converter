from flask import Flask, request, jsonify, render_template, send_from_directory
import os
from werkzeug.utils import secure_filename
from gradio_client import Client, handle_file  # Import Gradio client

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_BASE_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4', 'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_BASE_FOLDER'] = RESULTS_BASE_FOLDER

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_BASE_FOLDER, exist_ok=True)

# Initialize Gradio client for the E2-F5-TTS model
client = Client("mrfakename/E2-F5-TTS")

def allowed_file(filename):
    """
    Check if the file has an allowed extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_next_result_folder():
    """
    Generate the next result folder name (e.g., result_1, result_2, etc.).
    """
    existing_folders = [f for f in os.listdir(app.config['RESULTS_BASE_FOLDER']) if os.path.isdir(os.path.join(app.config['RESULTS_BASE_FOLDER'], f))]
    next_index = len(existing_folders) + 1
    return os.path.join(app.config['RESULTS_BASE_FOLDER'], f'result_{next_index}')

@app.route('/')
def index():
    """
    Render the main HTML page.
    """
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_and_process():
    """
    Handle file and text uploads, process them with the Gradio client.
    """
    if 'file' not in request.files or 'text' not in request.form:
        return jsonify({'error': 'File or text input missing'}), 400

    file = request.files['file']
    text = request.form['text']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        try:
            # Save the file
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Process the file and text with the Gradio client
            result = process_with_gradio(file_path, text)

            # Create a new result folder
            result_folder = get_next_result_folder()
            os.makedirs(result_folder, exist_ok=True)

            # Save Gradio result files to the new result folder
            audio_output_path = os.path.join(result_folder, 'audio_result.wav')
            image_output_path = os.path.join(result_folder, 'image_result.png')

            # Move audio and image files to the result folder
            os.rename(result[0], audio_output_path)  # Move audio file
            os.rename(result[1], image_output_path)  # Move image file

            return jsonify({
                'message': 'File uploaded and processed successfully',
                'filename': filename,
                'audio_result': f'/results/{os.path.basename(result_folder)}/audio_result.wav',
                'image_result': f'/results/{os.path.basename(result_folder)}/image_result.png',
                'text_result': result[2]
            })
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/results/<path:filename>')
def serve_result(filename):
    """
    Serve result files (audio or image) from the results directory.
    """
    try:
        return send_from_directory(app.config['RESULTS_BASE_FOLDER'], filename)
    except Exception as e:
        return jsonify({'error': f'Error retrieving result file: {str(e)}'}), 404

def process_with_gradio(file_path, text_input):
    """
    Process the uploaded file and text input using the Gradio client for E2-F5-TTS.
    """
    try:
        result = client.predict(
            ref_audio_input=handle_file(file_path),  # Reference audio input
            ref_text_input=text_input,              # Reference text input
            gen_text_input=text_input,              # Text to generate speech for
            remove_silence=False,
            cross_fade_duration_slider=0.15,
            nfe_slider=32,
            speed_slider=1,
            api_name="/basic_tts"
        )
        return result
    except Exception as e:
        return {"error": f"Gradio processing error: {str(e)}"}

if __name__ == '__main__':
    app.run(debug=True)