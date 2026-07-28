from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Usuario
from .models import Participante, Reserva, ResultadoPartido, SetResultado, validar_set
from datetime import datetime, timedelta


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['pista', 'fecha', 'hora_inicio']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.HiddenInput(),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario and usuario.urbanizacion:
            self.fields['pista'].queryset = usuario.urbanizacion.pistas.filter(activa=True)

    def clean(self):
        cleaned = super().clean()
        pista = cleaned.get('pista')
        fecha = cleaned.get('fecha')
        hora_inicio = cleaned.get('hora_inicio')

        # El modelo valida su propio estado en clean(), que se ejecuta sobre
        # self.instance antes de que ModelForm asigne los campos que no están
        # en Meta.fields (usuario, hora_fin) — hay que fijarlos aquí a mano.
        if self.usuario:
            self.instance.usuario = self.usuario

        if pista and fecha and hora_inicio:
            urb = pista.urbanizacion
            duracion = timedelta(minutes=urb.duracion_franja_minutos)
            inicio_dt = datetime.combine(fecha, hora_inicio)
            hora_fin = (inicio_dt + duracion).time()
            cleaned['hora_fin'] = hora_fin
            self.instance.hora_fin = hora_fin

        return cleaned

    def save(self, commit=True):
        reserva = super().save(commit=False)
        reserva.usuario = self.usuario
        if commit:
            reserva.save()
        return reserva


