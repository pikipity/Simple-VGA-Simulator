// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VDEVELOPMENTBOARD__SYMS_H_
#define VERILATED_VDEVELOPMENTBOARD__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "VDevelopmentBoard.h"

// INCLUDE MODULE CLASSES
#include "VDevelopmentBoard___024root.h"

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)VDevelopmentBoard__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    VDevelopmentBoard* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    VDevelopmentBoard___024root    TOP;

    // CONSTRUCTORS
    VDevelopmentBoard__Syms(VerilatedContext* contextp, const char* namep, VDevelopmentBoard* modelp);
    ~VDevelopmentBoard__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
