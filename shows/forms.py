from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .personal import (
    MAX_NOTES_LENGTH,
    PERSONAL_FIELDS,
    WATCH_STATUSES,
    validate_personal_fields,
)


class SignInForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class PersonalForm(forms.Form):
    rating = forms.IntegerField(
        required=False,
        label="Personal rating",
        widget=forms.NumberInput(attrs={"min": 1, "max": 10}),
    )
    notes = forms.CharField(
        required=False,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 8, "maxlength": MAX_NOTES_LENGTH}),
    )
    watch_status = forms.ChoiceField(choices=WATCH_STATUSES)
    last_season = forms.IntegerField(
        required=False,
        label="Last season finished",
        widget=forms.NumberInput(attrs={"min": 0}),
    )
    last_episode = forms.IntegerField(
        required=False,
        label="Last episode finished",
        widget=forms.NumberInput(attrs={"min": 1}),
    )
    clear_bookmark = forms.BooleanField(
        required=False, label="Clear bookmark (keep watch status)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = (
                "textarea w-full"
                if name == "notes"
                else "select w-full"
                if name == "watch_status"
                else "checkbox"
                if name == "clear_bookmark"
                else "input w-full"
            )

    def clean(self):
        values = super().clean()
        unexpected = set(self.data) - {
            *PERSONAL_FIELDS,
            "clear_bookmark",
            "csrfmiddlewaretoken",
        }
        if unexpected:
            raise ValidationError(
                "Only personal viewing fields may be edited. Remove extra fields."
            )
        if self.errors:
            return values
        if values["clear_bookmark"]:
            values["last_season"] = values["last_episode"] = None
        try:
            validate_personal_fields(values)
        except ValidationError as exc:
            for field, errors in exc.message_dict.items():
                self.add_error(field, errors)
        return values
