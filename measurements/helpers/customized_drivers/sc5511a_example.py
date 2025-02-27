# READ THE FIRST PART OF THE README.TXT FILE BEFORE RUNNING
# Thus far, this code can only support one device

import threading
import time

# calling the sc5511a lib of functions and definitions
import sc5511a
from sc5511a import *

error_dict = {
    "0": "SUCCESS",
    "-1": "USBDEVICEERROR",
    "-2": "USBTRANSFERERROR",
    "-3": "INPUTNULL",
    "-4": "COMMERROR",
    "-5": "INPUTNOTALLOC",
    "-6": "EEPROMOUTBOUNDS",
    "-7": "INVALIDARGUMENT",
    "-8": "INPUTOUTOFRANGE",
    "-9": "NOREFWHENLOCK",
    "-10": "NORESOURCEFOUND",
    "-11": "INVALIDCOMMAND",
}


def _error_handler(msg: int) -> None:
    """Display error when setting the device fail

    Args:
        msg(int): error key, see error_dict dict.
    Raises:
        BaseException
    """

    if msg != 0:
        raise BaseException(
            "Couldn't set the device due to {}.".format(error_dict[str(msg)])
        )
    else:
        pass


def device_temp():
    # returns the current device temperature in Farenheit
    error_code, device_temp = SC1.get_temperature()
    _error_handler(error_code)
    print(device_temp)
    return error_code, device_temp


def display_pll_status():
    # prints all elements of the PLL status structure
    error_code, PLL = SC1.get_pll_status()
    _error_handler(error_code)
    print(PLL)
    return 0


def get_sum_pll_ld():
    # prints the current state of the sum phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["sum_pll_ld"] == 0:
        print("The Main PLL loop is unlocked.")
    if PLL["sum_pll_ld"] == 1:
        print("The Main PLL loop is locked.")
    _error_handler(error_code)

    return PLL["sum_pll_ld"]


def get_crs_pll_ld():
    # prints the current state of the coarse phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["crs_pll_ld"] == 0:
        print("The Coarse Offset PLL loop is unlocked.")
    if PLL["crs_pll_ld"] == 1:
        print("The Coarse Offset PLL loop is locked.")
    _error_handler(error_code)

    return PLL["crs_pll_ld"]


def get_fine_pll_ld():
    # prints the current state of the fine phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["fine_pll_ld"] == 0:
        print("The DDS tuned Fine PLL loop is unlocked.")
    if PLL["fine_pll_ld"] == 1:
        print("The DDS tuned Fine PLL loop is locked.")
    _error_handler(error_code)
    return PLL["fine_pll_ld"]


def get_crs_ref_pll_ld():
    # prints the current state of the coarse reference phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["crs_ref_pll_ld"] == 0:
        print("The Coarse Reference PLL loop is unlocked.")
    if PLL["crs_ref_pll_ld"] == 1:
        print("The Coarse Reference PLL loop is locked.")
    _error_handler(error_code)
    return PLL["crs_ref_pll_ld"]


def get_crs_aux_pll_ld():
    # prints the current state of the coarse auxiliary phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["crs_aux_pll_ld"] == 0:
        print("The Auxiliary Coarse PLL loop is unlocked.")
    if PLL["crs_aux_pll_ld"] == 1:
        print("The Auxiliary Coarse PLL loop is locked.")
    _error_handler(error_code)
    return PLL["crs_aux_pll_ld"]


def get_ref_100_pll_ld():
    # prints the current state of the reference 100 phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["ref_100_pll_ld"] == 0:
        print("The 100 MHz VCXO PLL loop is unlocked.")
    if PLL["ref_100_pll_ld"] == 1:
        print("The 100 MHz VCXO PLL loop is locked.")
    _error_handler(error_code)
    return PLL["ref_100_pll_ld"]


def get_ref_10_pll_ld():
    # prints the current state of the reference 10 phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["ref_10_pll_ld"] == 0:
        print("The 10 MHz VCXO PLL loop is unlocked.")
    if PLL["ref_10_pll_ld"] == 1:
        print("The 10 MHz VCXO PLL loop is locked.")
    _error_handler(error_code)
    return PLL["ref_10_pll_ld"]


