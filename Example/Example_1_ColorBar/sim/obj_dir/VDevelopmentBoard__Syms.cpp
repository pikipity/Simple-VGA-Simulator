// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table implementation internals

#include "VDevelopmentBoard__pch.h"
#include "VDevelopmentBoard.h"
#include "VDevelopmentBoard___024root.h"

// FUNCTIONS
VDevelopmentBoard__Syms::~VDevelopmentBoard__Syms()
{
}

VDevelopmentBoard__Syms::VDevelopmentBoard__Syms(VerilatedContext* contextp, const char* namep, VDevelopmentBoard* modelp)
    : VerilatedSyms{contextp}
    // Setup internal state of the Syms class
    , __Vm_modelp{modelp}
    // Setup module instances
    , TOP{this, namep}
{
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-9);
    _vm_contextp__->timeprecision(-9);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
}
