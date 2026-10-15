#!/bin/bash
#SBATCH --job-name=campus202-thermal
#SBATCH --partition=<PARTITION>
#SBATCH --qos=<QOS>
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=02:00:00
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
for input in facets.inp.202 facetarea.inp.202 factypes.inp.202 Tfacinit.inp.202 netsw.inp.202 svf.inp.202 vfsparse.inp.202 prof.inp.202 lscale.inp.202; do
    test -s "$input" || { echo "Missing input: $input"; exit 1; }
done
for kind in solid fluid_boundary facet_sections; do
    for grid in u v w c; do
        test -f "${kind}_${grid}.txt" || { echo "Missing IBM file: ${kind}_${grid}.txt"; exit 1; }
    done
done
test -x "$SOURCE_DIR/build/intel-release/u-dales"
mpirun -np "$SLURM_NTASKS" "$SOURCE_DIR/build/intel-release/u-dales" namoptions.202
