from django import forms


class DateDemoForm(forms.Form):
    demo_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Pick a date",
        required=True,
    )