def get_rf2_pll_ld():
    # prints the current state of the RF2 phase lock loop
    error_code, PLL = SC1.get_pll_status()
    if PLL["rf2_pll_ld"] == 0:
        print("The RF2 PLL loop is unlocked.")
    if PLL["rf2_pll_ld"] == 1:
        print("The RF2 PLL loop is locked.")
    _error_handler(error_code)
    return PLL["rf2_pll_ld"]


def display_list_mode():
    # prints all current list mode parameter statuses
    error_code, LIST = SC1.get_list_mode()
    print(LIST)
    _error_handler(error_code)
    return 0


def get_sss_mode():
    # prints the current sss mode
    error_code, LIST = SC1.get_list_mode()
    if LIST["sweep_dir"] == 0:
        print("Sweeping from start/beginning to stop/end.")
    if LIST["sweep_dir"] == 1:
        print("Sweeping from stop/end to start/beginning.")
    _error_handler(error_code)
    return LIST["sweep_dir"]


def get_tri_waveform():
    # prints what shape the waveform is currently taking
    error_code, LIST = SC1.get_list_mode()
    if LIST["tri_waveform"] == 0:
        print("The waveform shape is sawtooth.")
    if LIST["tri_waveform"] == 1:
        print("The waveform shape is triangular")
    _error_handler(error_code)
    return LIST["tri_waveform"]


def get_hw_trigger():
    # prints the current state of the hardware trigger
    error_code, LIST = SC1.get_list_mode()
    if LIST["hw_trigger"] == 0:
        print("The soft trigger is expected.")
    if LIST["hw_trigger"] == 1:
        print("The hard trigger is expected.")
    _error_handler(error_code)
    return LIST["hw_trigger"]


def get_sweep_dir_status():
    # prints the direction the sweep will begin from
    error_code, LIST = SC1.get_list_mode()
    if LIST["sweep_dir"] == 0:
        print("Sweeping from start/beginning to stop/end.")
    if LIST["sweep_dir"] == 1:
        print("Sweeping from stop/end to start/beginning.")
    _error_handler(error_code)
    return LIST["sweep_dir"]


def get_hw_trigger():
    # prints if the soft trigger or the hard trigger is expected
    error_code, LIST = SC1.get_list_mode()
    if LIST["hw_trigger"] == 0:
        print("The soft trigger is expected")
    if LIST["hw_trigger"] == 1:
        print("The hard trigger is expected")
    _error_handler(error_code)


def get_step_on_hw_trigger():
    # prints if the hardware trigger will sweep through the list or step on every trigger
    error_code, LIST = SC1.get_list_mode()
    if LIST["step_on_hw_trig"] == 0:
        print("When triggered it will sweep through the list")
    if LIST["step_on_hw_trig"] == 1:
        print("When triggered it will step on every trigger (only for hard triggering)")
    _error_handler(error_code)
    return LIST["step_on_hw_trig"]


def get_return_to_start():
    # prints if the frequency will, or will not return to the start freq at the end of a cycle
    error_code, LIST = SC1.get_list_mode()
    if LIST["return_to_start"] == 0:
        print("Frequency will not return to the start frequency at the end of a cycle")
    if LIST["return_to_start"] == 1:
        print("Frequency will return to the start frequency at the end of cycle(s)")
    _error_handler(error_code)
    return LIST["return_to_start"]


def get_trig_out_enable():
    # prints if there is a trigger pulse at the trigger on pin
    error_code, LIST = SC1.get_list_mode()
    if LIST["trig_out_enable"] == 0:
        print("No trigger pulse at the trigger on pin")
    if LIST["trig_out_enable"] == 1:
        print("Trigger pulse at the trigger on pin")
    _error_handler(error_code)
    return LIST["trig_out_enable"]


def get_trig_out_on_cycle():
    # displays if there is a triggered output after a cycle????????????
    error_code, LIST = SC1.get_list_mode()
    if LIST["trig_out_on_cycle"] == 0:
        print("There is no trigger output after a cycle")
    if LIST["trig_out_on_cycle"] == 1:
        print("There is a trigger output after a cycle")
    return LIST["trig_out_on_cycle"]


