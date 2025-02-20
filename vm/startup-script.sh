#!/bin/bash
# startup-script.sh

# Update and install necessary packages
sudo apt-get update
sudo apt-get install -y wget git

# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$PATH"

# Initialize conda
source $HOME/miniconda/etc/profile.d/conda.sh

# Clone the repository
git clone https://github.com/RealWorldman/Group-Helper.git /home/$USER/Group-Helper

# Navigate to the project directory
cd /home/$USER/Group-Helper/vm

# Create the conda environment
conda env create -f environment.yml

# Activate the environment
conda activate discord

export GCP_PROJECT=$(gcloud config get-value project)

# Run the application
python3 auto-group.py