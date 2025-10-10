// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "VDevelopmentBoard__pch.h"

//============================================================
// Constructors

VDevelopmentBoard::VDevelopmentBoard(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new VDevelopmentBoard__Syms(contextp(), _vcname__, this)}
    , clk{vlSymsp->TOP.clk}
    , reset{vlSymsp->TOP.reset}
    , B2{vlSymsp->TOP.B2}
    , B3{vlSymsp->TOP.B3}
    , B4{vlSymsp->TOP.B4}
    , B5{vlSymsp->TOP.B5}
    , h_sync{vlSymsp->TOP.h_sync}
    , v_sync{vlSymsp->TOP.v_sync}
    , led1{vlSymsp->TOP.led1}
    , led2{vlSymsp->TOP.led2}
    , led3{vlSymsp->TOP.led3}
    , led4{vlSymsp->TOP.led4}
    , led5{vlSymsp->TOP.led5}
    , rgb{vlSymsp->TOP.rgb}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
}

VDevelopmentBoard::VDevelopmentBoard(const char* _vcname__)
    : VDevelopmentBoard(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

VDevelopmentBoard::~VDevelopmentBoard() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void VDevelopmentBoard___024root___eval_debug_assertions(VDevelopmentBoard___024root* vlSelf);
#endif  // VL_DEBUG
void VDevelopmentBoard___024root___eval_static(VDevelopmentBoard___024root* vlSelf);
void VDevelopmentBoard___024root___eval_initial(VDevelopmentBoard___024root* vlSelf);
void VDevelopmentBoard___024root___eval_settle(VDevelopmentBoard___024root* vlSelf);
void VDevelopmentBoard___024root___eval(VDevelopmentBoard___024root* vlSelf);

void VDevelopmentBoard::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate VDevelopmentBoard::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    VDevelopmentBoard___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        vlSymsp->__Vm_didInit = true;
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        VDevelopmentBoard___024root___eval_static(&(vlSymsp->TOP));
        VDevelopmentBoard___024root___eval_initial(&(vlSymsp->TOP));
        VDevelopmentBoard___024root___eval_settle(&(vlSymsp->TOP));
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    VDevelopmentBoard___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

//============================================================
// Events and timing
bool VDevelopmentBoard::eventsPending() { return false; }

uint64_t VDevelopmentBoard::nextTimeSlot() {
    VL_FATAL_MT(__FILE__, __LINE__, "", "%Error: No delays in the design");
    return 0;
}

//============================================================
// Utilities

const char* VDevelopmentBoard::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void VDevelopmentBoard___024root___eval_final(VDevelopmentBoard___024root* vlSelf);

VL_ATTR_COLD void VDevelopmentBoard::final() {
    VDevelopmentBoard___024root___eval_final(&(vlSymsp->TOP));
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* VDevelopmentBoard::hierName() const { return vlSymsp->name(); }
const char* VDevelopmentBoard::modelName() const { return "VDevelopmentBoard"; }
unsigned VDevelopmentBoard::threads() const { return 1; }
void VDevelopmentBoard::prepareClone() const { contextp()->prepareClone(); }
void VDevelopmentBoard::atClone() const {
    contextp()->threadPoolpOnClone();
}

//============================================================
// Trace configuration

VL_ATTR_COLD void VDevelopmentBoard::trace(VerilatedVcdC* tfp, int levels, int options) {
    vl_fatal(__FILE__, __LINE__, __FILE__,"'VDevelopmentBoard::trace()' called on model that was Verilated without --trace option");
}
