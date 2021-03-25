from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def home(request):
    return render(request, "home/home.html")
