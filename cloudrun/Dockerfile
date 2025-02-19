# Use the official Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file into the Docker image
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the Docker image
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Set the entry point for the application
CMD ["python", "auto-group.py"]