def display_operate_status():
    # prints the current parameters of each operate status
    error_code, OPERATE = SC1.get_operate_status()
    print(OPERATE)
    _error_handler(error_code)
    return 0


def get_rf1_lock_mode():
    # prints if the synthesizer is using the harmonic or fracN circuit
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["rf1_lock_mode"] == 0:
        print("The synthesizer is using the harmonic circuit.")
    if OPERATE["rf1_lock_mode"] == 1:
        print("The synthesizer is using the fracN circuit.")
    _error_handler(error_code)
    return OPERATE["rf1_lock_mode"]


def get_rf1_loop_gain():
    # prints if the loop gain of the sum PLL is normal or low
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["rf1_loop_gain"] == 0:
        print("The loop gain of the Sum PLL is normal.")
    if OPERATE["rf1_loop_gain"] == 1:
        print("The loop gain of the Sum PLL is low.")
    _error_handler(error_code)
    return OPERATE["rf1_loop_gain"]


def get_device_access():
    # prints if the device has been accessed or not
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["device_access"] == 0:
        print("The device has not been accessed")
    if OPERATE["device_access"] == 1:
        print("The device has been accessed")
    _error_handler(error_code)
    return OPERATE["device_access"]


def get_rf1_device_standby():
    # prints if the RF channel 1 is on standby or not
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["rf1_standby"] == 0:
        print("Channel 1 is on standby")
    if OPERATE["rf1_standby"] == 1:
        print("Channel 1 is not on standby")
    _error_handler(error_code)
    return OPERATE["rf1_standby"]


def get_rf2_device_standby():
    # prints if the RF channel 2 is on standby or not
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["rf2_standby"] == 0:
        print("Channel 2 is not on standby")
    if OPERATE["rf2_standby"] == 1:
        print("Channel 2 is on standby")
    _error_handler(error_code)
    return OPERATE["rf2_standby"]


def get_auto_pwr_status():
    # prints if there will be a power adjustment when the frequency is changed
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["auto_pwr_disable"] == 0:
        print("No power adjustment when the frequency is changed")
    if OPERATE["auto_pwr_disable"] == 1:
        print("Power adjustment when the frequency is changed")
    _error_handler(error_code)
    return OPERATE["auto_pwr_disable"]


def get_rf1_out_enable():
    # prints if the RF output is disabled or enabled
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["rf1_out_enable"] == 0:
        print("RF output is disabled")
    if OPERATE["rf1_out_enable"] == 1:
        print("RF output is enabled")
    _error_handler(error_code)
    return OPERATE["rf1_out_enable"]


def get_ext_ref_lock():
    # prints whether or not an external reference is detected
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["ext_ref_detect"] == 0:
        print("There is no external reference detected")
    if OPERATE["ext_ref_detect"] == 1:
        print("An external reference has been detected")
    _error_handler(error_code)
    return OPERATE["ext_ref_detect"]


def get_ref_out_select():
    # prints if the 10 MHz reference ouput is selected or if the 100 MHz reference output is selected
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["ref_out_select"] == 0:
        print("The 10 MHz reference output is selected")
    if OPERATE["ref_out_select"] == 1:
        print("The 100 MHz reference output is selected")
    _error_handler(error_code)
    return OPERATE["ref_out_select"]


def get_list_mode_running():
    # prints if the list or sweep mode is configured
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["list_mode_running"] == 0:
        print("Sweep mode is configured")
    if OPERATE["list_mode_running"] == 1:
        print("List mode is configured")
    _error_handler(error_code)
    return OPERATE["list_mode_running"]


def get_rf1_mode():
    # prints if the RF1 mode is in a fixed tone state or if in a list/sweep mode
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["rf1_mode"] == 0:
        print("The channel 1 RF mode is in a fixed tone state")
    if OPERATE["rf1_mode"] == 1:
        print("The channel 1 RF mode is in a list/sweep mode state")
    _error_handler(error_code)
    return OPERATE["rf1_mode"]


def get_over_temp_status():
    # prints The current parameters of the operate status
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["over_temp"] == 0:
        print("The device is at an ok temperature")
    if OPERATE["over_temp"] == 1:
        print("The device is overheating")
    _error_handler(error_code)
    return OPERATE["over_temp"]


