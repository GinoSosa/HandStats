import flet as ft
import asyncio
import json
import os
from datetime import datetime


# ============================================================
# CONFIGURACIÓN Y ALMACENAMIENTO
# ============================================================

# Desde Flet 0.86, FLET_APP_STORAGE_DATA es el lugar correcto
# para guardar datos persistentes de la aplicación en Android.
APP_DATA = os.environ.get("FLET_APP_STORAGE_DATA", os.getcwd())

os.makedirs(APP_DATA, exist_ok=True)

ARCHIVO_PLANTEL = os.path.join(APP_DATA, "plantel.json")
ARCHIVO_CATEGORIAS = os.path.join(APP_DATA, "categorias.json")
ARCHIVO_ESTADISTICAS = os.path.join(APP_DATA, "estadisticas_handball.json")
ARCHIVO_PARTIDOS = os.path.join(APP_DATA, "partidos.json")


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def cargar_json(archivo, default):
    """Carga un archivo JSON. Si no existe o está corrupto,
    devuelve el valor por defecto."""
    try:
        if os.path.exists(archivo):
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    return default


def guardar_json(archivo, datos):
    """Guarda datos en JSON de forma segura."""
    try:
        carpeta = os.path.dirname(archivo)

        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        archivo_temporal = archivo + ".tmp"

        with open(archivo_temporal, "w", encoding="utf-8") as f:
            json.dump(
                datos,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(archivo_temporal, archivo)

    except OSError as error:
        print(f"Error guardando {archivo}: {error}")


def parse_time(minuto_str):
    """Convierte MM:SS a segundos."""
    try:
        partes = str(minuto_str).split(":")

        if len(partes) != 2:
            return 0

        minutos = int(partes[0])
        segundos = int(partes[1])

        return minutos * 60 + segundos

    except (ValueError, TypeError):
        return 0


def nombre_jugador(jugador):
    return f"{jugador['nombre']} (#{jugador['numero']})"


def mostrar_snackbar(page, mensaje):
    page.snack_bar = ft.SnackBar(
        content=ft.Text(mensaje)
    )
    page.snack_bar.open = True
    page.update()


# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================

def main(page: ft.Page):

    # --------------------------------------------------------
    # CONFIGURACIÓN DE PÁGINA
    # --------------------------------------------------------

    page.title = "HandStats - Analista de Handball"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.scroll = ft.ScrollMode.AUTO

    # Flet moderno utiliza ft.Button.
    def Boton(texto, **kwargs):
        return ft.Button(
            content=texto,
            **kwargs
        )

    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    plantel = cargar_json(
        ARCHIVO_PLANTEL,
        []
    )

    categorias = cargar_json(
        ARCHIVO_CATEGORIAS,
        {
            "Primera": [],
            "Juveniles": []
        }
    )

    estadisticas = cargar_json(
        ARCHIVO_ESTADISTICAS,
        []
    )

    partidos_historial = cargar_json(
        ARCHIVO_PARTIDOS,
        []
    )

    # --------------------------------------------------------
    # ESTADO DEL PARTIDO
    # --------------------------------------------------------

    estado_partido = {
        "id": None,
        "fecha": None,
        "tiempo_segundos": 0,
        "activo": False,
        "periodo": "Pre-partido",
        "categoria_actual": None,
        "rival": "",
        "cancha_activa": [],
        "banco_activo": [],
        "segundos_jugados": {}
    }

    vista_dinamica = ft.Container(
        expand=True
    )

    # ========================================================
    # PESTAÑA 1 - JUGADORES
    # ========================================================

    input_nombre = ft.TextField(
        label="Nombre y Apellido",
        width=220
    )

    input_numero = ft.TextField(
        label="Nº",
        width=90
    )

    checkbox_arquero = ft.Checkbox(
        label="¿Es Arquero?",
        value=False
    )

    lista_jugadores_view = ft.Column(
        spacing=5
    )

    def refrescar_lista_jugadores():
        lista_jugadores_view.controls.clear()

        for jugador in plantel:

            tag_arq = " 🧤 [ARQ]" if jugador.get("es_arquero") else ""

            lista_jugadores_view.controls.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            f"#{jugador['numero']} - "
                            f"{jugador['nombre']}{tag_arq}",
                            expand=True
                        ),

                        ft.TextButton(
                            "Eliminar",
                            on_click=lambda e, jug=jugador:
                                eliminar_jugador(jug)
                        )
                    ]
                )
            )

        page.update()

    def agregar_jugador(e):

        nombre = (input_nombre.value or "").strip()
        numero = (input_numero.value or "").strip()

        if not nombre or not numero:
            mostrar_snackbar(
                page,
                "Completa nombre y número."
            )
            return

        nuevo = {
            "nombre": nombre,
            "numero": numero,
            "es_arquero": bool(checkbox_arquero.value)
        }

        existe = any(
            str(j.get("numero", "")) == numero
            and str(j.get("nombre", "")).lower() == nombre.lower()
            for j in plantel
        )

        if existe:
            mostrar_snackbar(
                page,
                "Ese jugador ya está registrado."
            )
            return

        plantel.append(nuevo)

        guardar_json(
            ARCHIVO_PLANTEL,
            plantel
        )

        input_nombre.value = ""
        input_numero.value = ""
        checkbox_arquero.value = False

        refrescar_lista_jugadores()
        actualizar_pestana_categorias()
        actualizar_pestana_partidos()

    def eliminar_jugador(jugador):

        if jugador not in plantel:
            return

        plantel.remove(jugador)

        # También lo quitamos de todas las categorías.
        for categoria in categorias.values():
            while jugador in categoria:
                categoria.remove(jugador)

        guardar_json(
            ARCHIVO_PLANTEL,
            plantel
        )

        guardar_json(
            ARCHIVO_CATEGORIAS,
            categorias
        )

        refrescar_lista_jugadores()
        actualizar_pestana_categorias()

    tab_jugadores = ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text(
                    "Gestión del Plantel General",
                    size=22,
                    weight=ft.FontWeight.BOLD
                ),

                ft.Row(
                    controls=[
                        input_nombre,
                        input_numero,
                        checkbox_arquero
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True
                ),

                ft.Row(
                    controls=[
                        Boton(
                            "Agregar Jugador",
                            on_click=agregar_jugador
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),

                ft.Divider(),

                ft.Text(
                    "Jugadores Registrados:",
                    weight=ft.FontWeight.BOLD
                ),

                lista_jugadores_view
            ]
        )
    )

    # ========================================================
    # PESTAÑA 2 - CATEGORÍAS
    # ========================================================

    input_nombre_categoria = ft.TextField(
        label="Nombre Categoría",
        width=220
    )

    vista_categorias = ft.Column(
        spacing=10
    )

    def actualizar_pestana_categorias():

        vista_categorias.controls.clear()

        for categoria, jugadores_asignados in categorias.items():

            checkboxes = []

            for jugador in plantel:

                asignado = jugador in jugadores_asignados

                tag_arq = (
                    " [ARQ]"
                    if jugador.get("es_arquero")
                    else ""
                )

                checkbox = ft.Checkbox(
                    label=(
                        f"#{jugador['numero']} "
                        f"{jugador['nombre']}"
                        f"{tag_arq}"
                    ),
                    value=asignado,
                    on_change=lambda e,
                    c=categoria,
                    jug=jugador:
                        toggle_jugador_categoria(
                            c,
                            jug,
                            e.control.value
                        )
                )

                checkboxes.append(checkbox)

            encabezado = ft.Row(
                controls=[
                    ft.Text(
                        f"Categoría: {categoria}",
                        size=18,
                        weight=ft.FontWeight.BOLD
                    ),

                    ft.TextButton(
                        "Eliminar",
                        on_click=lambda e, c=categoria:
                            eliminar_categoria(c)
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )

            bloque = ft.Container(
                padding=15,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=10,
                content=ft.Column(
                    controls=[
                        encabezado,
                        ft.Column(
                            controls=checkboxes
                        )
                    ]
                )
            )

            vista_categorias.controls.append(bloque)

        page.update()

    def agregar_categoria(e):

        nombre = (
            input_nombre_categoria.value or ""
        ).strip()

        if not nombre:
            mostrar_snackbar(
                page,
                "Escribe un nombre para la categoría."
            )
            return

        if nombre in categorias:
            mostrar_snackbar(
                page,
                "Esa categoría ya existe."
            )
            return

        categorias[nombre] = []

        guardar_json(
            ARCHIVO_CATEGORIAS,
            categorias
        )

        input_nombre_categoria.value = ""

        actualizar_pestana_categorias()
        actualizar_pestana_partidos()

    def eliminar_categoria(categoria):

        if categoria not in categorias:
            return

        del categorias[categoria]

        guardar_json(
            ARCHIVO_CATEGORIAS,
            categorias
        )

        actualizar_pestana_categorias()
        actualizar_pestana_partidos()

    def toggle_jugador_categoria(
        categoria,
        jugador,
        seleccionado
    ):

        if categoria not in categorias:
            return

        if seleccionado:

            if jugador not in categorias[categoria]:
                categorias[categoria].append(jugador)

        else:

            if jugador in categorias[categoria]:
                categorias[categoria].remove(jugador)

        guardar_json(
            ARCHIVO_CATEGORIAS,
            categorias
        )

    tab_categorias = ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text(
                    "Armado de Equipos por Categoría",
                    size=22,
                    weight=ft.FontWeight.BOLD
                ),

                ft.Row(
                    controls=[
                        input_nombre_categoria,

                        Boton(
                            "Crear Categoría",
                            on_click=agregar_categoria
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True
                ),

                ft.Divider(),

                vista_categorias
            ]
        )
    )

    # ========================================================
    # PESTAÑA 3 - ESTADÍSTICAS
    # ========================================================

    dropdown_filtro_partido = ft.Dropdown(
        label="Seleccionar Partido",
        width=280
    )

    dropdown_filtro_categoria = ft.Dropdown(
        label="Filtrar por Categoría",
        width=220
    )

    dropdown_modo_vista = ft.Dropdown(
        label="Modo de Vista",
        width=220,
        options=[
            ft.DropdownOption(
                key="equipo",
                text="Tops del Equipo"
            ),
            ft.DropdownOption(
                key="individual",
                text="Análisis Individual"
            )
        ]
    )

    dropdown_jugador_stats = ft.Dropdown(
        label="Seleccionar Jugador",
        width=280,
        visible=False
    )

    panel_stats_dinamico = ft.Column(
        spacing=20
    )

    def crear_grafico_barras(
        titulo,
        datos,
        formato="numero",
        color=None
    ):

        if not datos:
            return ft.Container(
                padding=15,
                content=ft.Text(
                    f"Sin datos suficientes para: {titulo}",
                    color=ft.Colors.GREY
                )
            )

        barras = []

        datos_ordenados = sorted(
            datos.items(),
            key=lambda x: x[1],
            reverse=True
        )

        max_valor = max(
            datos.values()
        )

        if max_valor <= 0:
            max_valor = 1

        if color is None:
            color = ft.Colors.BLUE

        for nombre, valor in datos_ordenados:

            if valor == 0 and formato != "tiempo":
                continue

            if formato == "porcentaje":

                texto_valor = f"{int(valor)}%"
                ancho = (valor / 100) * 100

            elif formato == "tiempo":

                minutos, segundos = divmod(
                    int(valor),
                    60
                )

                texto_valor = (
                    f"{minutos}m "
                    f"{segundos:02d}s"
                )

                ancho = (
                    valor / max_valor
                ) * 100

            else:

                texto_valor = str(valor)

                ancho = (
                    valor / max_valor
                ) * 100

            barras.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            str(nombre)[:20],
                            width=145,
                            size=13
                        ),

                        ft.Container(
                            width=max(
                                5,
                                ancho * 1.5
                            ),
                            height=18,
                            bgcolor=color,
                            border_radius=4
                        ),

                        ft.Text(
                            texto_valor,
                            size=12,
                            weight=ft.FontWeight.BOLD
                        )
                    ]
                )
            )

        return ft.Container(
            padding=15,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
            content=ft.Column(
                controls=[
                    ft.Text(
                        titulo,
                        weight=ft.FontWeight.BOLD,
                        size=15
                    )
                ] + barras
            )
        )

    def procesar_tiro(accion):

        accion_lower = (
            str(accion)
            .lower()
            .strip()
        )

        # Las acciones de arquero rival no son tiros
        # propios.
        if "tiro rival" in accion_lower:
            return None

        if (
            "tiro" not in accion_lower
            and "penal" not in accion_lower
        ):
            return None

        if "tiro bloqueado" in accion_lower:
            return None

        es_gol = (
            "gol" in accion_lower
            and "no gol" not in accion_lower
            and "errad" not in accion_lower
            and "atajad" not in accion_lower
            and "afuera" not in accion_lower
        )

        if "penal" in accion_lower:
            distancia = "Penal"

        elif (
            "6m" in accion_lower
            or "6 metros" in accion_lower
        ):
            distancia = "6m"

        elif (
            "9m" in accion_lower
            or "9 metros" in accion_lower
        ):
            distancia = "9m"

        else:
            distancia = "N/A"

        if "extremo" in accion_lower:
            posicion = "Extremo"

        elif "centro" in accion_lower:
            posicion = "Centro"

        elif "pivote" in accion_lower:
            posicion = "Pivote"

        elif "armado" in accion_lower:
            posicion = "Armado"

        else:
            posicion = "N/A"

        return {
            "gol": es_gol,
            "distancia": distancia,
            "posicion": posicion
        }

    # --------------------------------------------------------
    # LÍNEA DE TIEMPO
    # --------------------------------------------------------

    def dibujar_linea_tiempo_partido(
        partido_id,
        eventos
    ):

        eventos_partido = sorted(
            [
                ev
                for ev in eventos
                if str(
                    ev.get("partido_id", "")
                ) == str(partido_id)
            ],
            key=lambda x:
                parse_time(
                    x.get(
                        "minuto",
                        "00:00"
                    )
                )
        )

        if not eventos_partido:
            return ft.Container()

        intervalos = {}
        max_t = 0

        for evento in eventos_partido:

            tiempo = parse_time(
                evento.get(
                    "minuto",
                    "00:00"
                )
            )

            max_t = max(
                max_t,
                tiempo
            )

            jugador = evento.get(
                "jugador",
                "Desconocido"
            )

            accion = evento.get(
                "accion",
                ""
            )

            if jugador not in intervalos:
                intervalos[jugador] = []

            if accion == "Ingresa a cancha":

                intervalos[jugador].append(
                    [tiempo, None]
                )

            elif accion == "Sale al banco":

                if (
                    intervalos[jugador]
                    and intervalos[jugador][-1][1]
                    is None
                ):
                    intervalos[jugador][-1][1] = tiempo

        for jugador in intervalos:

            if (
                intervalos[jugador]
                and intervalos[jugador][-1][1]
                is None
            ):
                intervalos[jugador][-1][1] = max_t

        filas_ui = []

        for jugador, tramos in intervalos.items():

            if not tramos:
                continue

            ultima_posicion = 0
            barras = []

            for inicio, fin in tramos:

                if fin is None:
                    fin = max_t

                if inicio > ultima_posicion:

                    barras.append(
                        ft.Container(
                            expand=max(
                                1,
                                inicio - ultima_posicion
                            ),
                            bgcolor=ft.Colors.TRANSPARENT
                        )
                    )

                duracion = max(
                    0,
                    fin - inicio
                )

                if duracion > 0:

                    barras.append(
                        ft.Container(
                            expand=duracion,
                            bgcolor=ft.Colors.GREEN_700,
                            border_radius=3,
                            tooltip=(
                                f"{inicio // 60:02d}:"
                                f"{inicio % 60:02d} a "
                                f"{fin // 60:02d}:"
                                f"{fin % 60:02d}"
                            )
                        )
                    )

                ultima_posicion = fin

            if ultima_posicion < max_t:

                barras.append(
                    ft.Container(
                        expand=max(
                            1,
                            max_t - ultima_posicion
                        ),
                        bgcolor=ft.Colors.TRANSPARENT
                    )
                )

            filas_ui.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            jugador[:18],
                            width=120,
                            size=11,
                            color=ft.Colors.GREY_300
                        ),

                        ft.Container(
                            expand=True,
                            height=15,
                            bgcolor=ft.Colors.BLACK12,
                            border_radius=3,
                            content=ft.Row(
                                controls=barras,
                                spacing=0
                            )
                        )
                    ]
                )
            )

        if not filas_ui:
            return ft.Container()

        return ft.Container(
            padding=15,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
            margin=ft.Margin.only(top=10),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Línea de Tiempo - Jugadores en Cancha",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.TEAL
                    ),

                    ft.Text(
                        "Los bloques verdes indican "
                        "cuándo el jugador estuvo en cancha.",
                        size=12,
                        color=ft.Colors.GREY
                    ),

                    ft.Column(
                        controls=filas_ui,
                        spacing=5
                    )
                ]
            )
        )

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    def actualizar_panel_estadisticas(e=None):

        panel_stats_dinamico.controls.clear()

        modo = (
            dropdown_modo_vista.value
            or "equipo"
        )

        dropdown_jugador_stats.visible = (
            modo == "individual"
        )

        filtro_partido_id = str(
            dropdown_filtro_partido.value
            or "historico"
        )

        filtro_categoria = (
            dropdown_filtro_categoria.value
        )

        if filtro_partido_id == "historico":

            eventos_filtrados = estadisticas

            partidos_filtrados = partidos_historial

        else:

            eventos_filtrados = [
                evento
                for evento in estadisticas
                if str(
                    evento.get(
                        "partido_id",
                        ""
                    )
                ) == filtro_partido_id
            ]

            partidos_filtrados = [
                partido
                for partido in partidos_historial
                if str(
                    partido.get(
                        "id",
                        ""
                    )
                ) == filtro_partido_id
            ]

        if (
            filtro_categoria
            and filtro_categoria != "Todas"
        ):

            eventos_filtrados = [
                evento
                for evento in eventos_filtrados
                if evento.get("categoria")
                == filtro_categoria
            ]

            partidos_filtrados = [
                partido
                for partido in partidos_filtrados
                if partido.get("categoria")
                == filtro_categoria
            ]

        # ====================================================
        # VISTA EQUIPO
        # ====================================================

        if modo == "equipo":

            goleadores = {}
            efectividad_raw = {}
            minutos = {}

            for partido in partidos_filtrados:

                for jugador, segundos in (
                    partido
                    .get(
                        "minutos_jugados",
                        {}
                    )
                    .items()
                ):

                    minutos[jugador] = (
                        minutos.get(
                            jugador,
                            0
                        )
                        + segundos
                    )

            for evento in eventos_filtrados:

                jugador = evento.get(
                    "jugador",
                    "Desconocido"
                )

                tiro = procesar_tiro(
                    evento.get(
                        "accion",
                        ""
                    )
                )

                if tiro is None:
                    continue

                if jugador not in efectividad_raw:
                    efectividad_raw[jugador] = [
                        0,
                        0
                    ]

                efectividad_raw[jugador][1] += 1

                if tiro["gol"]:

                    efectividad_raw[jugador][0] += 1

                    goleadores[jugador] = (
                        goleadores.get(
                            jugador,
                            0
                        )
                        + 1
                    )

            efectividad_porcentajes = {
                jugador:
                    (
                        valores[0]
                        / valores[1]
                        * 100
                    )
                for jugador, valores
                in efectividad_raw.items()
                if valores[1] > 0
            }

            panel_stats_dinamico.controls.append(
                ft.Text(
                    "Rankings del Equipo",
                    size=20,
                    weight=ft.FontWeight.BOLD
                )
            )

            panel_stats_dinamico.controls.append(
                ft.Row(
                    controls=[
                        crear_grafico_barras(
                            "🏆 Top Goleadores",
                            goleadores,
                            "numero",
                            ft.Colors.GREEN_700
                        ),

                        crear_grafico_barras(
                            "🎯 Top Efectividad %",
                            efectividad_porcentajes,
                            "porcentaje",
                            ft.Colors.BLUE_700
                        ),

                        crear_grafico_barras(
                            "⏱️ Top Minutos",
                            minutos,
                            "tiempo",
                            ft.Colors.ORANGE_700
                        )
                    ],
                    wrap=True,
                    alignment=ft.MainAxisAlignment.CENTER
                )
            )

            if filtro_partido_id != "historico":

                grafico_gantt = (
                    dibujar_linea_tiempo_partido(
                        filtro_partido_id,
                        eventos_filtrados
                    )
                )

                panel_stats_dinamico.controls.append(
                    grafico_gantt
                )

            else:

                lista_p = []

                for partido in reversed(
                    partidos_filtrados[-5:]
                ):

                    goles_nuestros = partido.get(
                        "goles_nuestros",
                        0
                    )

                    goles_rival = partido.get(
                        "goles_rival",
                        0
                    )

                    if goles_nuestros > goles_rival:
                        resultado = "🟩"

                    elif goles_nuestros < goles_rival:
                        resultado = "🟥"

                    else:
                        resultado = "🟨"

                    lista_p.append(
                        ft.Text(
                            f"{resultado} "
                            f"{partido.get('fecha', '')} | "
                            f"{partido.get('categoria', '')} | "
                            f"HandStats "
                            f"{goles_nuestros} - "
                            f"{goles_rival} "
                            f"{partido.get('rival', '')}",
                            color=ft.Colors.CYAN
                        )
                    )

                if not lista_p:
                    lista_p.append(
                        ft.Text(
                            "Todavía no hay partidos guardados.",
                            color=ft.Colors.GREY
                        )
                    )

                panel_stats_dinamico.controls.append(
                    ft.Container(
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "Últimos Resultados:",
                                    weight=ft.FontWeight.BOLD
                                )
                            ] + lista_p
                        )
                    )
                )

        # ====================================================
        # VISTA INDIVIDUAL
        # ====================================================

        elif modo == "individual":

            jugador_sel = (
                dropdown_jugador_stats.value
            )

            if not jugador_sel:

                panel_stats_dinamico.controls.append(
                    ft.Text(
                        "Selecciona un jugador arriba.",
                        color=ft.Colors.GREY
                    )
                )

            else:

                tiros_distancia = {
                    "6m": [0, 0],
                    "9m": [0, 0],
                    "Penal": [0, 0],
                    "N/A": [0, 0]
                }

                tiros_posicion = {
                    "Extremo": [0, 0],
                    "Centro": [0, 0],
                    "Pivote": [0, 0],
                    "Armado": [0, 0],
                    "N/A": [0, 0]
                }

                sanciones = {
                    "2 Minutos": 0,
                    "Amarilla": 0,
                    "Roja": 0
                }

                total_segs = 0
                partidos_jugados = 0
                segs_posibles = 0

                for partido in partidos_filtrados:

                    segundos = (
                        partido
                        .get(
                            "minutos_jugados",
                            {}
                        )
                        .get(
                            jugador_sel,
                            0
                        )
                    )

                    total_segs += segundos

                    duracion_partido = (
                        partido.get(
                            "duracion_total",
                            0
                        )
                    )

                    if (
                        duracion_partido == 0
                        and partido.get(
                            "minutos_jugados"
                        )
                    ):

                        duracion_partido = max(
                            partido
                            .get(
                                "minutos_jugados"
                            )
                            .values()
                        )

                    segs_posibles += (
                        duracion_partido
                    )

                    if segundos > 0:
                        partidos_jugados += 1

                for evento in eventos_filtrados:

                    if (
                        str(
                            evento.get(
                                "jugador",
                                ""
                            )
                        ).strip()
                        != str(
                            jugador_sel
                        ).strip()
                    ):
                        continue

                    accion = evento.get(
                        "accion",
                        ""
                    )

                    tiro = procesar_tiro(
                        accion
                    )

                    if tiro:

                        distancia = tiro[
                            "distancia"
                        ]

                        posicion = tiro[
                            "posicion"
                        ]

                        if distancia in tiros_distancia:

                            tiros_distancia[
                                distancia
                            ][1] += 1

                            if tiro["gol"]:
                                tiros_distancia[
                                    distancia
                                ][0] += 1

                        if posicion in tiros_posicion:

                            tiros_posicion[
                                posicion
                            ][1] += 1

                            if tiro["gol"]:
                                tiros_posicion[
                                    posicion
                                ][0] += 1

                    accion_lower = accion.lower()

                    if "2 minutos" in accion_lower:
                        sanciones[
                            "2 Minutos"
                        ] += 1

                    if "amarilla" in accion_lower:
                        sanciones[
                            "Amarilla"
                        ] += 1

                    if "roja" in accion_lower:
                        sanciones[
                            "Roja"
                        ] += 1

                def graf_efectividad_mini(
                    titulo,
                    datos_array
                ):

                    goles, tiros = datos_array

                    if (
                        tiros == 0
                        and (
                            "N/A"
                            in titulo
                        )
                    ):
                        return ft.Container()

                    porcentaje = (
                        int(
                            goles
                            / tiros
                            * 100
                        )
                        if tiros > 0
                        else 0
                    )

                    return ft.Column(
                        controls=[
                            ft.Text(
                                f"{titulo}: "
                                f"{porcentaje}% "
                                f"({goles}/{tiros})",
                                size=13
                            ),

                            ft.ProgressBar(
                                value=(
                                    goles / tiros
                                    if tiros > 0
                                    else 0
                                ),
                                color=ft.Colors.GREEN,
                                bgcolor=ft.Colors.RED,
                                width=150
                            )
                        ]
                    )

                total_goles = sum(
                    valor[0]
                    for valor
                    in tiros_distancia.values()
                )

                total_tiros = sum(
                    valor[1]
                    for valor
                    in tiros_distancia.values()
                )

                min_m, min_s = divmod(
                    total_segs,
                    60
                )

                pos_m, pos_s = divmod(
                    segs_posibles,
                    60
                )

                efectividad_total = (
                    int(
                        total_goles
                        / total_tiros
                        * 100
                    )
                    if total_tiros > 0
                    else 0
                )

                panel_stats_dinamico.controls.append(
                    ft.Text(
                        f"Radiografía de {jugador_sel}",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE
                    )
                )

                resumen = ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=10,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Resumen General",
                                weight=ft.FontWeight.BOLD
                            ),

                            ft.Text(
                                f"⏱ Tiempo: "
                                f"{min_m}m "
                                f"{min_s}s"
                            ),

                            ft.Text(
                                f"📊 Participación: "
                                f"{partidos_jugados} "
                                f"partido(s)"
                            ),

                            ft.Text(
                                f"⏳ Minutos posibles: "
                                f"{pos_m}m "
                                f"{pos_s}s",
                                size=12,
                                color=ft.Colors.GREY
                            ),

                            ft.Text(
                                f"🎯 Efectividad: "
                                f"{efectividad_total}% "
                                f"({total_goles}G / "
                                f"{total_tiros}T)"
                            ),

                            ft.Text(
                                f"⚠️ Sanciones: "
                                f"{sanciones['Amarilla']}🟨 | "
                                f"{sanciones['2 Minutos']}✌ | "
                                f"{sanciones['Roja']}🟥"
                            )
                        ]
                    )
                )

                por_distancia = ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=10,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Por Distancia",
                                weight=ft.FontWeight.BOLD
                            ),

                            graf_efectividad_mini(
                                "6 Metros",
                                tiros_distancia["6m"]
                            ),

                            graf_efectividad_mini(
                                "9 Metros",
                                tiros_distancia["9m"]
                            ),

                            graf_efectividad_mini(
                                "Penales",
                                tiros_distancia["Penal"]
                            ),

                            graf_efectividad_mini(
                                "Sin Distancia (N/A)",
                                tiros_distancia["N/A"]
                            )
                        ]
                    )
                )

                por_posicion = ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=10,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Por Posición",
                                weight=ft.FontWeight.BOLD
                            ),

                            graf_efectividad_mini(
                                "Extremo",
                                tiros_posicion["Extremo"]
                            ),

                            graf_efectividad_mini(
                                "Centro",
                                tiros_posicion["Centro"]
                            ),

                            graf_efectividad_mini(
                                "Pivote",
                                tiros_posicion["Pivote"]
                            ),

                            graf_efectividad_mini(
                                "Armado",
                                tiros_posicion["Armado"]
                            ),

                            graf_efectividad_mini(
                                "Sin Posición (N/A)",
                                tiros_posicion["N/A"]
                            )
                        ]
                    )
                )

                panel_stats_dinamico.controls.append(
                    ft.Row(
                        controls=[
                            resumen,
                            por_distancia,
                            por_posicion
                        ],
                        wrap=True
                    )
                )

        page.update()

    def inicializar_filtros_stats():

        opciones_categorias = [
            ft.DropdownOption(
                key="Todas",
                text="Todas"
            )
        ]

        for categoria in categorias.keys():

            opciones_categorias.append(
                ft.DropdownOption(
                    key=categoria,
                    text=categoria
                )
            )

        dropdown_filtro_categoria.options = (
            opciones_categorias
        )

        if (
            not dropdown_filtro_categoria.value
            or dropdown_filtro_categoria.value
            not in ["Todas"] + list(categorias.keys())
        ):
            dropdown_filtro_categoria.value = "Todas"

        opciones_partidos = [
            ft.DropdownOption(
                key="historico",
                text="Histórico Total"
            )
        ]

        vistos = set()

        for partido in reversed(
            partidos_historial
        ):

            partido_id = str(
                partido.get("id", "")
            )

            if partido_id in vistos:
                continue

            vistos.add(partido_id)

            opciones_partidos.append(
                ft.DropdownOption(
                    key=partido_id,
                    text=(
                        f"{partido.get('fecha', '')} "
                        f"vs "
                        f"{partido.get('rival', '')} "
                        f"("
                        f"{partido.get('categoria', '')}"
                        f")"
                    )
                )
            )

        dropdown_filtro_partido.options = (
            opciones_partidos
        )

        if not dropdown_filtro_partido.value:
            dropdown_filtro_partido.value = (
                "historico"
            )

        opciones_jugadores = []

        for jugador in plantel:

            clave = nombre_jugador(
                jugador
            )

            opciones_jugadores.append(
                ft.DropdownOption(
                    key=clave,
                    text=clave
                )
            )

        dropdown_jugador_stats.options = (
            opciones_jugadores
        )

        if not dropdown_modo_vista.value:
            dropdown_modo_vista.value = (
                "equipo"
            )

        dropdown_filtro_partido.on_select = (
            actualizar_panel_estadisticas
        )

        dropdown_filtro_categoria.on_select = (
            actualizar_panel_estadisticas
        )

        dropdown_modo_vista.on_select = (
            actualizar_panel_estadisticas
        )

        dropdown_jugador_stats.on_select = (
            actualizar_panel_estadisticas
        )

    tab_stats = ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text(
                    "Analíticas Avanzadas",
                    size=22,
                    weight=ft.FontWeight.BOLD
                ),

                ft.Row(
                    controls=[
                        dropdown_filtro_categoria,
                        dropdown_filtro_partido,
                        dropdown_modo_vista,
                        dropdown_jugador_stats
                    ],
                    wrap=True
                ),

                Boton(
                    "🔄 Aplicar Filtros",
                    on_click=actualizar_panel_estadisticas
                ),

                ft.Divider(),

                panel_stats_dinamico
            ]
        )
    )

    # ========================================================
    # PESTAÑA 4 - PARTIDO EN VIVO
    # ========================================================

    dropdown_categorias_vivo = ft.Dropdown(
        label="Seleccionar Categoría",
        width=220
    )

    input_rival = ft.TextField(
        label="Equipo Rival",
        width=220
    )

    txt_reloj = ft.Text(
        "00:00",
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.YELLOW
    )

    txt_estado_periodo = ft.Text(
        "Estado: Sin iniciar",
        size=16,
        color=ft.Colors.CYAN
    )

    view_cancha_vivo = ft.Row(
        wrap=True,
        alignment=ft.MainAxisAlignment.CENTER
    )

    view_banco_vivo = ft.Column(
        spacing=5
    )

    # --------------------------------------------------------
    # CRONÓMETRO
    # --------------------------------------------------------

    async def loop_cronometro():

        while True:

            await asyncio.sleep(1)

            if estado_partido["activo"]:

                estado_partido[
                    "tiempo_segundos"
                ] += 1

                tiempo = estado_partido[
                    "tiempo_segundos"
                ]

                txt_reloj.value = (
                    f"{tiempo // 60:02}:"
                    f"{tiempo % 60:02}"
                )

                for jugador in (
                    estado_partido[
                        "cancha_activa"
                    ]
                ):

                    clave = nombre_jugador(
                        jugador
                    )

                    estado_partido[
                        "segundos_jugados"
                    ][clave] = (
                        estado_partido[
                            "segundos_jugados"
                        ].get(
                            clave,
                            0
                        )
                        + 1
                    )

                page.update()

    page.run_task(
        loop_cronometro
    )

    # --------------------------------------------------------
    # ACTUALIZAR CATEGORÍAS DEL PARTIDO
    # --------------------------------------------------------

    def actualizar_pestana_partidos():

        dropdown_categorias_vivo.options = [
            ft.DropdownOption(
                key=categoria,
                text=categoria
            )
            for categoria
            in categorias.keys()
        ]

        page.update()

    # --------------------------------------------------------
    # REGISTRAR EVENTOS
    # --------------------------------------------------------

    def registrar_evento_cronologia(
        jugador_obj,
        accion,
        tiempo_sec=None
    ):

        if not estado_partido["id"]:
            return

        tiempo = (
            tiempo_sec
            if tiempo_sec is not None
            else estado_partido[
                "tiempo_segundos"
            ]
        )

        evento = {
            "partido_id": str(
                estado_partido["id"]
            ),

            "rival": estado_partido[
                "rival"
            ],

            "categoria": estado_partido[
                "categoria_actual"
            ],

            "periodo": estado_partido[
                "periodo"
            ],

            "minuto": (
                f"{tiempo // 60:02}:"
                f"{tiempo % 60:02}"
            ),

            "jugador": nombre_jugador(
                jugador_obj
            ),

            "accion": accion,

            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        estadisticas.append(
            evento
        )

        guardar_json(
            ARCHIVO_ESTADISTICAS,
            estadisticas
        )

    # --------------------------------------------------------
    # CREAR PARTIDO
    # --------------------------------------------------------

    def iniciar_partido_config(e):

        categoria = (
            dropdown_categorias_vivo.value
        )

        rival = (
            input_rival.value or ""
        ).strip()

        if not categoria or not rival:

            mostrar_snackbar(
                page,
                "Selecciona una categoría "
                "y escribe el rival."
            )

            return

        jugadores_categoria = (
            categorias.get(
                categoria,
                []
            )
        )

        if not jugadores_categoria:

            mostrar_snackbar(
                page,
                "La categoría no tiene jugadores asignados."
            )

            return

        estado_partido["id"] = (
            datetime.now().strftime(
                "%Y%m%d%H%M%S%f"
            )
        )

        estado_partido["fecha"] = (
            datetime.now().strftime(
                "%d/%m/%Y"
            )
        )

        estado_partido[
            "categoria_actual"
        ] = categoria

        estado_partido[
            "rival"
        ] = rival

        estado_partido[
            "banco_activo"
        ] = list(
            jugadores_categoria
        )

        estado_partido[
            "cancha_activa"
        ] = []

        estado_partido[
            "tiempo_segundos"
        ] = 0

        estado_partido[
            "activo"
        ] = False

        estado_partido[
            "periodo"
        ] = "1° Tiempo"

        estado_partido[
            "segundos_jugados"
        ] = {}

        txt_reloj.value = "00:00"

        cambiar_periodo(
            "1° Tiempo",
            False
        )

        actualizar_interfaz_partido()

        mostrar_snackbar(
            page,
            "Partido creado correctamente."
        )

    # --------------------------------------------------------
    # CAMBIAR PERIODO
    # --------------------------------------------------------

    def cambiar_periodo(
        nuevo_periodo,
        activar=False
    ):

        estado_partido[
            "periodo"
        ] = nuevo_periodo

        estado_partido[
            "activo"
        ] = activar

        if activar:

            texto = (
                f"Estado: {nuevo_periodo} "
                "(Corriendo)"
            )

        else:

            texto = (
                f"Estado: {nuevo_periodo} "
                "(Pausado)"
            )

        txt_estado_periodo.value = texto

        page.update()

    # --------------------------------------------------------
    # INICIAR RELOJ
    # --------------------------------------------------------

    def iniciar_reloj(e):

        if not estado_partido["id"]:

            mostrar_snackbar(
                page,
                "Primero crea un partido."
            )

            return

        # Primera puesta en marcha.
        if (
            estado_partido[
                "tiempo_segundos"
            ] == 0
            and not estado_partido[
                "activo"
            ]
        ):

            for jugador in (
                estado_partido[
                    "cancha_activa"
                ]
            ):

                registrar_evento_cronologia(
                    jugador,
                    "Ingresa a cancha",
                    0
                )

        if estado_partido[
            "periodo"
        ] == "Finalizado":

            mostrar_snackbar(
                page,
                "El partido ya finalizó."
            )

            return

        cambiar_periodo(
            estado_partido[
                "periodo"
            ],
            True
        )

    # --------------------------------------------------------
    # FINALIZAR PARTIDO
    # --------------------------------------------------------

    def finalizar_partido(e):

        if not estado_partido["id"]:

            mostrar_snackbar(
                page,
                "No hay ningún partido activo."
            )

            return

        partido_id = str(
            estado_partido["id"]
        )

        if any(
            str(
                partido.get("id", "")
            ) == partido_id
            for partido
            in partidos_historial
        ):

            mostrar_snackbar(
                page,
                "Este partido ya fue guardado."
            )

            return

        # Detener reloj.
        estado_partido[
            "activo"
        ] = False

        # Cerrar intervalos de jugadores
        # que todavía estén en cancha.
        for jugador in list(
            estado_partido[
                "cancha_activa"
            ]
        ):

            registrar_evento_cronologia(
                jugador,
                "Sale al banco"
            )

        # ----------------------------------------------------
        # CALCULAR MARCADOR
        # ----------------------------------------------------

        goles_nuestros = 0
        goles_rival = 0

        for evento in estadisticas:

            if str(
                evento.get(
                    "partido_id",
                    ""
                )
            ) != partido_id:
                continue

            accion = str(
                evento.get(
                    "accion",
                    ""
                )
            ).lower()

            # Gol propio.
            if (
                accion.startswith(
                    "tiro: gol"
                )
                or accion == "penal - gol"
                or accion.startswith(
                    "penal - gol"
                )
            ):

                goles_nuestros += 1

            # Gol rival.
            if (
                "tiro rival: hecho"
                in accion
            ):

                goles_rival += 1

        resumen_partido = {

            "id": estado_partido[
                "id"
            ],

            "fecha": estado_partido[
                "fecha"
            ],

            "categoria": estado_partido[
                "categoria_actual"
            ],

            "rival": estado_partido[
                "rival"
            ],

            "goles_nuestros":
                goles_nuestros,

            "goles_rival":
                goles_rival,

            "minutos_jugados":
                estado_partido[
                    "segundos_jugados"
                ],

            "duracion_total":
                estado_partido[
                    "tiempo_segundos"
                ]
        }

        partidos_historial.append(
            resumen_partido
        )

        guardar_json(
            ARCHIVO_PARTIDOS,
            partidos_historial
        )

        # Limpiar estado.
        estado_partido[
            "id"
        ] = None

        estado_partido[
            "fecha"
        ] = None

        estado_partido[
            "activo"
        ] = False

        estado_partido[
            "periodo"
        ] = "Finalizado"

        mostrar_snackbar(
            page,
            "¡Partido finalizado y guardado con éxito!"
        )

        actualizar_interfaz_partido()

    # --------------------------------------------------------
    # ACTUALIZAR INTERFAZ DEL PARTIDO
    # --------------------------------------------------------

    def actualizar_interfaz_partido():

        view_cancha_vivo.controls.clear()
        view_banco_vivo.controls.clear()

        # ----------------------------
        # CANCHA
        # ----------------------------

        for jugador in (
            estado_partido[
                "cancha_activa"
            ]
        ):

            if jugador.get(
                "es_arquero",
                False
            ):

                color_btn = (
                    ft.Colors.GREEN_700
                )

            else:

                color_btn = (
                    ft.Colors.BLUE_700
                )

            view_cancha_vivo.controls.append(
                ft.Column(
                    horizontal_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),
                    controls=[
                        Boton(
                            nombre_jugador(
                                jugador
                            ),
                            width=120,
                            height=80,
                            bgcolor=color_btn,
                            on_click=lambda e,
                            jug=jugador:
                                abrir_menu_accion_vivo(
                                    jug
                                )
                        ),

                        ft.TextButton(
                            "⬇ Al Banco",
                            on_click=lambda e,
                            jug=jugador:
                                mover_a_banco(
                                    jug
                                )
                        )
                    ]
                )
            )

        # ----------------------------
        # BANCO
        # ----------------------------

        for jugador in (
            estado_partido[
                "banco_activo"
            ]
        ):

            tag_arq = (
                " 🧤"
                if jugador.get(
                    "es_arquero",
                    False
                )
                else ""
            )

            view_banco_vivo.controls.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            f"{jugador['nombre']} "
                            f"(#{jugador['numero']})"
                            f"{tag_arq}",
                            width=180
                        ),

                        Boton(
                            "⬆ A Cancha",
                            on_click=lambda e,
                            jug=jugador:
                                mover_a_cancha(
                                    jug
                                )
                        )
                    ]
                )
            )

        page.update()

    # --------------------------------------------------------
    # CAMBIAR JUGADOR A BANCO
    # --------------------------------------------------------

    def mover_a_banco(jugador):

        if jugador not in (
            estado_partido[
                "cancha_activa"
            ]
        ):
            return

        estado_partido[
            "cancha_activa"
        ].remove(jugador)

        estado_partido[
            "banco_activo"
        ].append(jugador)

        # Registrar solamente si el partido ya
        # comenzó.
        if (
            estado_partido[
                "tiempo_segundos"
            ] > 0
        ):

            registrar_evento_cronologia(
                jugador,
                "Sale al banco"
            )

        actualizar_interfaz_partido()

    # --------------------------------------------------------
    # CAMBIAR JUGADOR A CANCHA
    # --------------------------------------------------------

    def mover_a_cancha(jugador):

        if len(
            estado_partido[
                "cancha_activa"
            ]
        ) >= 7:

            mostrar_snackbar(
                page,
                "Ya hay 7 jugadores en cancha."
            )

            return

        if jugador not in (
            estado_partido[
                "banco_activo"
            ]
        ):
            return

        estado_partido[
            "banco_activo"
        ].remove(jugador)

        estado_partido[
            "cancha_activa"
        ].append(jugador)

        if (
            estado_partido[
                "id"
            ]
            and (
                estado_partido[
                    "tiempo_segundos"
                ] > 0
            )
        ):

            registrar_evento_cronologia(
                jugador,
                "Ingresa a cancha"
            )

        actualizar_interfaz_partido()

    # ========================================================
    # MENÚ DE ACCIONES
    # ========================================================

    panel_content_vivo = ft.Column(
        horizontal_alignment=(
            ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.MainAxisAlignment.CENTER
    )

    bottom_sheet_vivo = ft.BottomSheet(
        scrollable=True,
        show_drag_handle=True,
        content=ft.Container(
            padding=30,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=panel_content_vivo
        )
    )

    def cerrar_panel_vivo():

        try:
            page.pop_dialog()
        except Exception:
            pass

    def registrar_evento_vivo(
        accion_texto,
        jugador_obj
    ):

        if not estado_partido["id"]:

            mostrar_snackbar(
                page,
                "Inicia un partido primero."
            )

            return

        registrar_evento_cronologia(
            jugador_obj,
            accion_texto
        )

        cerrar_panel_vivo()

        mostrar_snackbar(
            page,
            f"Registrado: {accion_texto}"
        )

    def render_menu_vivo(
        titulo,
        opciones,
        jugador_obj
    ):

        botones = []

        for texto, funcion in opciones:

            botones.append(
                Boton(
                    texto,
                    on_click=lambda e,
                    fn=funcion:
                        fn(jugador_obj)
                )
            )

        panel_content_vivo.controls = [

            ft.Text(
                f"{titulo} - "
                f"{nombre_jugador(jugador_obj)}",
                size=18,
                weight=ft.FontWeight.BOLD
            ),

            ft.Row(
                controls=botones,
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True
            ),

            Boton(
                "❌ Cancelar",
                on_click=lambda e:
                    cerrar_panel_vivo()
            )
        ]

        try:
            page.show_dialog(
                bottom_sheet_vivo
            )
        except Exception:

            bottom_sheet_vivo.open = True
            page.update()

    # ========================================================
    # FLUJO DE TIROS PROPIOS
    # ========================================================

    def flujo_tiro_posicion(
        resultado_parcial,
        jugador_obj
    ):

        opciones = [

            (
                "Extremo",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro: "
                        f"{resultado_parcial} "
                        f"- Extremo",
                        j
                    )
            ),

            (
                "Centro",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro: "
                        f"{resultado_parcial} "
                        f"- Centro",
                        j
                    )
            ),

            (
                "Pivote",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro: "
                        f"{resultado_parcial} "
                        f"- Pivote",
                        j
                    )
            ),

            (
                "Armado",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro: "
                        f"{resultado_parcial} "
                        f"- Armado",
                        j
                    )
            )
        ]

        render_menu_vivo(
            "Posición del Tiro",
            opciones,
            jugador_obj
        )

    def flujo_tiro_distancia(
        resultado_base,
        jugador_obj
    ):

        opciones = [

            (
                "6 metros (de contra)",
                lambda j:
                    flujo_tiro_posicion(
                        f"{resultado_base} "
                        f"- 6m (Contra)",
                        j
                    )
            ),

            (
                "9 metros",
                lambda j:
                    flujo_tiro_posicion(
                        f"{resultado_base} - 9m",
                        j
                    )
            )
        ]

        render_menu_vivo(
            "Distancia",
            opciones,
            jugador_obj
        )

    def flujo_tiro_nogol_motivo(
        jugador_obj
    ):

        opciones = [

            (
                "Piso línea",
                lambda j:
                    flujo_tiro_distancia(
                        "No Gol - Piso línea",
                        j
                    )
            ),

            (
                "Falta ataque",
                lambda j:
                    flujo_tiro_distancia(
                        "No Gol - Falta en ataque",
                        j
                    )
            ),

            (
                "Erró",
                lambda j:
                    flujo_tiro_distancia(
                        "No Gol - Erró",
                        j
                    )
            ),

            (
                "Atajó arquero",
                lambda j:
                    flujo_tiro_distancia(
                        "No Gol - Atajó",
                        j
                    )
            )
        ]

        render_menu_vivo(
            "Motivo No Gol",
            opciones,
            jugador_obj
        )

    def flujo_tiro(
        jugador_obj
    ):

        opciones = [

            (
                "Gol",
                lambda j:
                    flujo_tiro_distancia(
                        "Gol",
                        j
                    )
            ),

            (
                "No Gol",
                lambda j:
                    flujo_tiro_nogol_motivo(
                        j
                    )
            )
        ]

        render_menu_vivo(
            "Resultado del Tiro",
            opciones,
            jugador_obj
        )

    # ========================================================
    # FLUJO DE TIROS RIVALES
    # ========================================================

    def flujo_arq_posicion(
        resultado_parcial,
        jugador_obj
    ):

        opciones = [

            (
                "Central",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro Rival: "
                        f"{resultado_parcial} "
                        f"- Central",
                        j
                    )
            ),

            (
                "Armado",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro Rival: "
                        f"{resultado_parcial} "
                        f"- Armado",
                        j
                    )
            ),

            (
                "Extremo",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro Rival: "
                        f"{resultado_parcial} "
                        f"- Extremo",
                        j
                    )
            ),

            (
                "Pivote",
                lambda j:
                    registrar_evento_vivo(
                        f"Tiro Rival: "
                        f"{resultado_parcial} "
                        f"- Pivote",
                        j
                    )
            )
        ]

        render_menu_vivo(
            "Lanzador Rival",
            opciones,
            jugador_obj
        )

    def flujo_arq_distancia(
        resultado,
        jugador_obj
    ):

        opciones = [

            (
                "Contra",
                lambda j:
                    flujo_arq_posicion(
                        f"{resultado} - Contra",
                        j
                    )
            ),

            (
                "6 metros",
                lambda j:
                    flujo_arq_posicion(
                        f"{resultado} - 6m",
                        j
                    )
            ),

            (
                "9 metros",
                lambda j:
                    flujo_arq_posicion(
                        f"{resultado} - 9m",
                        j
                    )
            ),

            (
                "Penal",
                lambda j:
                    flujo_arq_posicion(
                        f"{resultado} - Penal",
                        j
                    )
            )
        ]

        render_menu_vivo(
            "Distancia Rival",
            opciones,
            jugador_obj
        )

    # ========================================================
    # MENÚ PRINCIPAL DE ACCIONES
    # ========================================================

    def abrir_menu_accion_vivo(
        jugador_obj
    ):

        if not estado_partido["id"]:

            mostrar_snackbar(
                page,
                "Primero crea un partido."
            )

            return

        # ----------------------------------------------------
        # ARQUERO
        # ----------------------------------------------------

        if jugador_obj.get(
            "es_arquero",
            False
        ):

            opciones = [

                (
                    "Atajado",
                    lambda j:
                        flujo_arq_distancia(
                            "Atajado",
                            j
                        )
                ),

                (
                    "Hecho (Gol)",
                    lambda j:
                        flujo_arq_distancia(
                            "Hecho",
                            j
                        )
                )
            ]

            render_menu_vivo(
                "Tiro Rival",
                opciones,
                jugador_obj
            )

        # ----------------------------------------------------
        # JUGADOR DE CAMPO
        # ----------------------------------------------------

        else:

            opciones = [

                (
                    "Tiro",
                    flujo_tiro
                ),

                (
                    "Pérdida balón",
                    lambda j:
                        render_menu_vivo(
                            "Tipo Pérdida",
                            [

                                (
                                    "Pase",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Pérdida - Pase",
                                            x
                                        )
                                ),

                                (
                                    "Dribbling",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Pérdida - Dribbling",
                                            x
                                        )
                                )
                            ],
                            j
                        )
                ),

                (
                    "Amonestación",
                    lambda j:
                        render_menu_vivo(
                            "Sanción",
                            [

                                (
                                    "2 min",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Sanción - 2 Minutos",
                                            x
                                        )
                                ),

                                (
                                    "Amarilla",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Sanción - Amarilla",
                                            x
                                        )
                                ),

                                (
                                    "Roja",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Sanción - Roja",
                                            x
                                        )
                                )
                            ],
                            j
                        )
                ),

                (
                    "Penal a favor",
                    lambda j:
                        render_menu_vivo(
                            "Penal",
                            [

                                (
                                    "Gol",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Penal - Gol",
                                            x
                                        )
                                ),

                                (
                                    "Atajada",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Penal - Atajada",
                                            x
                                        )
                                ),

                                (
                                    "Errada",
                                    lambda x:
                                        registrar_evento_vivo(
                                            "Penal - Errada",
                                            x
                                        )
                                )
                            ],
                            j
                        )
                ),

                (
                    "Tiro bloqueado",
                    lambda j:
                        registrar_evento_vivo(
                            "Tiro bloqueado",
                            j
                        )
                )
            ]

            render_menu_vivo(
                "Acción de Jugador",
                opciones,
                jugador_obj
            )

    # ========================================================
    # CONTROLES DE PERIODO
    # ========================================================

    def terminar_primer_tiempo(e):

        if not estado_partido["id"]:
            return

        cambiar_periodo(
            "Entretiempo",
            False
        )

    def iniciar_segundo_tiempo(e):

        if not estado_partido["id"]:
            mostrar_snackbar(
                page,
                "Primero crea un partido."
            )
            return

        cambiar_periodo(
            "2° Tiempo",
            True
        )

    def pausar_partido(e):

        if not estado_partido["id"]:
            return

        cambiar_periodo(
            estado_partido[
                "periodo"
            ],
            False
        )

    # ========================================================
    # INTERFAZ PARTIDO
    # ========================================================

    tab_partidos = ft.Container(
        padding=20,
        content=ft.Column(
            controls=[

                ft.Text(
                    "Modo Partido (En Vivo)",
                    size=22,
                    weight=ft.FontWeight.BOLD
                ),

                ft.Row(
                    controls=[
                        dropdown_categorias_vivo,
                        input_rival,

                        Boton(
                            "Crear Partido",
                            on_click=iniciar_partido_config
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True
                ),

                ft.Divider(),

                txt_estado_periodo,

                ft.Row(
                    controls=[
                        txt_reloj,

                        Boton(
                            "▶ Play",
                            on_click=iniciar_reloj,
                            bgcolor=ft.Colors.GREEN_700
                        ),

                        Boton(
                            "⏸ Pausar",
                            on_click=pausar_partido,
                            bgcolor=ft.Colors.ORANGE_700
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True
                ),

                ft.Row(
                    controls=[
                        Boton(
                            "🏁 Terminar 1° Tiempo",
                            on_click=terminar_primer_tiempo,
                            bgcolor=ft.Colors.BLUE_GREY_700
                        ),

                        Boton(
                            "▶ Iniciar 2° Tiempo",
                            on_click=iniciar_segundo_tiempo,
                            bgcolor=ft.Colors.TEAL_700
                        ),

                        Boton(
                            "🛑 Guardar Partido",
                            on_click=finalizar_partido,
                            bgcolor=ft.Colors.RED_700
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True
                ),

                ft.Divider(),

                ft.Text(
                    "7 en Cancha",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE
                ),

                view_cancha_vivo,

                ft.Divider(),

                ft.Text(
                    "Banco",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY
                ),

                view_banco_vivo
            ]
        )
    )

    # ========================================================
    # NAVEGACIÓN
    # ========================================================

    def cambiar_vista(vista):

        vista_dinamica.content = vista

        if vista == tab_stats:

            inicializar_filtros_stats()

            actualizar_panel_estadisticas()

        page.update()

    barra_navegacion = ft.Row(
        controls=[

            Boton(
                "1. Jugadores",
                on_click=lambda e:
                    cambiar_vista(
                        tab_jugadores
                    )
            ),

            Boton(
                "2. Categorías",
                on_click=lambda e:
                    cambiar_vista(
                        tab_categorias
                    )
            ),

            Boton(
                "3. Estadísticas",
                on_click=lambda e:
                    cambiar_vista(
                        tab_stats
                    )
            ),

            Boton(
                "4. En Vivo",
                on_click=lambda e:
                    cambiar_vista(
                        tab_partidos
                    )
            )
        ],

        alignment=ft.MainAxisAlignment.CENTER,
        wrap=True
    )

    # ========================================================
    # INICIALIZACIÓN
    # ========================================================

    refrescar_lista_jugadores()

    actualizar_pestana_categorias()

    actualizar_pestana_partidos()

    cambiar_vista(
        tab_jugadores
    )

    page.add(
        barra_navegacion,
        ft.Divider(),
        vista_dinamica
    )


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    ft.run(main)