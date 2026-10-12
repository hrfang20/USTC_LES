#!/bin/bash
#SBATCH --job-name=udales201
#SBATCH --partition=<PARTITION>
#SBATCH --qos=<QOS>
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --output=udales-%j.log

set -euo pipefail
. /etc/profile.d/modules.sh
module load <COMPILER_MODULE>
module load <MPI_MODULE>
module load <FFTW_MODULE>
export UDALES_DEPS="$HOME/local/udales-intel"
export PATH="$UDALES_DEPS/bin:$PATH"
export LD_LIBRARY_PATH="$UDALES_DEPS/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=1
cd "$SLURM_SUBMIT_DIR"
UDALES_EXE="<SOURCE_DIR>/build/intel-release/u-dales"
test -x "$UDALES_EXE"
mpirun -np "$SLURM_NTASKS" "$UDALES_EXE" namoptions.201