def get_harmonic_ss_status():
    # returns the curent spur suppression state, whethery it's 'yes' or 'no'
    error_code, OPERATE = SC1.get_operate_status()
    if OPERATE["harmonic_ss"] == 0:
        print("The harmonic spur suppression state is off")
    if OPERATE["harmonic_ss"] == 1:
        print("The harmonic spur suppression state is on")
    _error_handler(error_code)
    return OPERATE["harmonic_ss"]


def display_rf_parameters():
    # prints the current RF parameter values
    error_code, RF = SC1.get_rf_parameters()
    print(RF)
    _error_handler(error_code)
    return 0


def get_rf1_frequency():
    # prints the current RF1 frequency
    error_code, RF = SC1.get_rf_parameters()
    frequency1_status = RF["rf1_freq"]
    print("The frequency is : {:.2f}".format(frequency1_status))
    return frequency1_status


def get_rf2_frequency():
    # prints the current RF2 frequency
    error_code, RF = SC1.get_rf_parameters()
    frequency2_status = RF["rf2_freq"]
    print("The frequency is : {:.2f}".format(frequency2_status))
    return frequency2_status


def get_sweep_start_freq():
    # prints the sweep start freq value
    error_code, RF = SC1.get_rf_parameters()
    sweep_start_freq_status = RF["sweep_start_freq"]
    print("The sweep start frequency is : {:.2f}".format(sweep_start_freq_status))
    _error_handler(error_code)
    return sweep_start_freq_status


def get_sweep_stop_freq():
    # prints the sweep stop freq value
    error_code, RF = SC1.get_rf_parameters()
    sweep_stop_freq_status = RF["sweep_stop_freq"]
    print("The sweep stop frequency is : {:.2f}".format(sweep_stop_freq_status))
    _error_handler(error_code)
    return sweep_stop_freq_status


def get_sweep_step_freq():
    # prints the sweep step frq value
    error_code, RF = SC1.get_rf_parameters()
    sweep_step_freq_status = RF["sweep_step_freq"]
    print("The sweep step frequency is : {:.2f}".format(sweep_step_freq_status))
    _error_handler(error_code)
    return sweep_step_freq_status


def get_sweep_dwell_time():
    # prints the sweep dwell time value
    error_code, RF = SC1.get_rf_parameters()
    sweep_dwell_time_status = RF["sweep_dwell_time"]
    print("The sweep dwell time is : {:.2f}".format(sweep_dwell_time_status))
    _error_handler(error_code)
    return sweep_dwell_time_status


def get_sweep_cycles():
    # prints the sweep cycles status is
    error_code, RF = SC1.get_rf_parameters()
    sweep_cycles_status = RF["sweep_cycles"]
    print("The sweep cycle status is : {:.2f}".format(sweep_cycles_status))
    _error_handler(error_code)
    return sweep_cycles_status


def get_buffer_points():
    # prints what the buffer points status is
    error_code, RF = SC1.get_rf_parameters()
    buffer_points_status = RF["buffer_points"]
    print("The buffer points status is : {:.2f}".format(buffer_points_status))
    _error_handler(error_code)
    return buffer_points_status


def get_power_level():
    # prints the current power level
    error_code, RF = SC1.get_rf_parameters()
    power_level_status = RF["rf_level"]
    print("The power level is : {:.2f}".format(power_level_status))
    _error_handler(error_code)
    return power_level_status


def display_clock_config():
    # This function works only for devices with firmware >= ver3.6 and hardware > ver16.0
    error_code, CLOCK = SC1.get_clock_config()
    print(CLOCK)
    _error_handler(error_code)
    return CLOCK


def get_ext_ref_lock_enable():
    # This function works only for devices with firmware >= ver3.6 and hardware > ver16.0
    error_code, ext_ref_lock = SC1.get_ext_ref_lock_enable()
    if ext_ref_lock == 1:
        print("The external reference lock is enabled.")
    else:
        print("The external reference lock is disabled.")
    print(ext_ref_lock)
    return 0


def get_ref_out_select():
    # This function works only for devices with firmware >= ver3.6 and hardware > ver16.0
    error_code, ref_out_select = SC1.get_ref_out_select()
    if ref_out_select == 1:
        print("The 10 MHz reference out is selected.")
    else:
        print("The 100 MHz reference out is selected.")
    print(ref_out_select)
    return 0


