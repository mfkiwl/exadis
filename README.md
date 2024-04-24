# ExaDiS

ExaDiS version 0.1

ExaDiS (Exascale Dislocation Simulator) is a set of software modules written to enable numerical simulations of large groups of moving and interacting dislocations, line defects in crystals responsible for crystal plasticity. By tracking time evolution of sufficiently large dislocation ensembles, ExaDiS predicts plasticity response and plastic strength of crystalline materials.

ExaDiS is built around a portable library of core functions for Discrete Dislocation Dynamics (DDD) method specifically written to perform efficient computations on new HPC architectures (e.g. GPUs). Simulations can be driven through the C++ or python interfaces. The python binding module can also be interfaced with the upcoming [OpenDiS](https://github.com/opendis/) framework.

Note: Although ExaDiS is a fully functional code, it is currently under active development and is subject to frequent updates and bug fixes. There is no guarantee of stability and one should expect occasional breaking changes to the code.



## Quick start

ExaDiS is implemented using the [Kokkos](https://kokkos.org) framework and built using the CMake build system. In most situations, the full code (kokkos + exadis) can be built using the `full_build.sh` script provided in this repository:

* Clone this repository
```
git clone https://github.com/LLNL/exadis.git
cd exadis
```
* Configure the build options for your own system (`SYS=user`) in script `full_build.sh` at lines 28-45. For instance, for building in serial mode for CPU, specify `SERIAL_user=On`. To build for CUDA GPU, specify `CUDA_user=On` and your target CUDA architecture, e.g. `ARCH_user=VOLTA70`.
* Build the code by running the script
```
./full_build.sh
```
The script will first clone, build and install kokkos, and then build exadis using the local kokkos install.
* Run an example to test your installation
```
cd examples/02_frank_read_src
python test_frank_read_src.py
```

Note: The `full_build.sh` script is intended to simplify the building process, e.g. if Kokkos is not installed on your machine and/or you are not too sure how to install it. While it should work fine in most cases (e.g. CPU build), it may fail on more complex environments (e.g. GPU build on HPC machines). If the build fails, it is recommended that the user follows the detailed manual build process described in the Installation section below.


## Installation

ExaDiS is implemented using the [Kokkos](https://kokkos.org) framework and built using the CMake build system. An installation of the code typically follows the following steps:

* Step 1: Install Kokkos
    * If Kokkos is installed on your machine, you can skip this step
    * If Kokkos is not installed on your machine, you can install it from the kokkos repository:
        * Clone the kokkos repository
        ```
        git clone https://github.com/kokkos/kokkos.git --branch 4.2.00
        cd kokkos
        ```
        * Build and install kokkos
            * Example: OpenMP CPU build
            ```
            mkdir build && cd build
            cmake \
                -DCMAKE_CXX_COMPILER=c++ \
                -DCMAKE_INSTALL_PREFIX=../install \
                -DCMAKE_POSITION_INDEPENDENT_CODE=On \
                -DKokkos_ENABLE_SERIAL=On \
                -DKokkos_ENABLE_OPENMP=On \
                ..
            make -j8
            make install
            cd ../..
            ```
            * Example: CUDA GPU build for `VOLTA70` device architecture
            ```
            mkdir build && cd build
            cmake \
                -DCMAKE_CXX_COMPILER=c++ \
                -DCMAKE_INSTALL_PREFIX=../install \
                -DCMAKE_POSITION_INDEPENDENT_CODE=On \
                -DKokkos_ENABLE_SERIAL=On \
                -DKokkos_ENABLE_OPENMP=On \
                -DKokkos_ENABLE_CUDA=On \
                -DKokkos_ENABLE_CUDA_LAMBDA=On \
                -DKokkos_ARCH_VOLTA70=On \
                ..
            make -j8
            make install
            cd ../..
            ```
      
* Step 2: Build ExaDiS
    * Clone this repository
    ```
    git clone https://github.com/LLNL/exadis.git
    cd exadis
    ```
    * Initialize the submodules (required if enabling the python binding)
    ```
    git submodule init
    git submodule update
    ```
    * Build the code. Examples of building scripts are provided at the root of the exadis project, e.g. see file `build_mac.sh`. The Kokkos root path must be specified with option `-DKokkos_ROOT`. A typical build instruction will look like:
    ```
    mkdir build && cd build
    cmake \
        -DKokkos_ROOT=/path/to/your/kokkos/install_dir \
        -DCMAKE_CXX_COMPILER=c++ \
        -DPYTHON_BINDING=On \
        ..
    make -j8
    cd ..
    ```
    Note: building with nvcc (Cuda) may be pretty slow, please be patient! 
    For additional building options and troubleshooting see section Detailed build instructions below.
    
* Step 3: Test your installation by running an example (assuming `-DPYTHON_BINDING=On`)
```
cd examples/02_frank_read_src
python test_frank_read_src.py
```

### Detailed build instructions

#### Dependencies

* Kokkos:
    * ExaDiS is implemented using the Kokkos framework. Kokkos must be installed in the machine prior to building ExaDiS. Instructions on how to configure/install Kokkos are found at https://github.com/kokkos/kokkos. ExaDiS will be compiled with the backend(s) that Kokkos was built for. For instance, if Kokkos was built to run on GPUs (e.g. compiled with option `-DKokkos_ENABLE_CUDA=ON`), then ExaDiS will be compiled to run on GPUs. The path to the Kokkos installation must be provided with ExaDiS build option `-DKokkos_ROOT`.
* FFT libraries
    * ExaDiS uses FFT libraries to compute long-range elastic interactions. To compile ExaDiS without this module (e.g. if no FFT library is available) use build option `-DEXADIS_FFT=Off`. Otherwise (default), different FFT libraries are invoked depending on the target backend:
        * Serial/OpenMP backend: uses FFTW. Include and library directories can be specified with build options `FFTW_INC_DIR` and `FFTW_LIB_DIR`, respectively.
        * Cuda backend: uses cuFFT
        * HIP backend: uses hipFFT
        
* pybind11
    * ExaDiS uses [pybind11](https://github.com/pybind/pybind11) for the python binding module. pybind11 is included as a submodule to the repository and will be automatically cloned to the `python/pybind11` folder when using git submodule:
    ```
    git submodule init
    git submodule update
    ```
    To use a specific python version/executable, use build option `PYTHON_EXECUTABLE`.
    To compile ExaDiS without this module, use build option `-DPYTHON_BINDING=Off`.


#### Build options

Below is a list of the various CMake build option specific to ExaDiS. The build options are passed as arguments to the cmake command as `-D<BUILD_OPTION_NAME>=<value>`.

* `Kokkos_ROOT` (required) : specifies the path of the Kokkos installation
* `PYTHON_BINDING` (optional, default=`On`): enable/disable compilation of the python module
* `PYTHON_EXECUTABLE` (optional, default=''): specifies the path of a specific python version to be used
* `EXADIS_FFT` (optional, default=`On`): enable/disable compilation of the FFT-based long-range force calculation module
* `FFTW_INC_DIR` (optional, default=''): specifies the path of the FFTW include directory
* `FFTW_LIB_DIR` (optional, default=''): specifies the path of the FFTW library directory
* `EXADIS_BUILD_EXAMPLES` (optional, default=`Off`): builds examples that are in the `examples/` folder
* `EXADIS_BUILD_TESTS` (optional, default=`Off`): builds test cases that are in the `tests/` folder


## Project structure

Brief description of the directories within this repository:

* `examples/` : examples of scripts and simulations
* `python/` : files related to the python binding implementation
* `src/` : C++ source and header files (`*.cpp`, `*.h`)
* `tests/` : files for testing and debugging

## Simulation examples

There are several examples of simulation files located in the `examples/` folder. These examples show the different ways that ExaDiS simulations can be setup and run.

For instance, folder `examples/02_frank_read_src` provides an example of a simple Frank-Read source simulation, driven either through the C++ interface or the python interface. 

Folders `examples/21_bcc_Ta_100nm_2e8` and `examples/22_fcc_Cu_15um_1e3` provide examples of typical large-scale DDD production runs (a BCC and a FCC simulation) driven through the C++ or the python interfaces.

The python simulations requires the code to be compiled with the python binding module using build option `-DPYTHON_BINDING=On`. The C++ simulations can be compiled by using build option `-DEXADIS_BUILD_EXAMPLES=On`.


## License

ExaDiS is released under the BSD-3 license. See [LICENSE](LICENSE) for details.

LLNL-CODE-862972


## Author
Nicolas Bertin (bertin1@llnl.gov)
