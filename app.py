import os
import sys
import shutil
import cv2
import numpy as np
from rembg import remove
from tqdm import tqdm
import gdown
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing (CORS) for the Flask app

# Define paths for input, output, and processing status
ROOP_PATH = 'srv/'
OUTPUT_FRAMES_DIR = 'srv/output_frames'
OUTPUT_VIDEO_PATH = 'srv/output_video.mp4'
PROCESSING_COMPLETE_FLAG = 'srv/processing_complete.txt'

# Helper function to create directories if they don't exist
def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory created: {directory}")
    else:
        print(f"Directory already exists: {directory}")

# Helper function to clear directories
def clear_directories(paths):
    for path in paths:
        if os.path.exists(path):
            for file_name in os.listdir(path):
                file_path = os.path.join(path, file_name)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
            print(f"Directory {path} cleared successfully.")
        else:
            print(f"Directory {path} does not exist.")

# Helper function to download a file from Google Drive
def download_from_google_drive(url, output_path):
    try:
        file_id = url.split("/d/")[1].split("/view")[0]
        download_url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(download_url, output_path, quiet=False)
        print(f"File downloaded successfully to {output_path}")
    except Exception as e:
        print(f"Failed to download file from {url}. Error: {str(e)}")

# Endpoint to process video
import logging

logging.basicConfig(level=logging.DEBUG)

@app.route('/change_background', methods=['POST'])
def change_background():
    try:
        logging.debug("Starting background change process.")
        clear_directories([OUTPUT_FRAMES_DIR])
        os.makedirs(OUTPUT_FRAMES_DIR, exist_ok=True)

        video_url = request.form.get('video_url')
        background_url = request.form.get('background_url')

        if not video_url or not background_url:
            logging.error('Both video URL and background URL are required.')
            return jsonify({'error': 'Both video URL and background URL are required.'}), 400

        input_video_path = os.path.join(ROOP_PATH, 'input_video.mp4')
        new_background_path = os.path.join(ROOP_PATH, 'new_background.jpg')

        logging.debug(f"Downloading video from: {video_url}")
        download_from_google_drive(video_url, input_video_path)
        logging.debug(f"Downloading background from: {background_url}")
        download_from_google_drive(background_url, new_background_path)

        logging.debug(f"Opening video file: {input_video_path}")
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            logging.error(f'Could not open video {input_video_path}')
            return jsonify({'error': f'Could not open video {input_video_path}'}), 400

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logging.debug(f"Video properties - FPS: {fps}, Frame count: {frame_count}, Width: {frame_width}, Height: {frame_height}")
        new_background = cv2.imread(new_background_path)
        if new_background is None:
            logging.error(f'Could not load background image {new_background_path}')
            return jsonify({'error': f'Could not load background image {new_background_path}'}), 400
        new_background_resized = cv2.resize(new_background, (frame_width, frame_height))

        logging.debug("Processing frames.")
        for i in tqdm(range(frame_count), desc="Processing frames"):
            ret, frame = cap.read()
            if not ret:
                logging.error(f"Failed to read frame {i}")
                break

            try:
                result = remove(frame)
            except Exception as e:
                logging.error(f"Error removing background from frame {i}: {e}")
                continue

            if result.shape[-1] != 4:
                result = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)

            alpha_channel = result[:, :, 3] / 255.0
            for c in range(3):
                result[:, :, c] = result[:, :, c] * alpha_channel + new_background_resized[:, :, c] * (1 - alpha_channel)

            frame_output_path = os.path.join(OUTPUT_FRAMES_DIR, f'{i:04d}.png')
            cv2.imwrite(frame_output_path, result[:, :, :3])

        cap.release()

        logging.debug("Reassembling video from frames.")
        frame_files = sorted([f for f in os.listdir(OUTPUT_FRAMES_DIR) if f.endswith('.png')])
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(OUTPUT_VIDEO_PATH, fourcc, fps, (frame_width, frame_height))

        for frame_file in tqdm(frame_files, desc="Reassembling Video"):
            frame_path = os.path.join(OUTPUT_FRAMES_DIR, frame_file)
            frame = cv2.imread(frame_path)
            video_writer.write(frame)

        video_writer.release()

        with open(PROCESSING_COMPLETE_FLAG, 'w') as f:
            f.write('Processing complete')

        return jsonify({'message': 'Video processing started. Check the status for completion.'}), 202

    except Exception as e:
        logging.error(f"Exception occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_path_change_bg', methods=['GET'])
def get_path_change_bg():
    try:
        if os.path.exists(OUTPUT_VIDEO_PATH):
            return jsonify({
                'status': 'success',
                'message': 'Output file path retrieved successfully',
                'output_path': OUTPUT_VIDEO_PATH
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Output file not found'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/get_video_output_bg', methods=['GET'])
def get_video_output_bg():
    if os.path.exists(PROCESSING_COMPLETE_FLAG):
        return send_file(OUTPUT_VIDEO_PATH, as_attachment=True, mimetype='video/mp4', download_name='output_video.mp4')
    else:
        return jsonify({'message': 'Processing is still in progress. Please wait.'}), 202

if __name__ == "__main__":
    app.run(debug=True)  # Set debug=True for development; change to False for production
