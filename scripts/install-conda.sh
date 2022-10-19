set -e

# Get and install miniforge
if [ ! -d "$HOME/miniforge3" ]; then
  curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh
  bash Mambaforge-$(uname)-$(uname -m).sh -b -p "$HOME/miniforge3"
  rm Mambaforge-$(uname)-$(uname -m).sh
fi

# Make an init file so we don't need to edit bashrc
# Note this will currently work for bash terminals
envsubst '$HOME' < conda/miniforge-init.sh > ~/.miniforge-init.sh
source ~/.miniforge-init.sh

# Create the bluemira conda environment
mamba env create -f conda/environment.yml
conda activate bluemira

