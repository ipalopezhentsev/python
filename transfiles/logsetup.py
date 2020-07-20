# intended to be included to every module requiring logging.
# motivation is that it allows to run tests from IDE and still see INFO level messages.
# without this, there would be nobody calling basicConfig and changing default minimum level of WARN

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")