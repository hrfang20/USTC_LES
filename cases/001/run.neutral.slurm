#!/bin/bash
#SBATCH --job-name=campus001-neutral
#SBATCH --partition=<PARTITION>
#SBATCH --qos=<QOS>
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=udales-%j.log
set -eo pipefail
. /etc/profile.d/modules.sh
module load "<COMPILER_MODULE>" "<MPI_MODULE>" "<FFTW_MODULE>"
SOURCE_DIR="<SOURCE_DIR>"
export UDALES_DEPS="<DEPS_PREFIX>"
export PATH="$UDALES_DEPS/bin:$PATH"
export LD_LIBRARY_PATH="$UDALES_DEPS/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=1
cd "$SLURM_SUBMIT_DIR"
for input in facets.inp.001 factypes.inp.001 solid_c.txt solid_u.txt solid_v.txt solid_w.txt fluid_boundary_c.txt fluid_boundary_u.txt fluid_boundary_v.txt fluid_boundary_w.txt facet_sections_c.txt facet_sections_u.txt facet_sections_v.txt facet_sections_w.txt; do
    test -f "$input" || { echo "Missing IBM input: $input"; exit 1; }
done
test -x "$SOURCE_DIR/build/intel-release/u-dales"
mpirun -np "$SLURM_NTASKS" "$SOURCE_DIR/build/intel-release/u-dales" namoptions.001
