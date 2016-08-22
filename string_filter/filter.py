# -*- coding: utf-8 -*-

"""
Has the filter that allows to filter by integer range.
"""

from django import forms
from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext as _

from django.contrib.admin.widgets import AdminTextInputWidget

try:
    from django.utils.html import format_html
except ImportError:
    from django.utils.html import conditional_escape, mark_safe

    def format_html(format_string, *args, **kwargs):
        args_safe = map(conditional_escape, args)
        kwargs_safe = dict((k, conditional_escape(v)) for (k, v) in kwargs.items())
        return mark_safe(format_string.format(*args_safe, **kwargs_safe))


# Django doesn't deal well with filter params that look like queryset lookups.
FILTER_PREFIX = 'sf__'


def clean_input_prefix(input_):
    return dict((key.split(FILTER_PREFIX)[1] if key.startswith(FILTER_PREFIX) else key, val)
                for (key, val) in input_.items())


class StringFilterBaseForm(forms.Form):
    def __init__(self, request, *args, **kwargs):
        super(StringFilterBaseForm, self).__init__(*args, **kwargs)
        self.request = request


class IntegerRangeForm(StringFilterBaseForm):

    def __init__(self, *args, **kwargs):
        field_name = kwargs.pop('field_name')
        super(IntegerRangeForm, self).__init__(*args, **kwargs)

        self.fields['%s%s__iexact' % (FILTER_PREFIX, field_name)] = forms.CharField(
            label='',
            widget=AdminTextInputWidget(
                attrs={'placeholder': _('split entries by commas')}
            ),
            localize=True,
            required=False
        )


class StringFilter(admin.filters.FieldListFilter):
    template = 'string_filter/filter.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_iexact = '%s%s__iexact' % (FILTER_PREFIX, field_path)
        super(StringFilter, self).__init__(
            field, request, params, model, model_admin, field_path)
        self.form = self.get_form(request)

    def choices(self, cl):
        """
        Pop the original parameters, and return the integer filter & other filter
        parameters.
        """
        cl.params.pop(self.lookup_kwarg_iexact, None)
        return ({
            'get_query': cl.params,
        }, )

    def expected_parameters(self):
        return [self.lookup_kwarg_iexact]

    def get_form(self, request):
        return IntegerRangeForm(request, data=self.used_parameters,
                             field_name=self.field_path)

    def queryset(self, request, queryset):
        if self.form.is_valid():
            # get no null params
            filter_params = clean_input_prefix(dict(filter(lambda x: bool(x[1]), self.form.cleaned_data.items())))

            # filter by iexact included
            lookup_iexact = self.lookup_kwarg_iexact.lstrip(FILTER_PREFIX)
            if filter_params.get(lookup_iexact) is not None:
                lookup_kwarg_values = filter_params.pop(lookup_iexact)

                values = [x.strip() for x in lookup_kwarg_values.split(',')]

                query = ""

                for value in values:
                    query += "Q({}__iexact='{}') | ".format(self.field_path, value)

                # strip unused " | " sign at the end of query string
                query = query[:-3]

                filtered_queryset = eval("queryset.filter({})".format(query))

                return filtered_queryset
        else:
            return queryset

# register the filters
admin.filters.FieldListFilter.register(
    lambda f: isinstance(f, models.CharField), StringFilter)
