module TinyFPGA_B (
  inout pin1_usb_dp,
  inout pin2_usb_dn,
  input pin3_clk_16mhz,
  inout pin4,
  inout pin5,
  inout pin6,
  inout pin7,
  inout pin8,
  inout pin9,
  inout pin10,
  inout pin11,
  inout pin12,
  inout pin13,
  inout pin14_sdo,
  inout pin15_sdi,
  output pin16_sck,
  inout pin17_ss,
  inout pin18,
  inout pin19,
  inout pin20,
  inout pin21,
  inout pin22,
  inout pin23,
  inout pin24
);
  // there are some decoupling caps just for the PLL on the board,
  // let's pipe the clock through the PLL so we can test both the
  // clock and PLL at once
  wire clk_48mhz;
  SB_PLL40_CORE pll_inst (
    .REFERENCECLK(pin3_clk_16mhz),
    .PLLOUTCORE(clk_48mhz),
    .PLLOUTGLOBAL(),
    .EXTFEEDBACK(),
    .DYNAMICDELAY(),
    .RESETB(1),
    .BYPASS(1'b0),
    .LATCHINPUTVALUE(),
    .LOCK(),
    .SDI(),
    .SDO(),
    .SCLK()
  );  
  // Fin=16, Fout=48
  defparam usb_pll_inst.DIVR = 4'b0000;
  defparam usb_pll_inst.DIVF = 7'b0101111;
  defparam usb_pll_inst.DIVQ = 3'b100;
  defparam usb_pll_inst.FILTER_RANGE = 3'b001;
  defparam usb_pll_inst.FEEDBACK_PATH = "SIMPLE";
  defparam usb_pll_inst.DELAY_ADJUSTMENT_MODE_FEEDBACK = "FIXED";
  defparam usb_pll_inst.FDA_FEEDBACK = 4'b0000;
  defparam usb_pll_inst.DELAY_ADJUSTMENT_MODE_RELATIVE = "FIXED";
  defparam usb_pll_inst.FDA_RELATIVE = 4'b0000;
  defparam usb_pll_inst.SHIFTREG_DIV_MODE = 2'b00;
  defparam usb_pll_inst.PLLOUT_SELECT = "GENCLK";
  defparam usb_pll_inst.ENABLE_ICEGATE = 1'b0;
  // divide the clock down to ensure two things:
  // 1. clock is connected to FPGA
  // 2. output clock is measurable by test-jig
  reg [19:0] clock_divider;
  reg slow_clock;
  assign pin16_sck = slow_clock;
  always @(posedge clk_48mhz) begin 
    if (clock_divider < 1000000) begin
      clock_divider <= clock_divider + 1;
    end else begin
      slow_clock <= ~slow_clock;
      clock_divider <= 0;
    end
  end


  // pulling an input pin low will drive the corresponding
  // output pin low as well.  this is a simple way for the
  // test jig to test all the IOs for opens and shorts
  assign pin11 = pin17_ss ? 0 : 1'bz;
  assign pin12 = pin1_usb_dp ? 0 : 1'bz;
  assign pin13 = pin2_usb_dn ? 0 : 1'bz;
  assign pin18 = pin4 ? 0 : 1'bz;
  assign pin19 = pin5 ? 0 : 1'bz;
  assign pin20 = pin6 ? 0 : 1'bz;
  assign pin21 = pin7 ? 0 : 1'bz;
  assign pin22 = pin8 ? 0 : 1'bz;
  assign pin23 = pin9 ? 0 : 1'bz;
  assign pin24 = pin10 ? 0 : 1'bz;
  assign pin14_sdo = pin15_sdi ? 0 : 1'bz;
endmodule
