import subprocess

def setup_environment():
    """
    Installs necessary dependencies for Roop and other processing tasks.
    """
    # List of Python packages to install
    packages = [
        'pillow',
        'ffmpeg-python',
        'tqdm',
        'rembg',
        'flask-ngrok',
        'pyngrok',
        'flask_cors',
        'gunicorn'
    ]

    # Install Python packages
    for package in packages:
        try:
            print(f"Installing Python package: {package}")
            subprocess.run(['pip', 'install', package], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error installing package {package}: {e}")

    # Install system package ffmpeg
    try:
        print("Installing system package: ffmpeg")
        subprocess.run(['apt-get', 'install', '-y', 'ffmpeg'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error installing system package ffmpeg: {e}")
