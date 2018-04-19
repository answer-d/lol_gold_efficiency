from django import forms
from .logger import *


class ItemInputKeysForm(forms.Form):
    @logging
    def __init__(self, item, *args, **kwargs):
        super(ItemInputKeysForm, self).__init__(*args, **kwargs)

        request_params = args[0]

        for key in item.get_input_keys():
            initial_value = request_params[key] if key in request_params else None
            self.fields[key] = forms.IntegerField(required=False, label=key, initial=initial_value)
