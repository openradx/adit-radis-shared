from crispy_forms.bootstrap import FieldWithButtons
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Hidden, Layout, Submit
from django import forms
from django.http.request import QueryDict

from adit_radis_shared.accounts.models import User


class RecipientsField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj: User):
        return f"{obj.username} <{obj.email}>"


class BroadcastForm(forms.Form):
    recipients = RecipientsField(
        label="Recipients",
        queryset=User.objects.order_by("username"),
    )
    subject = forms.CharField(label="Subject", max_length=200)
    message = forms.CharField(label="Message", max_length=10000, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recipients"].widget.attrs["size"] = 10


class SingleFilterFieldFormHelper(FormHelper):
    """One filter of a model is rendered in a field with button form."""

    def __init__(
        self,
        params: QueryDict | dict,
        field_name: str,
        button_label: str = "Filter",
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.form_method = "get"
        self.disable_csrf = True

        self.params = params
        self._field_name = field_name
        self._field = Field(field_name, css_class="form-control-sm")

        self.layout = Layout()
        self.layout.append(
            FieldWithButtons(
                self._field,
                Submit(
                    "",
                    button_label,
                    css_class="btn-secondary btn-sm",
                ),
                template="common/_filter_set_field.html",
            ),
        )

        hidden_fields = Div()
        self.layout.append(hidden_fields)

        for key in self.params:
            if key != field_name and key != "page":
                hidden_fields.append(Hidden(key, self.params.get(key)))

    def render_layout(self, form: forms.Form, *args, **kwargs):
        if isinstance(form.fields.get(self._field_name), forms.ChoiceField):
            self._field.attrs["class"] += " form-select form-select-sm"

        return self.layout.render(form, *args, **kwargs)
