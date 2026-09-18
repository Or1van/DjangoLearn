# from django.http import HttpResponse
from django.shortcuts import render

def homepage(request):
  #  return HttpResponse("Welcome to the Home Page!")
  return render(request, 'home.html')

def about(request):
   # return HttpResponse("This is the About Page.")
   return render(request, 'about.html')