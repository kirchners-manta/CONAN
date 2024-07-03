#!/usr/bin/python3.10
# The program is written by Leonard Dick, 2023

import os
import sys
import time

import conan.defdict as ddict
from conan import simbox
from conan.build_modules import build_main


def main():
    # Add the 'build_module' directory to the import path
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    target_directory = os.path.join(current_script_dir, "build_modules")
    sys.path.append(target_directory)
    target_directory = os.path.join(current_script_dir, "analysis_modules")
    sys.path.append(target_directory)

    # RUNTIME
    start_time = time.time()

    # MAIN
    # Rename old log file if it exists. Starting from 1 and going up from there.
    id_num = 1
    # Check if log file exists.
    if os.path.exists("conan.log"):
        # Increment id_num if log file with that name already exists.
        while os.path.exists(f"conan-{id_num}.log"):
            id_num += 1
        # Rename the existing log file.
        os.rename("conan.log", f"conan-{id_num}.log")

    # print command
    ddict.printLog("{}".format(" ".join(sys.argv)))
    ddict.printLog("")

    # LOGO
    ddict.printLog("###########################################", color="yellow")
    ddict.printLog("##                                       ##", color="yellow")
    ddict.printLog("##   #####  #####  #   #  #####  #   #   ##", color="yellow")
    ddict.printLog("##   #      #   #  ##  #  #   #  ##  #   ##", color="yellow")
    ddict.printLog("##   #      #   #  # # #  #####  # # #   ##", color="yellow")
    ddict.printLog("##   #      #   #  #  ##  #   #  #  ##   ##", color="yellow")
    ddict.printLog("##   #####  #####  #   #  #   #  #   #   ##", color="yellow")
    ddict.printLog("##                                       ##", color="yellow")
    ddict.printLog("###########################################", color="yellow")
    ddict.printLog("")

    # INFO
    # Refer to the documentation and papers for more information on the program.
    ddict.printLog("Find the documentation on the CONAN website: http://con-an.readthedocs.io")
    ddict.printLog("If you use CONAN in your research, please cite the following papers:")
    ddict.printLog("doi.org/10.1021/acs.jcim.3c01075")
    ddict.printLog("doi.org/10.1021/acs.jpcb.3c08493")

    # ARGUMENTS
    args = ddict.read_commandline()

    # CBUILD SECTION
    if args["cbuild"]:
        build_main.main(args)

    # SIMULATION SETUP SECTION
    if args["box"]:
        simbox.simbox_mode(args)

    # TRAJECTORY ANALYSIS SECTION
    if args["trajectoryfile"]:
        ddict.printLog("")

        # Load the atom data.
        from conan.analysis_modules import traj_info

        id_frame, box_size = traj_info.read_first_frame(args)

        maindict = {"id_frame": id_frame, "box_size": box_size, "args": args}

        maindict = traj_info.structure_recognition(maindict)

        from conan.analysis_modules import traj_an

        traj_an.analysis_opt(maindict)

    ddict.printLog("The program took %0.3f seconds to run." % (time.time() - start_time))


if __name__ == "__main__":
    main()
