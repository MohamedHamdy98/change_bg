# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install system packages (like ffmpeg) and clean up to reduce image size
RUN apt update && \
    apt install --no-install-recommends -y ffmpeg 

# Copy the rest of the application code into the container
COPY . /app

# Expose port 5000 for the Flask app
EXPOSE 8000

# Run the Flask app using gunicorn in production
CMD ["uvicorn", "app_fast:app", "--host", "0.0.0.0", "--port", "8000"]
