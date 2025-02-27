# convenience import for all LabOne Q software functionality
# argparse
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from laboneq.simple import *

parser = ArgumentParser(
    description="Script automatically flag receipts, it assume a collection of file beginning with receipt_, but can be set with a different filestart",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

# add argument
parser.add_argument("-f", "--filename", help="Name of the file with the json to plot")
parser.add_argument("-o", "--outname", help="name to give the pulse sheet viewer")
parser.add_argument(
    "--maxlength",
    type=float,
    default=10e-3,
    help="max simulation length in the pulse_sheet_viewer",
)
parser.add_argument(
    "--maxevents",
    type=int,
    default=1000,
    help="max events to publish in the pulse sheet viewer",
)

args = parser.parse_args()

compiled_experiment = CompiledExperiment.load(args.filename)

show_pulse_sheet(
    args.outname,
    compiled_experiment=compiled_experiment,
    max_events_to_publish=args.maxevents,
    max_simulation_length=args.maxlength,
    interactive=True,
)
