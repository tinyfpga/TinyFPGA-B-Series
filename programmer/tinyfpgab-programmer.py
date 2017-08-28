#!python2.7
import sys
import os
script_path = os.path.dirname(os.path.realpath(__file__))
local_packages_path = os.path.join(script_path, 'pkgs')
sys.path.insert(0, local_packages_path)

import serial
import array
import time
from intelhex import IntelHex
from Tkinter import *
from ttk import *
import tkFileDialog
import threading
import os
import os.path
import traceback
from serial.tools.list_ports import comports

from tinyfpgab import h, TinyFPGAB


################################################################################
################################################################################
##
## TinyFPGA B-Series Programmer GUI
##
################################################################################
################################################################################

r = Tk()
r.title("TinyFPGA B-Series Programmer")
r.resizable(width=False, height=False)

program_in_progress = False
program_failure = False

boot_fpga_b = Button(r, text="Exit Bootloader")
program_fpga_b = Button(r, text="Program FPGA")
program_progress_pb = Progressbar(r, orient="horizontal", length=400, mode="determinate")

program_status_sv = StringVar(r)

serial_port_ready = False;
bitstream_file_ready = False;
file_mtime = 0

def update_button_state():
    if serial_port_ready and not program_in_progress:
        boot_fpga_b.config(state=NORMAL)

        if bitstream_file_ready:
            program_fpga_b.config(state=NORMAL)
        else:
            program_fpga_b.config(state=DISABLED)

    else:
        boot_fpga_b.config(state=DISABLED)
        program_fpga_b.config(state=DISABLED)


########################################
## Select Serial Port
########################################

com_port_status_sv = StringVar(r)
com_port_status_l = Label(r, textvariable=com_port_status_sv)
com_port_status_l.grid(column=1, row=0, sticky=W+E, padx=10, pady=8)
com_port_sv = StringVar(r)
com_port_sv.set("")
select_port_om = OptionMenu(r, com_port_sv, ())
select_port_om.grid(column=0, row=0, sticky=W+E, padx=10, pady=8)

tinyfpga_ports = []
def update_serial_port_list_task():
    global tinyfpga_ports
    global program_in_progress
    
    if not program_in_progress:
        new_tinyfpga_ports = [i[0] for i in comports() if ("0000:0000" in i[2]) or ("1209:2100" in i[2])]

        if new_tinyfpga_ports != tinyfpga_ports:
            if com_port_sv.get() == "" and len(new_tinyfpga_ports) > 0:
                com_port_sv.set(new_tinyfpga_ports[0])
            menu = select_port_om["menu"]
            menu.delete(0, "end")
            for string in new_tinyfpga_ports:
                menu.add_command(
                    label=string, 
                    command=lambda value=string: com_port_sv.set(value))
            tinyfpga_ports = new_tinyfpga_ports

    r.after(1000, update_serial_port_list_task)

update_serial_port_list_task()

def check_port_status_task():
    global serial_port_ready
    if not program_in_progress:
        try:
            with serial.Serial(com_port_sv.get(), 10000000, timeout=1, writeTimeout=0.1) as ser:
                fpga = TinyFPGAB(ser)

                fpga.wake()
                devid = fpga.read_id()

                expected_devid = [0x1F, 0x84, 0x01]
                if devid == expected_devid:
                    com_port_status_sv.set("Bootloader active. Ready to program.")
                    serial_port_ready = True;
                    update_button_state()
                else:
                    com_port_status_sv.set("Unable to communicate with TinyFPGA. Reconnect and reset TinyFPGA before programming.")
                    serial_port_ready = False;
                    update_button_state()

        except serial.SerialTimeoutException:
            com_port_status_sv.set("Hmm...try pressing the reset button on TinyFPGA again.")
            serial_port_ready = False;
            update_button_state()

        except:
            com_port_status_sv.set("Bootloader not active. Press reset button on TinyFPGA before programming.")
            serial_port_ready = False;
            update_button_state()
            
    r.after(50, check_port_status_task)

check_port_status_task()


########################################
## Select File
########################################

filename_sv = StringVar(r)

