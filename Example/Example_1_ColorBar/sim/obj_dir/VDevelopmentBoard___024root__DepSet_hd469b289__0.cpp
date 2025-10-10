// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VDevelopmentBoard.h for the primary calling header

#include "VDevelopmentBoard__pch.h"
#include "VDevelopmentBoard___024root.h"

void VDevelopmentBoard___024root___eval_act(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval_act\n"); );
}

VL_INLINE_OPT void VDevelopmentBoard___024root___nba_sequent__TOP__0(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___nba_sequent__TOP__0\n"); );
    // Body
    vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk 
        = ((IData)(vlSelf->reset) && (1U & (~ (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_clk))));
}

extern const VlUnpacked<SData/*15:0*/, 2048> VDevelopmentBoard__ConstPool__TABLE_h7e1c79c2_0;

VL_INLINE_OPT void VDevelopmentBoard___024root___nba_sequent__TOP__1(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___nba_sequent__TOP__1\n"); );
    // Init
    SData/*10:0*/ __Vtableidx1;
    __Vtableidx1 = 0;
    SData/*9:0*/ __Vdly__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h;
    __Vdly__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h = 0;
    // Body
    __Vdly__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h 
        = vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h;
    if (vlSelf->reset) {
        __Vdly__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h 
            = ((0x31fU == (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h))
                ? 0U : (0x3ffU & ((IData)(1U) + (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h))));
        vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v 
            = (((0x20cU == (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v)) 
                & (0x31fU == (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h)))
                ? 0U : (0x3ffU & ((0x31fU == (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h))
                                   ? ((IData)(1U) + (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v))
                                   : (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v))));
    } else {
        __Vdly__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h = 0U;
        vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v = 0U;
    }
    __Vtableidx1 = (((((0x8fU <= (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h)) 
                       & ((0x30fU > (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h)) 
                          & (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT____VdfgTmp_ha8b3968e__0)))
                       ? (0x3ffU & ((IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h) 
                                    - (IData)(0x8fU)))
                       : 0x3ffU) << 1U) | (IData)(vlSelf->reset));
    vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__pix_data 
        = VDevelopmentBoard__ConstPool__TABLE_h7e1c79c2_0
        [__Vtableidx1];
    vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h 
        = __Vdly__DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h;
    vlSelf->v_sync = (1U >= (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v));
    vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT____VdfgTmp_ha8b3968e__0 
        = ((0x23U <= (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v)) 
           & (0x203U > (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_v)));
    vlSelf->h_sync = (0x5fU >= (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h));
    vlSelf->rgb = (((0x90U <= (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h)) 
                    & ((0x310U > (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT__cnt_h)) 
                       & (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__vga_ctrl_inst__DOT____VdfgTmp_ha8b3968e__0)))
                    ? (IData)(vlSelf->DevelopmentBoard__DOT__ColorBar_inst__DOT__pix_data)
                    : 0U);
}

void VDevelopmentBoard___024root___eval_nba(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval_nba\n"); );
    // Body
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VDevelopmentBoard___024root___nba_sequent__TOP__0(vlSelf);
    }
    if ((2ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VDevelopmentBoard___024root___nba_sequent__TOP__1(vlSelf);
    }
}

void VDevelopmentBoard___024root___eval_triggers__act(VDevelopmentBoard___024root* vlSelf);

bool VDevelopmentBoard___024root___eval_phase__act(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval_phase__act\n"); );
    // Init
    VlTriggerVec<2> __VpreTriggered;
    CData/*0:0*/ __VactExecute;
    // Body
    VDevelopmentBoard___024root___eval_triggers__act(vlSelf);
    __VactExecute = vlSelf->__VactTriggered.any();
    if (__VactExecute) {
        __VpreTriggered.andNot(vlSelf->__VactTriggered, vlSelf->__VnbaTriggered);
        vlSelf->__VnbaTriggered.thisOr(vlSelf->__VactTriggered);
        VDevelopmentBoard___024root___eval_act(vlSelf);
    }
    return (__VactExecute);
}

bool VDevelopmentBoard___024root___eval_phase__nba(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval_phase__nba\n"); );
    // Init
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = vlSelf->__VnbaTriggered.any();
    if (__VnbaExecute) {
        VDevelopmentBoard___024root___eval_nba(vlSelf);
        vlSelf->__VnbaTriggered.clear();
    }
    return (__VnbaExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VDevelopmentBoard___024root___dump_triggers__nba(VDevelopmentBoard___024root* vlSelf);
#endif  // VL_DEBUG
#ifdef VL_DEBUG
VL_ATTR_COLD void VDevelopmentBoard___024root___dump_triggers__act(VDevelopmentBoard___024root* vlSelf);
#endif  // VL_DEBUG

void VDevelopmentBoard___024root___eval(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval\n"); );
    // Init
    IData/*31:0*/ __VnbaIterCount;
    CData/*0:0*/ __VnbaContinue;
    // Body
    __VnbaIterCount = 0U;
    __VnbaContinue = 1U;
    while (__VnbaContinue) {
        if (VL_UNLIKELY((0x64U < __VnbaIterCount))) {
#ifdef VL_DEBUG
            VDevelopmentBoard___024root___dump_triggers__nba(vlSelf);
#endif
            VL_FATAL_MT("DevelopmentBoard.v", 3, "", "NBA region did not converge.");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        __VnbaContinue = 0U;
        vlSelf->__VactIterCount = 0U;
        vlSelf->__VactContinue = 1U;
        while (vlSelf->__VactContinue) {
            if (VL_UNLIKELY((0x64U < vlSelf->__VactIterCount))) {
#ifdef VL_DEBUG
                VDevelopmentBoard___024root___dump_triggers__act(vlSelf);
#endif
                VL_FATAL_MT("DevelopmentBoard.v", 3, "", "Active region did not converge.");
            }
            vlSelf->__VactIterCount = ((IData)(1U) 
                                       + vlSelf->__VactIterCount);
            vlSelf->__VactContinue = 0U;
            if (VDevelopmentBoard___024root___eval_phase__act(vlSelf)) {
                vlSelf->__VactContinue = 1U;
            }
        }
        if (VDevelopmentBoard___024root___eval_phase__nba(vlSelf)) {
            __VnbaContinue = 1U;
        }
    }
}

#ifdef VL_DEBUG
void VDevelopmentBoard___024root___eval_debug_assertions(VDevelopmentBoard___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VDevelopmentBoard__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VDevelopmentBoard___024root___eval_debug_assertions\n"); );
    // Body
    if (VL_UNLIKELY((vlSelf->clk & 0xfeU))) {
        Verilated::overWidthError("clk");}
    if (VL_UNLIKELY((vlSelf->reset & 0xfeU))) {
        Verilated::overWidthError("reset");}
    if (VL_UNLIKELY((vlSelf->B2 & 0xfeU))) {
        Verilated::overWidthError("B2");}
    if (VL_UNLIKELY((vlSelf->B3 & 0xfeU))) {
        Verilated::overWidthError("B3");}
    if (VL_UNLIKELY((vlSelf->B4 & 0xfeU))) {
        Verilated::overWidthError("B4");}
    if (VL_UNLIKELY((vlSelf->B5 & 0xfeU))) {
        Verilated::overWidthError("B5");}
}
#endif  // VL_DEBUG
