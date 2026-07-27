from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario
from viviendas.models import Vivienda, Portal
from urbanizaciones.models import Urbanizacion


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'email': 'Email',
            'telefono': 'Teléfono',
        }


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Email', required=True)
    telefono = forms.CharField(label='Teléfono', max_length=20, required=False)
    urbanizacion = forms.ModelChoiceField(
        queryset=Urbanizacion.objects.all(),
        label='Urbanización',
        empty_label='Selecciona tu urbanización',
    )
    portal = forms.ModelChoiceField(
        queryset=Portal.objects.none(),
        label='Portal',
        empty_label='Selecciona el portal',
    )
    vivienda = forms.ModelChoiceField(
        queryset=Vivienda.objects.none(),
        label='Vivienda (piso)',
        empty_label='Selecciona tu piso',
    )

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono',
                  'urbanizacion', 'portal', 'vivienda', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'urbanizacion' in self.data:
            try:
                urb_id = int(self.data.get('urbanizacion'))
                self.fields['portal'].queryset = Portal.objects.filter(urbanizacion_id=urb_id)
            except (ValueError, TypeError):
                pass
        if 'portal' in self.data:
            try:
                portal_id = int(self.data.get('portal'))
                self.fields['vivienda'].queryset = Vivienda.objects.filter(portal_id=portal_id)
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.vivienda = self.cleaned_data['vivienda']
        user.telefono = self.cleaned_data.get('telefono', '')
        user.aprobado = False
        if commit:
            user.save()
        return user


class CrearComunidadForm(UserCreationForm):
    """Alta self-service de una urbanización nueva: crea la Urbanizacion, su
    primer Portal/Vivienda, y el Usuario que la administra (admin_urb,
    aprobado automáticamente — es el único responsable de su propia
    comunidad, no necesita que nadie más lo apruebe)."""

    first_name = forms.CharField(label='Nombre', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Email', required=True)
    telefono = forms.CharField(label='Teléfono', max_length=20, required=False)

    urb_nombre = forms.CharField(label='Nombre de la urbanización', max_length=200)
    urb_direccion = forms.CharField(label='Dirección', max_length=300)
    num_pistas = forms.IntegerField(label='Número de pistas', min_value=1, initial=1)

    portal_nombre = forms.CharField(label='Portal', max_length=50, initial='A')
    piso = forms.CharField(label='Tu piso', max_length=10)
    puerta = forms.CharField(label='Puerta', max_length=5, required=False)

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)

        urb = Urbanizacion.objects.create(
            nombre=self.cleaned_data['urb_nombre'],
            direccion=self.cleaned_data['urb_direccion'],
            num_pistas=self.cleaned_data['num_pistas'],
        )
        portal = Portal.objects.create(urbanizacion=urb, nombre=self.cleaned_data['portal_nombre'])
        vivienda = Vivienda.objects.create(
            portal=portal, piso=self.cleaned_data['piso'], puerta=self.cleaned_data.get('puerta', ''),
        )

        user.vivienda = vivienda
        user.telefono = self.cleaned_data.get('telefono', '')
        user.rol = Usuario.ROL_ADMIN_URB
        user.aprobado = True
        if commit:
            user.save()
        return user
