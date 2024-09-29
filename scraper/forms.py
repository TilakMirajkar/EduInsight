from django import forms


class UserInput(forms.Form):
    prefix_usn = forms.CharField(max_length=7)  # first 7 characters of USN
    suffix_usn = forms.CharField()  # USN range
    main_sem = forms.IntegerField(max_value=8)  # Semester
    url_value = forms.CharField()   # result page URl

    # placeholder values
    def __init__(self, *args, **kwargs):
        super(UserInput, self).__init__(*args, **kwargs)
        self.fields['prefix_usn'].widget.attrs.update({'class': 'input', 'placeholder': 'e.g 2AG21CS'})
        self.fields['suffix_usn'].widget.attrs.update({'class': 'input', 'placeholder': 'e.g 1-100'})
        self.fields['main_sem'].widget.attrs.update({'class': 'input', 'placeholder': 'e.g 5'})
        self.fields['url_value'].widget.attrs.update(
            {'class': 'input', 'placeholder': 'e.g https://results.vtu.ac.in/DJcbcs24/index.php'})
