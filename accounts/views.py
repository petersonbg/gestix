from django.contrib.auth.views import LoginView, LogoutView


class GestixLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class GestixLogoutView(LogoutView):
    pass
