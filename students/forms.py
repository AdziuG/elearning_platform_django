from django import forms
from courses.models import Course


class CourseEnrollForm(forms.Form):
    """form for students to enroll on courses"""
    course = forms.ModelChoiceField(queryset=Course.objects.all(), widget=forms.HiddenInput)