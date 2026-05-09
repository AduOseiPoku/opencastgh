from django import forms
from .models import Transaction


class VoteForm(forms.Form):
    num_votes = forms.IntegerField(
        label='Number of Votes',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'placeholder': '1', 'min': '1'}),
    )

    def __init__(self, *args, max_votes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_votes = max_votes
        if max_votes:
            self.fields['num_votes'].widget.attrs['max'] = max_votes

    def clean_num_votes(self):
        val = self.cleaned_data['num_votes']
        if val < 1:
            raise forms.ValidationError("You must vote at least once.")
        if self.max_votes and val > self.max_votes:
            raise forms.ValidationError(
                f"You can only purchase up to {self.max_votes} votes per transaction."
            )
        return val
