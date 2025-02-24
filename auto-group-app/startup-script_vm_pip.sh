#!/bin/bash
# startup-script.sh

# Update and install necessary packages
sudo apt-get update
sudo apt-get install -y wget git

# Clone the repository
git clone https://github.com/RealWorldman/Group-Helper.git /home/$USER/Group-Helper

# Navigate to the project directory
cd /home/$USER/Group-Helper/auto-group-app

pip install -r requirements.txt

export GCP_PROJECT=$(gcloud config get-value project)

# Run the application
python3 auto-group.py