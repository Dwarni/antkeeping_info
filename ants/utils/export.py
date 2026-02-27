"""Utility functions for exporting ant data as CSV or JSON."""

import csv

from django.http import HttpResponse, JsonResponse


def export_csv_response(queryset_or_list, filename, headers, row_getter):
    """Return an HttpResponse with CSV content as a file download.

    Adds a UTF-8 BOM so Excel opens the file correctly.
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    response.write("\ufeff")  # BOM for Excel UTF-8 compatibility
    writer = csv.writer(response)
    writer.writerow(headers)
    for item in queryset_or_list:
        writer.writerow(row_getter(item))
    return response


def export_json_response(data, filename):
    """Return a JsonResponse as a file download."""
    response = JsonResponse(
        data,
        safe=False,
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.json"'
    return response
