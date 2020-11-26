import logging
import random
import string

# TODO probably shouldn't be doing this in the library
logging.basicConfig(
    format='%(levelname)s: %(asctime)s - %(name)s (%(module)s:%(lineno)s): %(message)s',
    level=logging.WARNING,
)

logging.getLogger('kleroteria').setLevel(logging.DEBUG)

NONCE_LEN = 8
NONCE_CHARS = string.ascii_lowercase + string.ascii_uppercase


def generate_nonce():
    return ''.join(random.SystemRandom().choice(NONCE_CHARS) for _ in range(NONCE_LEN))
