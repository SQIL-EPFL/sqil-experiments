import os
import sys
from distutils.dir_util import copy_tree

import matplotlib.pyplot as plt
import numpy as np
import tqdm
from helpers.setup.TD_Setup import (
    db_path,
    db_path_local,
    main_descriptor,
    param_dict,
    pd_file,
    setup_file,
    sgs_IP,
    wiring,
)
from helpers.taketo_datadict_storage import DataDict, DDH5Writer
from helpers.utilities import external_average_loop_2data
from laboneq.simple import *
from qcodes.instrument_drivers.rohde_schwarz import RohdeSchwarzSGS100A
from qcodes_contrib_drivers.drivers.SignalCore.SignalCore import SC5521A

sys.path.append("../analysis_code")
import constants as const
from single_shot_exp import exp_file, main_exp
from single_shot_gaussian import compute_threshold_two_gaussian


def iq_rand(length, centre_x, centre_y):
    # generating dummy data for emulation mode
    return np.random.normal(centre_x, 1, length) + 1j * np.random.normal(
        centre_y, 1, length
    )


exp_name = "single_shot"
tags = ["0_single_shot"]

# update param_dict when local parameter used
local_param_list = param_dict["single_shot"].keys()
for key in local_param_list:
    if key in param_dict.keys():
        if not param_dict["single_shot"][key] == False:
            param_dict[key] = param_dict["single_shot"][key]

if param_dict["single_shot"]["sweep"] == False:
    sweep_list = [0]
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        index=dict(),
        ground_data=dict(axes=["index"]),
        excited_data=dict(axes=["index"]),
    )
    datadict.validate()
else:
    exp_name = exp_name + "_vs_" + param_dict["single_shot"]["sweep"]
    tags.append(f"0_{exp_name}")
    param_dict[param_dict["single_shot"]["sweep"]] = "sweeping"
    if param_dict["sweep_list"] == False:
        sweep_list = np.linspace(
            param_dict["sweep_start"],
            param_dict["sweep_stop"],
            param_dict["sweep_npts"],
        )
        param_dict["sweep_list"] = sweep_list
    else:
        sweep_list = param_dict["sweep_list"]
        param_dict["sweep_start"] = False
        param_dict["sweep_stop"] = False
        param_dict["sweep_npts"] = False
    # define DataDict for saving in DDH5 format
    datadict = DataDict(
        index=dict(),
        sweep_param=dict(unit=""),
        ground_data=dict(axes=["index", "sweep_param"]),
        excited_data=dict(axes=["index", "sweep_param"]),
    )
    datadict.validate()

with DDH5Writer(datadict, db_path_local, name=exp_name) as writer:
    filepath_parent = writer.filepath.parent
    writer.add_tag(tags)
    writer.save_dict("param_dict.json", param_dict)
    writer.backup_file([__file__, setup_file, pd_file, exp_file])
    writer.save_text("wiring.md", wiring)

    # take the last two stages of the filepath_parent
    path = str(filepath_parent)
    last_two_parts = path.split(os.sep)[-2:]
    new_path = os.path.join(db_path, *last_two_parts)
    writer.save_text("directry_path.md", new_path)

    ## connect to the equipment
    # connect to Signal core (LO source)
    sc = SC5521A("mw1")
    # connect to R&S SGS100A
    # sgsa = RohdeSchwarzSGS100A("SGSA100", sgs_IP)

    # setting of Signal Core
    sc.status("off")
    sc.power(-10)  # for safety
    sc.clock_frequency(10)
    # setting of R&S SGS100A
    # sgsa.status(False)
    # sgsa.power(-60) # for safety

    # ZInstrument; create and connect to a session
    device_setup = DeviceSetup.from_descriptor(main_descriptor)
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=False, reset_devices=True)

    sc.status("on")
    # sgsa.status(True)
    for sweep_param in tqdm.tqdm(sweep_list):
        # update param_dict
        if not param_dict["single_shot"]["sweep"] == False:
            param_dict[param_dict["single_shot"]["sweep"]] = sweep_param

        ## update parameters
        # setting of SGS100A
        sc.power(param_dict["ro_exLO_power"])
        sc.frequency(param_dict["ro_exLO_freq"])

        # define ZI experiment
        exp = main_exp(session, param_dict)
        compiled_exp = session.compile(exp)

        # output and save a pulse sheet
        if param_dict["save_pulsesheet"] == True:
            show_pulse_sheet(
                f"{writer.filepath.parent}/pulsesheet", compiled_exp, interactive=False
            )

        # run the experiment and take external averages
        ground_data, excited_data = external_average_loop_2data(
            session, compiled_exp, param_dict["external_avg"]
        )

        if param_dict["single_shot"]["sweep"] == False:
            writer.add_data(
                index=list(range(param_dict["single_shot"]["n_shots"])),
                ground_data=ground_data,
                excited_data=excited_data,
            )
        else:
            writer.add_data(
                index=list(range(param_dict["single_shot"]["n_shots"])),
                sweep_param=sweep_param,
                ground_data=ground_data,
                excited_data=excited_data,
            )

    sc.status("off")
    # sgsa.status(False)
    sc.close()
    # sgsa.close()

