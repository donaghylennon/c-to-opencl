# c-to-opencl

A translator from C with OpenMP to OpenCL

It is best to install in a virtual environment and run from there:
`python -m venv venv`
`source venv/bin/activate`
`pip install -e .`

To run:
`python -m c-to-opencl [-I<INCLUDE DIRECTORY>] [-D<MACRO DEFINITION>] <INPUT FILE> <OUTPUT C FILE> <OUTPUT CL FILE>`

To run test.py, make sure matplotlib is installed:

`pip install matplotlib`

And then run:

`python test.py translate`
`python test.py compile`
`python test.py run`
