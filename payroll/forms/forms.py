"""
forms.py
"""

from datetime import date
from typing import Any

from django import forms
from django.forms import widgets
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as trans

from base.forms import Form
from base.methods import reload_queryset
from employee.forms import MultipleFileField
from employee.models import Employee
from horilla import horilla_middlewares
from payroll.context_processors import get_active_employees
from payroll.models.models import (
    Contract,
    EncashmentGeneralSettings,
    PayrollGeneralSetting,
    ReimbursementFile,
    ReimbursementrequestComment,
)


class ModelForm(forms.ModelForm):
    """
    ModelForm override for additional style
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        for _, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.DateInput)):
                field.initial = date.today()

            if isinstance(widget, (forms.DateInput)):
                field.widget.attrs.update({"class": "oh-input oh-calendar-input w-100"})
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                label = trans(field.label)
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                label = trans(field.label)
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})

            try:
                self.fields["employee_id"].initial = request.user.employee_get
            except:
                pass

            try:
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


class ContractForm(ModelForm):
    """
    ContactForm
    """

    verbose_name = trans("Contract")
    contract_start_date = forms.DateField()
    contract_end_date = forms.DateField(required=False)

    class Meta:
        """
        Meta class for additional options
        """

        fields = "__all__"
        exclude = [
            "is_active",
        ]
        model = Contract

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].widget.attrs.update(
            {"onchange": "contractInitial(this)"}
        )
        self.fields["contract_start_date"].widget = widgets.DateInput(
            attrs={
                "type": "date",
                "class": "oh-input w-100",
                "placeholder": "Select a date",
            }
        )
        self.fields["contract_end_date"].widget = widgets.DateInput(
            attrs={
                "type": "date",
                "class": "oh-input w-100",
                "placeholder": "Select a date",
            }
        )
        self.fields["contract_status"].widget.attrs.update(
            {
                "class": "oh-select",
            }
        )
        if self.instance and self.instance.pk:
            dynamic_url = self.get_dynamic_hx_post_url(self.instance)
            self.fields["contract_status"].widget.attrs.update(
                {
                    "hx-target": "this",
                    "hx-post": dynamic_url,
                    "hx-swap": "beforebegin",
                }
            )
        first = PayrollGeneralSetting.objects.first()
        if first and self.instance.pk is None:
            self.initial["notice_period_in_days"] = first.notice_period
        self.fields["contract_document"].widget.attrs[
            "accept"
        ] = ".jpg, .jpeg, .png, .pdf"

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("contract_form.html", context)
        return table_html

    def get_dynamic_hx_post_url(self, instance):
        return f"/payroll/update-contract-status/{instance.pk}"


class ReimbursementRequestCommentForm(ModelForm):
    """
    ReimbursementRequestCommentForm form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ReimbursementrequestComment
        fields = ("comment",)


class reimbursementCommentForm(ModelForm):
    """
    Reimbursement request comment model form
    """

    verbose_name = "Add Comment"

    class Meta:
        model = ReimbursementrequestComment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["files"] = MultipleFileField(label="files")
        self.fields["files"].required = False
        self.fields["files"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        multiple_files_ids = []
        files = None
        if self.files.getlist("files"):
            files = self.files.getlist("files")
            self.instance.attachemnt = files[0]
            multiple_files_ids = []
            for attachemnt in files:
                file_instance = ReimbursementFile()
                file_instance.file = attachemnt
                file_instance.save()
                multiple_files_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.files.add(*multiple_files_ids)
        return instance, files


class EncashmentGeneralSettingsForm(ModelForm):
    class Meta:
        model = EncashmentGeneralSettings
        fields = "__all__"

class DashboardExport(forms.Form):
    status_choices = [
        ("", ""),
        ("draft", "Draft"),
        ("review_ongoing", "Review Ongoing"),
        ("confirmed", "Confirmed"),
        ("paid", "Paid"),
    ]
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input w-100"}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input w-100"}),
    )
    
    # Use only necessary fields and exclude large NCLOB fields
    employees = forms.ChoiceField(
        required=False,
        choices=[],  # Will be populated in __init__
        widget=forms.SelectMultiple,
    )
    
    status = forms.ChoiceField(required=False, choices=status_choices)
    
    # Use only necessary fields and exclude large NCLOB fields
    contributions = forms.ChoiceField(
        required=False,
        choices=[],  # Will be populated in __init__
        widget=forms.SelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fetch only necessary fields for employees to avoid NCLOB fields
        employee_choices = [
            (emp.id, emp.get_full_name()) 
            for emp in Employee.objects.only('id', 'employee_first_name', 'employee_last_name')  # Only fetch necessary fields
        ]
        self.fields['employees'].choices = employee_choices

        # Dynamically load contributions choices (active employees)
        active_employees = get_active_employees()  # Ensure this returns Employee instances
        contributions_choices = [
            (emp.id, emp.get_full_name())  # This assumes emp is an Employee object with an id and get_full_name()
            for emp in active_employees
        ]
        self.fields['contributions'].choices = contributions_choices

# Helper function to retrieve active employees (this function should return Employee objects)
def get_active_employees():
    # Ensure that we are retrieving Employee instances, not just strings.
    return Employee.objects.filter(is_active=True).only('id', 'employee_first_name', 'employee_last_name')