// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VDevelopmentBoard.h for the primary calling header

#include "VDevelopmentBoard__pch.h"
#include "VDevelopmentBoard__Syms.h"
#include "VDevelopmentBoard___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void VDevelopmentBoard___024root___dump_triggers__act(VDevelopmentBoard___024root* vlSelf);
#endif  // VL_DEBUG

void VDevelopmentBoard___024root___eval_triggers__act(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval_triggers__act\n"); );
    // Body
    vlSelf->__VactTriggered.set(0U, (((IData)(vlSelf->clk) 
                                      & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__clk__0))) 
                                     | ((~ (IData)(vlSelf->reset)) 
                                        & (IData)(vlSelf->__Vtrigprevexpr___TOP__reset__0))));
    vlSelf->__VactTriggered.set(1U, (((IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk) 
                                      & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk__0))) 
                                     | ((~ (IData)(vlSelf->reset)) 
                                        & (IData)(vlSelf->__Vtrigprevexpr___TOP__reset__0))));
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = vlSelf->clk;
    vlSelf->__Vtrigprevexpr___TOP__reset__0 = vlSelf->reset;
    vlSelf->__Vtrigprevexpr___TOP__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk__0 
        = vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk;
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        VDevelopmentBoard___024root___dump_triggers__act(vlSelf);
    }
#endif
}
