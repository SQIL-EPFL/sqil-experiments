from typing import cast

import sqil_core as sqil
from sqil_core.config_log import logger

# Connect to the server and retrieve instruments
server, instruments = sqil.experiment.link_instrument_server()

# Check available instruments
logger.info("Connected to the instruments server")
logger.info(f" instruments: {list(instruments.keys())}")

# Do something
sgs = cast(sqil.experiment.LocalOscillator, instruments["sgs"])
logger.debug("Requesting SGS frequency change to 11 GHz")
sgs.frequency(11e9)

# Disconnect from the instrument server and release variables
sqil.experiment.unlink_instrument_server(server, **instruments)
