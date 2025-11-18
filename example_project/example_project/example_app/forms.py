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
