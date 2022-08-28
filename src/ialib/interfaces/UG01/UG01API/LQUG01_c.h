/******************************************************************************
  UG01 Library Definitions (Header File) 

Description:
    This file defines the functions, the data types and constants 
    in the UG01 library (LQUG01_c.lib and LQUG01_c.dll).
   This file is located in the directory of "C:\Program Files\LQElectronics\UG01\UG01API\" 
   for 32bit windows OS or in the directory of 
   "C:\Program Files (x86)\LQElectronics\UG01\UG01API\".
   for 64bit windows  OS. 
  The library of LQUG01_c.dll can be called with  _cdecl. 

    When including this file in a new project, this file can either be
    referenced from the directory in which it was installed or copied
    directly into the user application folder. If the first method is
    chosen to keep the file located in the folder in which it is installed
    then include paths need to be added so that the library and the
    application both know where to reference each others files.
********************************************************************************

 FileName:        LQUG01_c.h
 Equipment used for:       UG01 USB to GPIB adapter
 Library:	LQUG01_c.lib\LQUG01_c.dll
 Company:         LQ ELECTRONICS CORP

Software License Agreement

The software supplied herewith by LQ ELECTRONICS CORP
(the “Company”) for its UG01 USB -GPIB controller is intended and
supplied to you, the Company’s customer, for use solely and
exclusively on UG series products. The software is owned by the
Company and/or its supplier, and is protected under applicable 
copyright laws. All rights are reserved. Any use in violation of the
foregoing restrictions may subject the user to criminal sanctions 
under applicable laws, as well as to civil liability for the breach of 
the terms and conditions of this license.

THIS SOFTWARE IS PROVIDED IN AN “AS IS” CONDITION. NO WARRANTIES,
WHETHER EXPRESS, IMPLIED OR STATUTORY, INCLUDING, BUT NOT LIMITED
TO, IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE APPLY TO THIS SOFTWARE. THE COMPANY SHALL NOT,
IN ANY CIRCUMSTANCES, BE LIABLE FOR SPECIAL, INCIDENTAL OR
CONSEQUENTIAL DAMAGES, FOR ANY REASON WHATSOEVER.

*******************************************************************************/
//Write GPIB command to a specfific GPIB interface equipment
extern "C"  __declspec(dllimport) int Gwrite(int address, char* scpi);

//Write GPIB command in binary mode to a specfific GPIB interface equipment
extern "C"  __declspec(dllimport) int Gbwrite(int address,bool bmode, unsigned char* bdata,int writelength);

//Read data from a specific GPIB interface equipment - Read only 
extern "C"  __declspec(dllimport) char* Gread(int address);

//Read binary data (byte) or file from a specific GPIB interface equipment - Read only 
extern "C"  __declspec(dllimport) char* Gbread(int address);
//Data read length for binary data
extern "C"  __declspec(dllimport) int Gbreadlength(void);

//Send inquery command to a specific GPIB interface equipment and read data 
extern "C"  __declspec(dllimport) char* Gquery(int address, char *scpi);

//Find all the addresses of equipment connected on the GPIB bus 
extern "C"  __declspec(dllimport) int* Gfind(void);

//Read file from GPIB equipment and save the file in local PC at current foler
extern "C"  __declspec(dllimport) int Gfilesave(int address, bool mode, char* filename);
/*************************************************************************************
For detailed information, please refer to "UG01 User's Manual"