class ResultadoPartidoForm(forms.Form):
    """No es ModelForm: los jugadores pueden ser un Usuario con perfil o un
    invitado sin cuenta (solo un nombre), y los sets son varios objetos
    relacionados — más simple validarlo todo junto aquí y orquestar la
    creación en save()."""

    equipo_a_companero = forms.ModelChoiceField(
        queryset=Usuario.objects.none(), required=False, label='Tu compañero (dobles, opcional)',
    )
    equipo_a_companero_invitado = forms.CharField(
        required=False, max_length=100, label='…o nombre si no tiene perfil',
        widget=forms.TextInput(attrs={'placeholder': 'Nombre (sin perfil en la app)'}),
    )
    equipo_b_jugador1 = forms.ModelChoiceField(
        queryset=Usuario.objects.none(), required=False, label='Rival 1',
    )
    equipo_b_jugador1_invitado = forms.CharField(
        required=False, max_length=100, label='…o nombre si no tiene perfil',
        widget=forms.TextInput(attrs={'placeholder': 'Nombre (sin perfil en la app)'}),
    )
    equipo_b_jugador2 = forms.ModelChoiceField(
        queryset=Usuario.objects.none(), required=False, label='Rival 2 (dobles, opcional)',
    )
    equipo_b_jugador2_invitado = forms.CharField(
        required=False, max_length=100, label='…o nombre si no tiene perfil',
        widget=forms.TextInput(attrs={'placeholder': 'Nombre (sin perfil en la app)'}),
    )

    set1_a = forms.IntegerField(min_value=0, max_value=30, label='Set 1 — vosotros')
    set1_b = forms.IntegerField(min_value=0, max_value=30, label='Set 1 — rivales')
    set2_a = forms.IntegerField(min_value=0, max_value=30, required=False, label='Set 2 — vosotros')
    set2_b = forms.IntegerField(min_value=0, max_value=30, required=False, label='Set 2 — rivales')
    set3_a = forms.IntegerField(min_value=0, max_value=30, required=False, label='Set 3 / súper tie-break — vosotros')
    set3_b = forms.IntegerField(min_value=0, max_value=30, required=False, label='Set 3 / súper tie-break — rivales')
    set3_es_super_tiebreak = forms.BooleanField(required=False, label='El set 3 fue un súper tie-break (a 10)')

    def __init__(self, *args, usuario, reserva, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.reserva = reserva
        candidatos = Usuario.objects.filter(
            vivienda__portal__urbanizacion=reserva.urbanizacion, aprobado=True,
        ).exclude(pk=usuario.pk).order_by('first_name', 'username')
        self.fields['equipo_a_companero'].queryset = candidatos
        self.fields['equipo_b_jugador1'].queryset = candidatos
        self.fields['equipo_b_jugador2'].queryset = candidatos

    @property
    def pares_jugador(self):
        """(campo de selección, campo de nombre libre) para cada hueco de
        jugador — para que la plantilla los pinte juntos."""
        return [
            (self['equipo_a_companero'], self['equipo_a_companero_invitado']),
            (self['equipo_b_jugador1'], self['equipo_b_jugador1_invitado']),
            (self['equipo_b_jugador2'], self['equipo_b_jugador2_invitado']),
        ]

    def _sets_introducidos(self, cleaned):
        sets = []
        for i in (1, 2, 3):
            a = cleaned.get(f'set{i}_a')
            b = cleaned.get(f'set{i}_b')
            if a is None and b is None:
                continue
            if a is None or b is None:
                self.add_error(None, f'Faltan los juegos del set {i}.')
                continue
            es_stb = i == 3 and bool(cleaned.get('set3_es_super_tiebreak'))
            sets.append({'numero': i, 'a': a, 'b': b, 'es_super_tiebreak': es_stb})
        return sets

    def _resolver_jugador(self, cleaned, campo_usuario, campo_invitado, requerido, etiqueta):
        """('usuario', Usuario) | ('invitado', nombre) | None (slot vacío)."""
        usuario = cleaned.get(campo_usuario)
        nombre = (cleaned.get(campo_invitado) or '').strip()
        if usuario and nombre:
            self.add_error(None, f'{etiqueta}: elige un vecino con perfil o escribe un nombre, no las dos cosas.')
            return None
        if usuario:
            return ('usuario', usuario)
        if nombre:
            return ('invitado', nombre)
        if requerido:
            self.add_error(None, f'Falta {etiqueta[0].lower()}{etiqueta[1:]}.')
        return None

    def clean(self):
        cleaned = super().clean()

        companero = self._resolver_jugador(
            cleaned, 'equipo_a_companero', 'equipo_a_companero_invitado', False, 'Tu compañero'
        )
        rival1 = self._resolver_jugador(
            cleaned, 'equipo_b_jugador1', 'equipo_b_jugador1_invitado', True, 'Rival 1'
        )
        rival2 = self._resolver_jugador(
            cleaned, 'equipo_b_jugador2', 'equipo_b_jugador2_invitado', False, 'Rival 2'
        )

        equipo_a = [('usuario', self.usuario)] + ([companero] if companero else [])
        equipo_b = ([rival1] if rival1 else []) + ([rival2] if rival2 else [])

        usuarios_pks = [j[1].pk for j in equipo_a + equipo_b if j[0] == 'usuario']
        if len(usuarios_pks) != len(set(usuarios_pks)):
            self.add_error(None, 'Un jugador con perfil no puede estar en los dos equipos ni repetirse.')

        cleaned['equipo_a'] = equipo_a
        cleaned['equipo_b'] = equipo_b

        sets = self._sets_introducidos(cleaned)
        if not sets:
            self.add_error(None, 'Introduce al menos el resultado del primer set.')
        else:
            ganados_a = ganados_b = 0
            for s in sets:
                try:
                    validar_set(s['a'], s['b'], s['es_super_tiebreak'])
                except ValidationError as e:
                    self.add_error(None, f"Set {s['numero']}: {e.message}")
                    continue
                if s['a'] > s['b']:
                    ganados_a += 1
                else:
                    ganados_b += 1

            if len(sets) == 1:
                self.add_error(None, 'Hace falta ganar al menos 2 sets para completar el partido.')
            elif len(sets) == 2 and not (ganados_a == 2 or ganados_b == 2):
                self.add_error(
                    None,
                    'Con un set para cada equipo hace falta un tercer set (o súper tie-break) que decida el partido.',
                )
            elif len(sets) == 3 and {ganados_a, ganados_b} != {1, 2}:
                self.add_error(None, 'El resultado de los 3 sets no es coherente: alguien ya debería haber ganado en 2.')

        cleaned['sets'] = sets
        return cleaned

    @staticmethod
    def _crear_participante(resultado, equipo, jugador):
        tipo, valor = jugador
        if tipo == 'usuario':
            Participante.objects.create(resultado=resultado, equipo=equipo, usuario=valor)
        else:
            Participante.objects.create(resultado=resultado, equipo=equipo, nombre_invitado=valor)

    def save(self):
        with transaction.atomic():
            resultado = ResultadoPartido.objects.create(reserva=self.reserva, creado_por=self.usuario)
            for jugador in self.cleaned_data['equipo_a']:
                self._crear_participante(resultado, Participante.EQUIPO_A, jugador)
            for jugador in self.cleaned_data['equipo_b']:
                self._crear_participante(resultado, Participante.EQUIPO_B, jugador)
            for s in self.cleaned_data['sets']:
                SetResultado.objects.create(
                    resultado=resultado, numero=s['numero'],
                    juegos_equipo_a=s['a'], juegos_equipo_b=s['b'],
                    es_super_tiebreak=s['es_super_tiebreak'],
                )
        return resultado
