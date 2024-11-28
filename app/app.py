import os
import logging
import boto3
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# S3 Configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'your-s3-bucket-name')
UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize S3 client using IAM role
# No explicit credentials - will use instance metadata
s3_client = boto3.client('s3')

@app.route('/upload', methods=['POST'])
def upload_log():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    local_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(local_path)

    try:
        # Upload using IAM role
        s3_client.upload_file(local_path, S3_BUCKET, filename)
        os.remove(local_path)

        return jsonify({
            "message": f"File {filename} uploaded successfully",
            "bucket": S3_BUCKET,
            "filename": filename
        }), 200

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/list', methods=['GET'])
def list_logs():
    try:
        # List objects using IAM role
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)

        # Extract file names, handle case of empty bucket
        files = [obj['Key'] for obj in response.get('Contents', [])]

        return jsonify({
            "files": files,
            "total_files": len(files)
        }), 200

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_log(filename):
    try:
        local_path = os.path.join(UPLOAD_FOLDER, filename)

        # Download using IAM role
        s3_client.download_file(S3_BUCKET, filename, local_path)

        return send_file(local_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({"error": str(e)}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_log(filename):
    try:
        # Delete using IAM role
        s3_client.delete_object(Bucket=S3_BUCKET, Key=filename)

        return jsonify({
            "message": f"File {filename} deleted successfully",
            "bucket": S3_BUCKET
        }), 200

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "S3 Log Manager is running",
        "bucket": S3_BUCKET
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)