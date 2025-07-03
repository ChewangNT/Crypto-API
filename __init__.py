import sys


if sys.version_info < (3, 7):
    raise ImportError('该库所支持的最低版本为 Python 3.7')

from . import callback
from . import error
from . import database

from .callback import Session, Callback
from .error import BaseError
from .database import INTERFACE, Database


__version__ = '1.0.0'
__author__ = 'NT CheWang'
__email__ = 'ChewangNeko@outlook.com'
