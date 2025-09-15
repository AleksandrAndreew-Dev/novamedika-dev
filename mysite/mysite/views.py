from django.shortcuts import render



def show_psi(request):
  return render(request, 'psi/psi_new2.html')


def show_nova(request):
  return render(request, 'nova_new/nova_temp_new.html')
