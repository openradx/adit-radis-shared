from django import forms


class DateDemoForm(forms.Form):
    demo_date = forms.DateField(
        label="Demo date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    demo_datetime = forms.DateTimeField(
        required=False,
        label="Demo datetime",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Uses browser datetime-local widget; sends local time without timezone info.",
    )
    freeform_date = forms.DateField(
        required=False,
        label="Free-form date",
        help_text="Plain text field using Django's default DateField parsing.",
    )
