# Use the official Conda base image
FROM continuumio/miniconda3

# Set the working directory
WORKDIR /app

# Copy the environment.yml file into the Docker image
COPY environment.yml .

# Install the Conda environment
RUN conda env update -f environment.yml

# Copy the application code into the Docker image
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Set the entry point for the application
CMD ["python", "auto-group.py"]