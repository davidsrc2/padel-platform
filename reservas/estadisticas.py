from .models import Participante, ResultadoPartido


def calcular_estadisticas(usuario, ultimos_n=10):
    """Estadísticas de un jugador a partir de sus resultados CONFIRMADOS.
    Se calcula al vuelo (sin contadores guardados) — a este volumen de datos
    es más simple y no hay riesgo de que se desincronicen; si el número de
    partidos por jugador crece mucho, valorar guardar contadores agregados."""
    resultados = list(
        ResultadoPartido.objects.filter(
            participantes__usuario=usuario,
            estado=ResultadoPartido.ESTADO_CONFIRMADO,
        )
        .distinct()
        .prefetch_related('sets', 'participantes')
        .order_by('reserva__fecha', 'reserva__hora_inicio')
    )

    ganados = perdidos = 0
    sets_ganados = sets_perdidos = 0
    juegos_ganados = juegos_perdidos = 0
    historial = []  # 'V'/'D' en orden cronológico (más antiguo primero)

    for r in resultados:
        gano = r.gano(usuario)
        if gano is None:
            continue
        en_equipo_a = any(
            p.usuario_id == usuario.pk and p.equipo == Participante.EQUIPO_A for p in r.participantes.all()
        )

        for s in r.sets.all():
            propios, rivales = (s.juegos_equipo_a, s.juegos_equipo_b) if en_equipo_a \
                else (s.juegos_equipo_b, s.juegos_equipo_a)
            juegos_ganados += propios
            juegos_perdidos += rivales
            if propios > rivales:
                sets_ganados += 1
            else:
                sets_perdidos += 1

        if gano:
            ganados += 1
            historial.append('V')
        else:
            perdidos += 1
            historial.append('D')

    jugados = ganados + perdidos

    racha_actual = 0
    if historial:
        ultimo = historial[-1]
        for resultado_h in reversed(historial):
            if resultado_h != ultimo:
                break
            racha_actual += 1
        if ultimo == 'D':
            racha_actual = -racha_actual

    mejor_racha = actual = 0
    for resultado_h in historial:
        if resultado_h == 'V':
            actual += 1
            mejor_racha = max(mejor_racha, actual)
        else:
            actual = 0

    return {
        'jugados': jugados,
        'ganados': ganados,
        'perdidos': perdidos,
        'pct_victorias': round(100 * ganados / jugados, 1) if jugados else 0,
        'sets_ganados': sets_ganados,
        'sets_perdidos': sets_perdidos,
        'diferencia_juegos': juegos_ganados - juegos_perdidos,
        'racha_actual': racha_actual,
        'mejor_racha_victorias': mejor_racha,
        'ultimos_resultados': list(reversed(historial[-ultimos_n:])),  # más reciente primero
    }
