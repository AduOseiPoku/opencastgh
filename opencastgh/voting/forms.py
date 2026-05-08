from django import forms
from .models import Transaction


VOTE_CHOICES = [(i, f"{i} vote{'s' if i > 1 else ''}") for i in [1, 2, 3, 5, 10, 20, 50]]


class VoteForm(forms.Form):
    voter_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Your full name'}),
        label='Your Name',
    )
    voter_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
        label='Email Address',
        help_text='Your receipt will be sent here.',
    )
    voter_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '024XXXXXXX'}),
        label='Phone Number (optional)',
    )
    num_votes = forms.ChoiceField(
        choices=VOTE_CHOICES,
        label='Number of Votes',
        initial=1,
    )

    def clean_num_votes(self):
        val = int(self.cleaned_data['num_votes'])
        if val < 1:
            raise forms.ValidationError("You must vote at least once.")
        return val