def get_pxi_clock_enable():
    # This function works only for devices with firmware >= ver3.6 and hardware > ver16.0
    error_code, pxi_clock_enable = SC1.get_pxi_clock_enable()
    if pxi_clock_enable == 1:
        print("The PXI clock is enabled.")
    else:
        print("The PXI clock is disabled.")
    print(pxi_clock_enable)
    return 0


def get_ext_direct_clock():
    # This function works only for devices with firmware >= ver3.6 and hardware > ver16.0
    error_code, ext_direct_clocking = SC1.get_ext_direct_clock()
    if ext_direct_clocking == 1:
        print("The direct 100 MHz clocking of the synthesizer has been enabled.")
    else:
        print("The direct 100 MHz clocking of the synthesizer is NOT enabled.")

    print(ext_direct_clocking)
    return 0


def get_ext_ref_freq():
    # This function works only for devices with firmware >= ver3.6 and hardware > ver16.0
    error_code, ext_ref_freq = SC1.get_ext_ref_freq()
    if ext_ref_freq == 1:
        print("The device will lock to an external reference")
    else:
        print("The device will not lock to an external reference")
    print(ext_ref_freq)
    return 0


def get_idn():
    # prints the device information
    error_code, IDN = SC1.get_idn()
    _error_handler(error_code)
    print(IDN)
    return IDN


def close_device():
    SC1._close()


def set_signal_phase(phase):
    # sets the signal phase for the device
    error_code, phase = SC1.set_signal_phase(phase)
    _error_handler(error_code)
    return phase


def set_standby(standby_state):
    # sets the standby state for the device
    error_code, standby = SC1.set_standby(standby_state)
    _error_handler(error_code)
    return standby


def set_output(output):
    # sets the output value for the device
    error_code, output_enable = SC1.set_output(output)
    _error_handler(error_code)
    return output_enable


def set_rf_mode(rf_mode):
    # sets the RF mode
    error_code, set_rf_mode = SC1.set_rf_mode(rf_mode)
    _error_handler(error_code)
    return set_rf_mode


def set_rf1_frequency(freq_set):
    # sets the RF channel 1 frequency for the device
    error_code, frequency = SC1.set_frequency(freq_set)
    _error_handler(error_code)
    return frequency


def set_rf2_frequency(freq2_set):
    # sets the RF channel 2 frequency for the device
    error_code, frequency2 = SC1.set_rf2_frequency(freq2_set)
    _error_handler(error_code)
    return frequency2


def set_synth_mode(disable_spur, low_loop, lock):
    # sets the synth mode for the device
    error_code, disable_spur_suppress, low_loop_gain, lock_mode = SC1.set_synth_mode(
        disable_spur, low_loop, lock
    )
    _error_handler(error_code)
    return disable_spur, low_loop, lock


def set_clock_reference_mode(ext_ref, direct_lock, lock_to_external, high_):
    # sets the clock reference mode for the device
    error_code, ref, direct_lock, high_, lock_to_external = SC1.set_clock_reference(
        ext_ref, direct_lock, lock_to_external, high_
    )
    _error_handler(error_code)
    return error_code, ref, direct_lock, high_, lock_to_external


def set_level(level):
    # sets the power level for the device
    error_code, power = SC1.set_level(level)
    _error_handler(error_code)
    return power


def set_auto_level_disable(alc):
    # sets the auto level to be disabled or enabled
    error_code, alc_enable = SC1.set_auto_level_disable(alc)
    _error_handler(error_code)
    return alc_enable


def set_list_dwell_time(d_time):
    # sets the list dwell time for the device
    error_code, dwell_time = SC1.set_list_dwell_time(d_time)
    _error_handler(error_code)
    return dwell_time


def set_list_cycle_count(num):
    # sets the list cycle count
    error_code, cycle_num = SC1.set_list_cycle_count(num)
    _error_handler(error_code)
    return cycle_num


def set_alc_mode(alc_mode):
    # sets the ALC mode
    error_code, alc_mode = SC1.set_alc_mode(alc_mode)
    _error_handler(error_code)
    return alc_mode


