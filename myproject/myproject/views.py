from django.http import HttpResponse

def homepage(request):
    return HttpResponse("Welcome to the Home Page!")

def about(request):
    return HttpResponse("This is the About Page.")