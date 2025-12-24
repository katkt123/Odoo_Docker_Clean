from . import models
from . import controllers


def post_init_hook(env):
	# Keep this minimal: required for fresh DB installs.
	# Data seeding is handled by the cron / manual actions in the module.
	return