from .base import *

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = split_env_list(config('ALLOWED_HOSTS', default='localhost,127.0.0.1'))
