from django import forms
from .models import Transaction


class VoteForm(forms.Form):
    num_votes = forms.IntegerField(
        label='Number of Votes',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'placeholder': '1', 'min': '1'}),
    )

    def clean_num_votes(self):
        val = self.cleaned_data['num_votes']
        if val < 1:
            raise forms.ValidationError("You must vote at least once.")
        return val
