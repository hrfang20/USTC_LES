#!/bin/bash
#SBATCH --job-name=campus001-pre
#SBATCH --partition=<PARTITION>
#SBATCH --qos=<QOS>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=preprocess-%j.log
set -eo pipefail
. /etc/profile.d/modules.sh
module load "<GNU_COMPILER_MODULE>" "<PYTHON_MODULE>" "<CMAKE_MODULE>"
SOURCE_DIR="<SOURCE_DIR>"
export PREPROC_NCPU=4 NUMBA_NUM_THREADS=4 OMP_NUM_THREADS=4
cd "$SLURM_SUBMIT_DIR"
"$SOURCE_DIR/tools/python/.venv/bin/python" "$SOURCE_DIR/tools/write_inputs.py" "$PWD"
