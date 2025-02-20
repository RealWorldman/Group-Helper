#!/bin/bash
# startup-script.sh

# Update and install necessary packages
sudo apt-get update
sudo apt-get install -y python3-pip git

# Clone the repository
git clone https://github.com/RealWorldman/Group-Helper.git /home/$USER/Group-Helper

# Navigate to the project directory
cd /home/$USER/Group-Helper

# Install the Python dependencies
sudo pip3 install --no-cache-dir -r requirements.txt

# Run the application
python3 auto-group.py