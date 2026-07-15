# Load MPI module. This should be available as standard module on a cluster.
# If not, build your own MPI and update PATH, LD_LIBRARY_PATH
module load openmpi-4.1.1

# Set MPI_HOME by quering path loaded by site module
export MPI_HOME=$(which mpicc | sed s/'\/bin\/mpicc'//)

#module load nvhpc-nompi/21.3
#module load nvhpc/21.3

# Set NVHPC_HOME by quering path
#export NVHPC_HOME=$(which nvcc | sed s/'\/bin\/nvcc'//)
