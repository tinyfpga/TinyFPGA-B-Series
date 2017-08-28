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
  inout pin16_sck,
  inout pin17_ss,
  inout pin18,
  inout pin19,
  inout pin20,
  inout pin21,
  inout pin22,
  inout pin23,
  inout pin24
);
  wire clk_48mhz;

  /*

  TODO: endpoint reset

   */

  ////////////////////////////////////////////////////////////////////////////////
  ////////////////////////////////////////////////////////////////////////////////
  ////////
  //////// generate 48 mhz clock
  ////////
  ////////////////////////////////////////////////////////////////////////////////
  ////////////////////////////////////////////////////////////////////////////////

  SB_PLL40_CORE usb_pll_inst (
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

  // Fin=16, Fout=48;
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


  ////////////////////////////////////////////////////////////////////////////////
  ////////////////////////////////////////////////////////////////////////////////
  ////////
  //////// usb engine
  ////////
  ////////////////////////////////////////////////////////////////////////////////
  ////////////////////////////////////////////////////////////////////////////////

  wire [6:0] dev_addr;
  wire [7:0] out_ep_data;

  wire ctrl_out_ep_req;
  wire ctrl_out_ep_grant;
  wire ctrl_out_ep_data_avail;
  wire ctrl_out_ep_setup;
  wire ctrl_out_ep_data_get;
  wire ctrl_out_ep_stall;
  wire ctrl_out_ep_acked;

  wire ctrl_in_ep_req;
  wire ctrl_in_ep_grant;
  wire ctrl_in_ep_data_free;
  wire ctrl_in_ep_data_put;
  wire [7:0] ctrl_in_ep_data;
  wire ctrl_in_ep_data_done;
  wire ctrl_in_ep_stall;
  wire ctrl_in_ep_acked;


  wire serial_out_ep_req;
  wire serial_out_ep_grant;
  wire serial_out_ep_data_avail;
  wire serial_out_ep_setup;
  wire serial_out_ep_data_get;
  wire serial_out_ep_stall;
  wire serial_out_ep_acked;

  wire serial_in_ep_req;
  wire serial_in_ep_grant;
  wire serial_in_ep_data_free;
  wire serial_in_ep_data_put;
  wire [7:0] serial_in_ep_data;
  wire serial_in_ep_data_done;
  wire serial_in_ep_stall;
  wire serial_in_ep_acked;

  wire sof_valid;
  wire [10:0] frame_index;

  reg [31:0] host_presence_timer;
  reg host_presence_timeout;

  wire boot_to_user_design;

  wire [31:0] output_pin_values;
  wire [31:0] output_pin_enables;

  wire reset;

  SB_WARMBOOT warmboot_inst (
    .S1(0),
    .S0(1),
    .BOOT(host_presence_timeout || boot_to_user_design)
  );

  usb_serial_ctrl_ep ctrl_ep_inst (
    .clk(clk_48mhz),
    .reset(reset),
    .dev_addr(dev_addr),

    // out endpoint interface 
    .out_ep_req(ctrl_out_ep_req),
    .out_ep_grant(ctrl_out_ep_grant),
    .out_ep_data_avail(ctrl_out_ep_data_avail),
    .out_ep_setup(ctrl_out_ep_setup),
    .out_ep_data_get(ctrl_out_ep_data_get),
    .out_ep_data(out_ep_data),
    .out_ep_stall(ctrl_out_ep_stall),
    .out_ep_acked(ctrl_out_ep_acked),


    // in endpoint interface 
    .in_ep_req(ctrl_in_ep_req),
    .in_ep_grant(ctrl_in_ep_grant),
    .in_ep_data_free(ctrl_in_ep_data_free),
    .in_ep_data_put(ctrl_in_ep_data_put),
    .in_ep_data(ctrl_in_ep_data),
    .in_ep_data_done(ctrl_in_ep_data_done),
    .in_ep_stall(ctrl_in_ep_stall),
    .in_ep_acked(ctrl_in_ep_acked)
  );

  usb_spi_bridge_ep usb_spi_bridge_ep_inst (
    .clk(clk_48mhz),
    .reset(reset),

    // out endpoint interface 
    .out_ep_req(serial_out_ep_req),
    .out_ep_grant(serial_out_ep_grant),
    .out_ep_data_avail(serial_out_ep_data_avail),
    .out_ep_setup(serial_out_ep_setup),
    .out_ep_data_get(serial_out_ep_data_get),
    .out_ep_data(out_ep_data),
    .out_ep_stall(serial_out_ep_stall),
    .out_ep_acked(serial_out_ep_acked),

    // in endpoint interface 
    .in_ep_req(serial_in_ep_req),
    .in_ep_grant(serial_in_ep_grant),
    .in_ep_data_free(serial_in_ep_data_free),
    .in_ep_data_put(serial_in_ep_data_put),
    .in_ep_data(serial_in_ep_data),
    .in_ep_data_done(serial_in_ep_data_done),
    .in_ep_stall(serial_in_ep_stall),
    .in_ep_acked(serial_in_ep_acked),

    // spi interface 
    .spi_cs_b(pin17_ss),
    .spi_sck(pin16_sck),
    .spi_mosi(pin14_sdo),
    .spi_miso(pin15_sdi),

    // warm boot interface
    .boot_to_user_design(boot_to_user_design),

    // output pin interface for test
    .output_pin_values(output_pin_values),
    .output_pin_enables(output_pin_enables)
  );

  wire nak_in_ep_grant;
  wire nak_in_ep_data_free;
  wire nak_in_ep_acked;

  usb_fs_pe #(
    .NUM_OUT_EPS(2),
    .NUM_IN_EPS(3)
  ) usb_fs_pe_inst (
    .clk(clk_48mhz),
    .reset(reset),

    .dp(pin1_usb_dp),
    .dn(pin2_usb_dn),

    .dev_addr(dev_addr),

    // out endpoint interfaces 
    .out_ep_req({serial_out_ep_req, ctrl_out_ep_req}),
    .out_ep_grant({serial_out_ep_grant, ctrl_out_ep_grant}),
    .out_ep_data_avail({serial_out_ep_data_avail, ctrl_out_ep_data_avail}),
    .out_ep_setup({serial_out_ep_setup, ctrl_out_ep_setup}),
    .out_ep_data_get({serial_out_ep_data_get, ctrl_out_ep_data_get}),
    .out_ep_data(out_ep_data),
    .out_ep_stall({serial_out_ep_stall, ctrl_out_ep_stall}),
    .out_ep_acked({serial_out_ep_acked, ctrl_out_ep_acked}),

    // in endpoint interfaces 
    .in_ep_req({1'b0, serial_in_ep_req, ctrl_in_ep_req}),
    .in_ep_grant({nak_in_ep_grant, serial_in_ep_grant, ctrl_in_ep_grant}),
    .in_ep_data_free({nak_in_ep_data_free, serial_in_ep_data_free, ctrl_in_ep_data_free}),
    .in_ep_data_put({1'b0, serial_in_ep_data_put, ctrl_in_ep_data_put}),
    .in_ep_data({8'b0, serial_in_ep_data[7:0], ctrl_in_ep_data[7:0]}),
    .in_ep_data_done({1'b0, serial_in_ep_data_done, ctrl_in_ep_data_done}),
    .in_ep_stall({1'b0, serial_in_ep_stall, ctrl_in_ep_stall}),
    .in_ep_acked({nak_in_ep_acked, serial_in_ep_acked, ctrl_in_ep_acked}),

    // sof interface
    .sof_valid(sof_valid),
    .frame_index(frame_index)
  );

  

  ////////////////////////////////////////////////////////////////////////////////
  // host presence detection
  ////////////////////////////////////////////////////////////////////////////////

  always @(posedge clk_48mhz) begin
    if (sof_valid) begin
      host_presence_timer <= 0;
      host_presence_timeout <= 0;
    end else begin
      host_presence_timer <= host_presence_timer + 1;
    end

    if (host_presence_timer > 48000000) begin
      host_presence_timeout <= 1;
    end
  end

  assign pin4 =  output_pin_enables[4]  ? output_pin_values[4]  : 1'bz;
  assign pin5 =  output_pin_enables[5]  ? output_pin_values[5]  : 1'bz;
  assign pin6 =  output_pin_enables[6]  ? output_pin_values[6]  : 1'bz;
  assign pin7 =  output_pin_enables[7]  ? output_pin_values[7]  : 1'bz;
  assign pin8 =  output_pin_enables[8]  ? output_pin_values[8]  : 1'bz;
  assign pin9 =  output_pin_enables[9]  ? output_pin_values[9]  : 1'bz;
  assign pin10 = output_pin_enables[10] ? output_pin_values[10] : 1'bz;
  assign pin11 = output_pin_enables[11] ? output_pin_values[11] : 1'bz;
  assign pin12 = output_pin_enables[12] ? output_pin_values[12] : 1'bz;
  assign pin13 = output_pin_enables[13] ? output_pin_values[13] : 1'bz;

  assign pin18 = output_pin_enables[18] ? output_pin_values[18] : 1'bz;
  assign pin19 = output_pin_enables[19] ? output_pin_values[19] : 1'bz;
  assign pin20 = output_pin_enables[20] ? output_pin_values[20] : 1'bz;
  assign pin21 = output_pin_enables[21] ? output_pin_values[21] : 1'bz;
  assign pin22 = output_pin_enables[22] ? output_pin_values[22] : 1'bz;
  assign pin23 = output_pin_enables[23] ? output_pin_values[23] : 1'bz;
  assign pin24 = output_pin_enables[24] ? output_pin_values[24] : 1'bz;

endmodule
