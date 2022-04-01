# c-to-opencl

A translator from C with OpenMP to OpenCL

To run:
`python -m c-to-opencl [-I<INCLUDE DIRECTORY>] [-D<MACRO DEFINITION>] <INPUT FILE> <OUTPUT C FILE> <OUTPUT CL FILE>`

To run test.py, make sure matplotlib is installed and then run

`python test.py translate`
`python test.py compile`
`python test.py run`
