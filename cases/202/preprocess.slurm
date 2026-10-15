#!/bin/bash
#SBATCH --job-name=campus202-pre
#SBATCH --partition=<PARTITION>
#SBATCH --qos=<QOS>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=preprocess-%j.log
set -eo pipefail
. /etc/profile.d/modules.sh
# Use the personal module environment which successfully built preprocessing.
module load "<PREPROCESSING_RUNTIME_MODULE>" "<PYTHON_MODULE>"
SOURCE_DIR="<SOURCE_DIR>"
GNU_OPENMP="$(/usr/bin/gfortran -print-file-name=libgomp.so.1)"
test -f "$GNU_OPENMP" || { echo "GNU OpenMP library not found"; exit 1; }
export LD_LIBRARY_PATH="$(dirname "$GNU_OPENMP"):${LD_LIBRARY_PATH:-}"
export LD_PRELOAD="$GNU_OPENMP"
export PREPROC_NCPU="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export VIEW3D_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export PYTHONUNBUFFERED=1
cd "$SLURM_SUBMIT_DIR"
"$SOURCE_DIR/tools/python/.venv/bin/python" -c "from udprep import ibm_preproc_f2py; print('IBM OK')"
"$SOURCE_DIR/tools/python/.venv/bin/python" -u "$SOURCE_DIR/tools/write_inputs.py" "$PWD"
