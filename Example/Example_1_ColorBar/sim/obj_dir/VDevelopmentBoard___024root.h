// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See VDevelopmentBoard.h for the primary calling header

#ifndef VERILATED_VDEVELOPMENTBOARD___024ROOT_H_
#define VERILATED_VDEVELOPMENTBOARD___024ROOT_H_  // guard

#include "verilated.h"


class VDevelopmentBoard__Syms;

class alignas(VL_CACHE_LINE_BYTES) VDevelopmentBoard___024root final : public VerilatedModule {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(reset,0,0);
    CData/*0:0*/ DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk;
    VL_IN8(B2,0,0);
    VL_IN8(B3,0,0);
    VL_IN8(B4,0,0);
    VL_IN8(B5,0,0);
    VL_OUT8(h_sync,0,0);
    VL_OUT8(v_sync,0,0);
    VL_OUT8(led1,0,0);
    VL_OUT8(led2,0,0);
    VL_OUT8(led3,0,0);
    VL_OUT8(led4,0,0);
    VL_OUT8(led5,0,0);
    CData/*0:0*/ DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT____VdfgTmp_ha8b3968e__0;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __Vtrigprevexpr___TOP__clk__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__reset__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk__0;
    CData/*0:0*/ __VactContinue;
    VL_OUT16(rgb,15,0);
    SData/*15:0*/ DevelopmentBoard__DOT__ColorBar_inst__DOT__pix_data;
    SData/*9:0*/ DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h;
    SData/*9:0*/ DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v;
    IData/*31:0*/ __VactIterCount;
    VlTriggerVec<1> __VstlTriggered;
    VlTriggerVec<2> __VactTriggered;
    VlTriggerVec<2> __VnbaTriggered;

    // INTERNAL VARIABLES
    VDevelopmentBoard__Syms* const vlSymsp;

    // CONSTRUCTORS
    VDevelopmentBoard___024root(VDevelopmentBoard__Syms* symsp, const char* v__name);
    ~VDevelopmentBoard___024root();
    VL_UNCOPYABLE(VDevelopmentBoard___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
