from django.utils.translation import gettext_lazy as _

from utilities.choices import  ChoiceSet

class LogLevelChoices(ChoiceSet):

    LOG_DEFAULT = 'default'
    LOG_SUCCESS = 'success'
    LOG_INFO = 'info'
    LOG_WARNING = 'warning'
    LOG_FAILURE = 'failure'

    CHOICES = (
        (LOG_DEFAULT, _('Default'), 'gray'),
        (LOG_SUCCESS, _('Success'), 'green'),
        (LOG_INFO, _('Info'), 'cyan'),
        (LOG_WARNING, _('Warning'), 'yellow'),
        (LOG_FAILURE, _('Failure'), 'red'),
    )

class LogCategoryChoices(ChoiceSet):

    SETTING = 'setting'
    ONBOARD = 'onboard'
    DATA_MAPPING = 'data_mapping'
    RECONCILE = 'reconcile'
    INIT = 'init'
    PLANNING = 'planning'
    LOGGING = 'logging'

    CHOICES = (
        (SETTING, _('setting')),
        (ONBOARD, _('onboard')),
        (DATA_MAPPING, _('data_mapping')),
        (RECONCILE, _('reconcile')),
        (INIT, _('init')),
        (PLANNING, _('planning')),
        (LOGGING, _('logging')),
    )

class SlurpitApplianceTypeChoices(ChoiceSet):

    PUSH = 'push'
    PULL = 'pull'
    BOTH = 'both'

    CHOICES = (
        (PUSH, _('PUSH')),
        (PULL, _('PULL')),
        (BOTH, _('BOTH')),
    )