def select_bitstream_file_cmd():
    filename = tkFileDialog.askopenfilename(
        title = "Select file", 
        filetypes = [
            ('FPGA Bitstream Files', '.hex'), 
            ('all files', '.*')
        ]
    )

    filename_sv.set(filename)

select_file_b = Button(r, text="Select File", command=select_bitstream_file_cmd)
select_file_b.grid(column=0, row=1, sticky=W+E, padx=10, pady=8)
filename_e = Entry(r)
filename_e.config(textvariable=filename_sv)
filename_e.grid(column=1, row=1, sticky=W+E, padx=10, pady=8)

def check_bitstream_file_status_cmd(): 
    global bitstream_file_ready
    global file_mtime

    if os.path.isfile(filename_sv.get()):
        new_file_mtime = os.stat(filename_sv.get()).st_mtime

        bitstream_file_ready = True
        update_button_state()

        if new_file_mtime > file_mtime:
            program_status_sv.set("Bitstream file updated.")
        
        file_mtime = new_file_mtime

    else:
        if bitstream_file_ready:
            program_status_sv.set("Bitstream file no longer exists.")

        bitstream_file_ready = False
        update_button_state()

def check_bitstream_file_status_task():
    check_bitstream_file_status_cmd()
    r.after(1000, check_bitstream_file_status_task)

check_bitstream_file_status_task()

def check_bitstream_file_status_cb(*args):
    global file_mtime
    file_mtime = 0
    check_bitstream_file_status_cmd()

filename_sv.trace("w", check_bitstream_file_status_cb)



########################################
## Program FPGA
########################################

program_status_l = Label(r, textvariable=program_status_sv)
program_status_l.grid(column=1, row=3, sticky=W+E, padx=10, pady=8)

program_progress_pb.grid(column=1, row=2, sticky=W+E, padx=10, pady=8)

def program_fpga_thread():
    global program_in_progress
    global program_failure
    program_failure = False

    try:
        
        with serial.Serial(com_port_sv.get(), 10000000, timeout=1, writeTimeout=1) as ser:
            global current_progress
            global max_progress
            current_progress = 0

            def progress(v): 
                if isinstance(v, int) or isinstance(v, long):
                    global current_progress
                    current_progress += v
                elif isinstance(v, str):
                    program_status_sv.set(v)

            fpga = TinyFPGAB(ser, progress)

            (addr, bitstream) = fpga.slurp(filename_sv.get())

            max_progress = len(bitstream) * 3 

            try:
                fpga.program_bitstream(addr, bitstream)
            except:
                program_failure = True

        program_in_progress = False
    except:
        program_failure = True

current_progress = 0
max_progress = 0

def update_progress_task():
    global current_progress
    global max_progress
    program_progress_pb["value"] = current_progress
    program_progress_pb["maximum"] = max_progress
    r.after(10, update_progress_task)

update_progress_task()

def program_fpga_cmd():
    global program_in_progress
    program_in_progress = True
    update_button_state()
    t = threading.Thread(target=program_fpga_thread)
    t.start()

program_fpga_b.configure(command=program_fpga_cmd)
program_fpga_b.grid(column=0, row=2, sticky=W+E, padx=10, pady=8)

def program_failure_task():
    global program_failure
    if program_failure:
        program_status_sv.set("Programming failed! Reset TinyFPGA and try again.")
        program_failure = False

    r.after(100, program_failure_task)

program_failure_task()


########################################
## Boot FPGA
########################################

def boot_cmd():
    with serial.Serial(com_port_sv.get(), 10000000, timeout=1, writeTimeout=0.1) as ser:
        try:
            TinyFPGAB(ser).boot()

        except serial.SerialTimeoutException:
            com_port_status_sv.set("Hmm...try pressing the reset button on TinyFPGA again.")

boot_fpga_b.configure(command=boot_cmd)
boot_fpga_b.grid(column=0, row=3, sticky=W+E, padx=10, pady=8)

# make sure we can't get resized too small
r.update()
r.minsize(r.winfo_width(), r.winfo_height())

# start the gui
r.mainloop()
