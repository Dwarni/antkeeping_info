"""Module which contains all views of flights app."""
from django.conf import settings
from django.core.serializers import serialize
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, TemplateView, DetailView, View, DeleteView
from django.shortcuts import redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .forms import FlightForm
from .models import Flight


# Create your views here.
class AddFlightView(FormView):
    """View for adding a new flight."""
    template_name = 'flights/flights_add.html'
    form_class = FlightForm
    success_url = reverse_lazy('flights_map')
    def form_valid(self, form):
        form.create_flight(self.request.user.is_staff)
        return super().form_valid(form)

class FlightsMapView(TemplateView):
    """View for the flights map."""
    template_name = 'flights/flights_map.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY_CLIENT
        return context

class FlightsListView(ListView):
    """List view for flights."""
    model = Flight
    # queryset = Flight.objects.filter(reviewed=True)
    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [{'id': flight.id, 'lat': flight.latitude, 'lng': flight.longitude, 'ant': flight.ant_species.name} for flight in qs]
        return JsonResponse(data, status=200, safe=False)
    

class FlightInfoWindow(DetailView):
    """View for google maps info window."""
    template_name = 'flights/info_window.html'
    model = Flight
    context_object_name = 'flight'

@method_decorator(staff_member_required, name='dispatch')
class FlightsReviewListView(ListView):
    """Displays all not yet reviewed flights."""
    model = Flight
    template_name = "flights/flights_review.html"
    queryset = model.objects.filter(reviewed=False)
    context_object_name = 'flights'

@method_decorator(staff_member_required, name='dispatch')
class FlightReviewView(View):
    def post(self, request, **kwargs):
        pk = kwargs.get('pk')
        flight = get_object_or_404(Flight, pk=pk)
        flight.reviewed = True
        flight.save()

        return redirect('flights_review_list')

@method_decorator(staff_member_required, name='dispatch')
class FlightDeleteView(DeleteView):
    model = Flight
    success_url = reverse_lazy('flights_review_list')
