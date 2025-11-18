from django import forms


class DateDemoForm(forms.Form):
    demo_date = forms.DateField(
        label="Demo date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