def list_buffer_points(points):
    # sets the number of list points
    error_code, l_points = SC1.list_buffer_points(points)
    _error_handler(error_code)
    return l_points


def list_buffer_write(command):
    # writes the frequency to the buffer list
    error_code, command = SC1.list_buffer_write(command)
    _error_handler(error_code)
    return command


def list_buffer_transfer(transfer_mode):
    # transfers the list frequencies between RAM and EEPROM
    # transfer_mode = 0 will transfer the list in current RAM into the EEPROM
    # 1 = transfer from EEPROM to RAM
    error_code, t_mode = SC1.list_buffer_transfer(transfer_mode)
    _error_handler(error_code)
    return t_mode


def set_list_soft_trigger():
    # sets the list soft trigger for the device
    error_code = SC1.set_list_soft_trigger()
    _error_handler(error_code)
    return error_code


def list_buffer_read():
    # retrieves frequency member from the device list buffer
    error_code, freq = SC1.list_buffer_read()
    _error_handler(error_code)
    return freq


def synth_self_cal():
    # self calibrates the synthesizer
    error_code = SC1.synth_self_cal()
    _error_handler(error_code)
    return error_code


def reg_read(reg_read, inst_word):
    # reads from the specified device register
    error_code, rec_word = SC1.reg_read(reg_read, inst_word)
    _error_handler(error_code)
    print(rec_word)
    return error_code, rec_word


def reg_write(reg_byte, ins_word):
    # writes to a specified deviced register
    error_code, ins_word = SC1.reg_write(reg_byte, ins_word)
    _error_handler(error_code)
    return error_code, ins_word


def set_list_start_freq(start_frequency):
    # allows the user to write the list start frequency
    error_code, start_freq = SC1.set_list_start_freq(start_frequency)
    _error_handler(error_code)
    return start_freq


def set_list_stop_freq(stop_frequency):
    # allows the user to write the list stop frequency
    error_code, stop_freq = SC1.set_list_stop_freq(stop_frequency)
    _error_handler(error_code)
    return stop_freq


def set_list_step_freq(step_frequency):
    # allows the user to write the list step frequency
    error_code, step_freq = SC1.set_list_step_freq(step_frequency)
    _error_handler(error_code)
    return step_freq


def set_list_cycle_count(num):
    # allows the user to specify the list cycle count
    error_code, cycle_num = SC1.set_list_cycle_count(num)
    _error_handler(error_code)
    return cycle_num


def set_list_soft_trigger():
    # allows the user to set the list soft trigger
    error_code = SC1.set_list_soft_trigger()
    _error_handler(error_code)
    return 0


# example code
if __name__ == "__main__":

    # how to initialize the device
    print("INITIALIZING AND GETTING BASIC DEVICE INFORMATION")
    print()
    print()

    # Establish the name and serial number of the instrument. Ensure that the serial number matches yours.
    SC1 = SignalCore_SC5511A("SC1", "10002374")

    #####################################################################################################

    # initializing some device input/output values
    set_rf1_frequency(12000000000)
    set_rf2_frequency(2000)
    set_level(4)

    # reading back the temperature
    print()
    print("Reading back the device temperature back in Farenheit...")
    device_temp()

    # disable the sweep/list mode
    print()
    print("Setting the RF mode to disable sweep/list mode...")
    set_rf_mode(0)

    # reading back the rf1 frequency
    print()
    get_rf1_frequency()

    # enabling rf1 output
    print()
    set_output(1)
    get_rf1_out_enable()

    # reading back the rf2 frequency
    print()
    get_rf2_frequency()

    # reading back the RF level
    print()
    get_power_level()

    # setting the clock reference
    print()
    print("The Ref to 100 MHz out, lock enabled")
    set_clock_reference_mode(0, 0, 1, 1)

    # getting the full device status
    print()
    display_operate_status()
    print()
    display_pll_status()

    # get the device identity
    print()
    get_idn()

    # get the device RF parameters
    print()
    display_rf_parameters()

    # use the register read to get RF1 frequency
    print()
    print("Using the read register function to retrieve the RF2 frequency")
    reg_read(0x20, 0)

    print("Completed the sc5511a python example, closing the device")
    # closing the device
    SC1._close()