### plotting
path = str(filepath_parent)

"""
if param_dict["single_shot"]["sweep"]==False:
    
    plt.close('all') 
    
    #reload all data after writer-object is released
    filename = os.path.join(filepath_parent, 'data.ddh5')
    h5file = h5py.File(filename,"r")
    
    db_ro_pulse_length = h5file["data"]["ro_pulse_length"][:]  
    nominal_parameter, nominal_parameter_idx = [np.take(db_ro_pulse_length, int(db_ro_pulse_length.size // 2)), int(db_ro_pulse_length.size // 2)]
       
    db_ground_data = h5file["data"]["ground_data"][:][:]
    db_excited_data = h5file["data"]["excited_data"][:][:]

    # compute contrast, threshold and fidelity for nominal condition
    threshold, SNR, fidelity = compute_threshold(db_ground_data[nominal_parameter_idx], db_excited_data[nominal_parameter_idx], plotting=True, path=f"{filepath_parent}")
    
    print(f"threshold={threshold:g}")
    print(f"SNR={SNR:g}")
    print(f"fidelity={fidelity:g}")
    
    # plot contrast vs readout parameter
    SNR_vs_readout_power = np.empty((0,2), float)
    for idx, readout_parameter in enumerate(db_ro_pulse_length):
        threshold, SNR, fidelity ,g_fit,e_fit= compute_threshold_two_gaussian(db_ground_data[idx], db_excited_data[idx], plotting=False, path=f"{filepath_parent}")
        SNR_vs_readout_power = np.append(SNR_vs_readout_power, [[readout_parameter, SNR]], axis=0)
        
    fig_SNR_vs_readout_parameter = plt.figure()
    ax_SNR_vs_readout_parameter = fig_SNR_vs_readout_parameter.add_subplot(111)
    ax_SNR_vs_readout_parameter.set_title('SNR vs readout parameter')
    ax_SNR_vs_readout_parameter.scatter(SNR_vs_readout_power[:,0], SNR_vs_readout_power[:,1])
 #%%   
"""
threshold, SNR, fidelity, g_fit, e_fit = compute_threshold_two_gaussian(
    ground_data, excited_data, plotting=True, path=f"{filepath_parent}"
)
A0 = g_fit[0]
A1 = g_fit[3]
p1 = A1 / (A1 + A0)
T_qu = const.h * param_dict["qu_freq"] / (const.k_B * np.log(1 / p1 - 1))
print("T_qu=" + str(T_qu * 1000) + "mK")
print("SNR=" + f"{SNR}")
with open(path + r"\fitted_params.md", "w") as f:
    f.write("SNR=" + f"{SNR}\n" + "T_qu=" + str(T_qu * 1000) + "mK")

# copy the directory to the server
copy_tree(filepath_parent, new_path)
plt.show()
# from ro_length_optimization import ro_opt_plot
# filepath_parent = writer.filepath.parent

# filename = os.path.join(filepath_parent, 'data.ddh5')
# h5file = h5py.File(filename,"r")
# data1 = h5file["data"]["ground_data"][::]*1e3 #transform to unit mV
# data0 = h5file["data"]["excited_data"][::]*1e3 #transform to unit mV
# interval =h5file["data"]["excited_data"][0][::]#h5file["data"]["interval"][::]*1e6 # transform to unit us
# data=np.vstack((data0,data1))
# ro_opt_plot(data,interval)
# plt.savefig(f"{writer.filepath.parent}/Readout_optimization.png", bbox_inches='tight')
# bins=100
# qubit_temp=np.zeros(int(db_excited_data.shape[1]/bins))
# plt.figure(8)
# for i in range(0,db_excited_data.shape[1]-bins+1,bins):

#         samples1=db_excited_data[:,i:i+bins]
#         averaged1=np.average(samples1,axis=1)
#         samples2=db_ground_data[:,i:i+bins]
#         averaged2=np.average(samples2,axis=1)


#         plt.plot(np.real(averaged2),np.imag(averaged2),'ko')
#         plt.plot(np.real(averaged1),np.imag(averaged1),'ro')
