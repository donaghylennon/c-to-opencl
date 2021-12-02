# Timelog

* Translation of C code to OpenCL
* Lennon Donaghy
* 2371694D
* Syed Waqar Nabi

## Guidance

* This file contains the time log for your project. It will be submitted along with your final dissertation.
* **YOU MUST KEEP THIS UP TO DATE AND UNDER VERSION CONTROL.**
* This timelog should be filled out honestly, regularly (daily) and accurately. It is for *your* benefit.
* Follow the structure provided, grouping time by weeks.  Quantise time to the half hour.

## Week 1

### 5 Oct 2021

* *0.5 hour* meeting with supervisor

### 8 Oct 2021

* *2 hours* Read suggested papers on translation from Fortran/C to OpenCL
* *1 hour* Researched options for parsing/lexing with Python

### 9 Oct 2021

* *1 hour* Downloaded and looked through Rodinia test suite code

## Week 2

### 12 Oct 2021

* *0.5 hour* meeting with supervisor

### 17 Oct 2021

* *2 hours* Researched OpenCL and wrote example equivalent programs

## Week 3

### 18 Oct 2021

* *2 hours* Started experimenting and learning to use pycparser

### 19 Oct 2021

* *0.5 hour* meeting with supervisor

### 22 Oct 2021

* *4 hours* Worked on getting a working OpenCL setup, and running examples from Nvidia and GitHub

### 24 Oct 2021

* *4 hours* Wrote initial translation code, to translate simple for loop functions directly to OpenCL kernels

## Week 4

### 27 Oct 2021

* *2 hours* Studied paper on translation of OpenMP code to GPGPU code

### 28 Oct 2021

* *1.5 hours* Studied paper on parallelization of loop nests

### 30 Oct 2021

* *3 hours* Gathered and read more possibly useful papers

## Week 5

### 7 Nov 2021

* *2.5 hours* Wrote a first version of the template for host side boilerplate code

* *4 hours* Started to write some code to generate host side boilerplate

## Week 6

### 8 Nov 2021

* *3.5 hours* Continued working on code to generate host side boilerplate

### 9 Nov 2021

* *0.5 hours* Meeting with supervisor

* *2.5 hours* Wrote classes to gather info required to generate host code from original code

## Week 7

### 15 Nov 2021

* *6 hours* Wrote logic to handle parsing the ast for the information required to generate the host side
  code, as well as the logic to fully generate that code, along with numerous fixes and edits to the template
  file used for this

### 16 Nov 2021

* *0.5 hours* Meeting with supervisor

## Week 8

### 24 Nov 2021

* *3 hours* Researched OpenMP and tested some minor example programs to familiarise myself with it

### 27 Nov 2021

* *3.5 hours* Read through a number of programs from the Rodinia suite in order to understand how more
  advanced OpenCL and OpenMP are used

## Week 9

### 29 Nov 2021

* *2 hours* Reseached the use of the visitor pattern for visiting abstract syntax trees

* *6 hours* Restructure translation code into visitor pattern, and add some more features to translation
  using this

### 1 Dec 2021

* *3 hours* Researched Python package structure and reorganised my project so it is installible via pip

