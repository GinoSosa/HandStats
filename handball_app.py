import flet as ft
import asyncio
import json
import os
from datetime import datetime

# Archivos JSON para persistencia
ARCHIVO_PLANTEL = "plantel.json"
ARCHIVO_CATEGORIAS = "categorias.json"
ARCHIVO_ESTADISTICAS = "estadisticas_handball.json"
ARCHIVO_PARTIDOS = "partidos.json"

def cargar_json(archivo, default):
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return default
    return default

def guardar_json(archivo, datos):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def parse_time(minuto_str):
    try:
        m, s = map(int, minuto_str.split(":"))
        return m * 60 + s
    except:
        return 0

def main(page: ft.Page):
    page.title = "Handball Stats Pro - Salsipuedes"
    page.theme_mode = "dark"
    page.vertical_alignment = "start"
    page.scroll = "auto"

    Boton = getattr(ft, "Button", ft.ElevatedButton)

    plantel = cargar_json(ARCHIVO_PLANTEL, [])
    categorias = cargar_json(ARCHIVO_CATEGORIAS, {"Primera": [], "Juveniles": []})
    estadisticas = cargar_json(ARCHIVO_ESTADISTICAS, [])
    partidos_historial = cargar_json(ARCHIVO_PARTIDOS, [])

    estado_partido = {
        "id": None, "fecha": None, "tiempo_segundos": 0, "activo": False,
        "periodo": "Pre-partido", "categoria_actual": None, "rival": "",
        "cancha_activa": [], "banco_activo": [], "segundos_jugados": {}
    }

    vista_dinamica = ft.Container(expand=True)

    # ==========================================
    # PESTAÑA 1: CARGA DE JUGADORES
    # ==========================================
    input_nombre = ft.TextField(label="Nombre y Apellido", width=200)
    input_numero = ft.TextField(label="Nº", width=80)
    checkbox_arquero = ft.Checkbox(label="¿Es Arquero?", value=False)
    lista_jugadores_view = ft.Column()

    def refrescar_lista_jugadores():
        lista_jugadores_view.controls.clear()
        for j in plantel:
            tag_arq = " 🧤 [ARQ]" if j.get("es_arquero") else ""
            lista_jugadores_view.controls.append(
                ft.Row([
                    ft.Text(f"#{j['numero']} - {j['nombre']}{tag_arq}", width=250),
                    ft.TextButton("Eliminar", on_click=lambda e, jug=j: eliminar_jugador(jug), style=ft.ButtonStyle(color="red"))
                ])
            )
        page.update()

    def agregar_jugador(e):
        if not input_nombre.value or not input_numero.value: return
        nuevo = {"nombre": input_nombre.value.strip(), "numero": input_numero.value.strip(), "es_arquero": checkbox_arquero.value}
        if any(j['numero'] == nuevo['numero'] and j['nombre'].lower() == nuevo['nombre'].lower() for j in plantel):
            page.snack_bar = ft.SnackBar(content=ft.Text("Ese jugador ya está registrado con ese número."))
            page.snack_bar.open = True
            page.update()
            return
        plantel.append(nuevo)
        guardar_json(ARCHIVO_PLANTEL, plantel)
        input_nombre.value = ""
        input_numero.value = ""
        checkbox_arquero.value = False
        refrescar_lista_jugadores()
        actualizar_pestana_categorias()

    def eliminar_jugador(j):
        if j in plantel:
            plantel.remove(j)
            guardar_json(ARCHIVO_PLANTEL, plantel)
            refrescar_lista_jugadores()
            actualizar_pestana_categorias()

    tab_jugadores = ft.Container(
        content=ft.Column([
            ft.Text("Gestión del Plantel General", size=20, weight="bold"),
            ft.Row([input_nombre, input_numero, checkbox_arquero], alignment="center"),
            ft.Row([Boton("Agregar Jugador", on_click=agregar_jugador)], alignment="center"),
            ft.Divider(), ft.Text("Jugadores Registrados:", weight="bold"), lista_jugadores_view
        ]), padding=20
    )

    # ==========================================
    # PESTAÑA 2: CATEGORÍAS
    # ==========================================
    input_nombre_categoria = ft.TextField(label="Nombre Categoría", width=200)
    vista_categorias = ft.Column()

    def actualizar_pestana_categorias():
        vista_categorias.controls.clear()
        for cat, jugadores_asignados in categorias.items():
            checkboxes = []
            for j in plantel:
                asignado = j in jugadores_asignados
                tag_arq = " [ARQ]" if j.get("es_arquero") else ""
                cb = ft.Checkbox(label=f"#{j['numero']} {j['nombre']}{tag_arq}", value=asignado, on_change=lambda e, c=cat, jug=j: toggle_jugador_categoria(c, jug, e.control.value))
                checkboxes.append(cb)
            vista_categorias.controls.append(ft.Container(content=ft.Column([
                ft.Row([ft.Text(f"Categoría: {cat}", size=18, weight="bold", color="blue"), ft.TextButton("Eliminar", on_click=lambda e, c=cat: eliminar_categoria(c), style=ft.ButtonStyle(color="red"))], alignment="spaceBetween" if hasattr(ft.Row, "alignment") else "center"),
                ft.Column(checkboxes)
            ]), padding=15, bgcolor="surfaceVariant", border_radius=10, margin=5))
        page.update()

    def agregar_categoria(e):
        nombre = input_nombre_categoria.value.strip()
        if nombre and nombre not in categorias:
            categorias[nombre] = []
            guardar_json(ARCHIVO_CATEGORIAS, categorias)
            input_nombre_categoria.value = ""
            actualizar_pestana_categorias()

    def eliminar_categoria(cat):
        if cat in categorias:
            del categorias[cat]
            guardar_json(ARCHIVO_CATEGORIAS, categorias)
            actualizar_pestana_categorias()

    def toggle_jugador_categoria(cat, jugador, seleccionado):
        if seleccionado:
            if jugador not in categorias[cat]: categorias[cat].append(jugador)
        else:
            if jugador in categorias[cat]: categorias[cat].remove(jugador)
        guardar_json(ARCHIVO_CATEGORIAS, categorias)

    tab_categorias = ft.Container(
        content=ft.Column([
            ft.Text("Armado de Equipos por Categoría", size=20, weight="bold"),
            ft.Row([input_nombre_categoria, Boton("Crear Categoría", on_click=agregar_categoria)], alignment="center"),
            ft.Divider(), vista_categorias
        ]), padding=20
    )

    # ==========================================
    # PESTAÑA 3: ESTADÍSTICAS AVANZADAS
    # ==========================================
    dropdown_filtro_partido = ft.Dropdown(label="Seleccionar Partido", width=250)
    dropdown_filtro_categoria = ft.Dropdown(label="Filtrar por Categoría", width=200)
    dropdown_modo_vista = ft.Dropdown(label="Modo de Vista", width=200, options=[
        ft.dropdown.Option(key="equipo", text="Tops del Equipo"), 
        ft.dropdown.Option(key="individual", text="Análisis Individual")
    ])
    dropdown_jugador_stats = ft.Dropdown(label="Seleccionar Jugador", width=250, visible=False)
    
    panel_stats_dinamico = ft.Column(spacing=20)

    def crear_grafico_barras(titulo, datos, formato="numero", color="blue"):
        barras = []
        if not datos: return ft.Text(f"Sin datos suficientes para: {titulo}", color="grey", size=12)
        datos_ordenados = sorted(datos.items(), key=lambda x: x[1], reverse=True)
        max_valor = max(datos.values()) if datos.values() else 1
        if max_valor == 0: max_valor = 1
        for k, v in datos_ordenados:
            if v == 0 and formato != "tiempo": continue
            if formato == "porcentaje": txt_val, ancho = f"{int(v)}%", v
            elif formato == "tiempo":
                m, s = divmod(v, 60); txt_val, ancho = f"{m}m {s:02d}s", (v / max_valor) * 100
            else: txt_val, ancho = str(v), (v / max_valor) * 100
            barras.append(ft.Row([
                ft.Text(k[:18], width=140, size=13),
                ft.Container(width=max(1, ancho * 1.5), height=18, bgcolor=color, border_radius=4),
                ft.Text(txt_val, size=12, weight="bold")
            ]))
        return ft.Container(content=ft.Column([ft.Text(titulo, weight="bold", size=15)] + barras), padding=15, bgcolor="surfaceVariant", border_radius=10)

    def procesar_tiro(accion):
        acc = accion.lower()
        if "tiro" not in acc and "penal" not in acc: return None
        if "rival" in acc or "bloquead" in acc: return None
        is_gol = "gol" in acc and "no gol" not in acc and "errad" not in acc and "atajad" not in acc and "afuera" not in acc
        d = "Penal" if "penal" in acc else ("6m" if "6m" in acc or "6 metros" in acc else ("9m" if "9m" in acc or "9 metros" in acc else "N/A"))
        p = "Extremo" if "extremo" in acc else ("Centro" if "centro" in acc else ("Pivote" if "pivote" in acc else ("Armado" if "armad" in acc else "N/A")))
        return {"gol": is_gol, "distancia": d, "posicion": p}

    def dibujar_linea_tiempo_partido(partido_id, eventos):
        eventos_partido = sorted([ev for ev in eventos if str(ev.get("partido_id")) == str(partido_id)], key=lambda x: parse_time(x.get("minuto", "00:00")))
        if not eventos_partido: return ft.Container()

        intervalos = {}
        max_t = 0
        for ev in eventos_partido:
            t = parse_time(ev.get("minuto", "00:00"))
            if t > max_t: max_t = t
            jug = ev.get("jugador", "Desconocido")
            accion = ev.get("accion", "")
            
            if jug not in intervalos: intervalos[jug] = []
            
            if accion == "Ingresa a cancha":
                intervalos[jug].append([t, None])
            elif accion == "Sale al banco":
                if intervalos[jug] and intervalos[jug][-1][1] is None:
                    intervalos[jug][-1][1] = t
        
        for jug in intervalos:
            if intervalos[jug] and intervalos[jug][-1][1] is None:
                intervalos[jug][-1][1] = max_t
        
        filas_ui = []
        for jug, tramos in intervalos.items():
            if not tramos: continue
            last_t = 0
            bars = []
            for start, end in tramos:
                if start > last_t:
                    bars.append(ft.Container(expand=max(1, start - last_t), bgcolor=ft.colors.TRANSPARENT))
                duracion = end - start
                if duracion > 0:
                    bars.append(ft.Container(expand=duracion, bgcolor="green700", border_radius=3, tooltip=f"{start//60:02d}:{start%60:02d} a {end//60:02d}:{end%60:02d}"))
                last_t = end
            if last_t < max_t:
                bars.append(ft.Container(expand=max(1, max_t - last_t), bgcolor=ft.colors.TRANSPARENT))
            
            filas_ui.append(ft.Row([
                ft.Text(jug[:15], width=110, size=11, color="grey300"),
                ft.Container(content=ft.Row(bars, spacing=0), expand=True, height=15, bgcolor="black12", border_radius=3)
            ]))
        
        if not filas_ui: return ft.Container()
        return ft.Container(content=ft.Column([
            ft.Text("Línea de Tiempo - Jugadores en Cancha", size=16, weight="bold", color="teal"),
            ft.Text("Los bloques verdes indican los minutos en los que el jugador estuvo activamente en el campo.", size=12, color="grey"),
            ft.Column(filas_ui, spacing=5)
        ]), padding=15, bgcolor="surfaceVariant", border_radius=10, margin=ft.margin.only(top=10))

    def actualizar_panel_estadisticas(e=None):
        panel_stats_dinamico.controls.clear()
        
        modo = dropdown_modo_vista.value or "equipo"
        dropdown_jugador_stats.visible = (modo == "individual")
        
        filtro_partido_id = str(dropdown_filtro_partido.value or "historico")
        filtro_categoria = dropdown_filtro_categoria.value
        
        eventos_filtrados = estadisticas if filtro_partido_id == "historico" else [ev for ev in estadisticas if str(ev.get("partido_id", "")) == filtro_partido_id]
        partidos_filtrados = partidos_historial if filtro_partido_id == "historico" else [p for p in partidos_historial if str(p.get("id", "")) == filtro_partido_id]
        
        if filtro_categoria and filtro_categoria != "Todas":
            eventos_filtrados = [ev for ev in eventos_filtrados if ev.get("categoria") == filtro_categoria]
            partidos_filtrados = [p for p in partidos_filtrados if p.get("categoria") == filtro_categoria]
        
        if modo == "equipo":
            goleadores, efectividad_raw, minutos = {}, {}, {}
            for p in partidos_filtrados:
                for j_nombre, segs in p.get("minutos_jugados", {}).items():
                    minutos[j_nombre] = minutos.get(j_nombre, 0) + segs
                    
            for ev in eventos_filtrados:
                jug = ev.get("jugador", "Desconocido")
                tiro = procesar_tiro(ev.get("accion", ""))
                if tiro:
                    if jug not in efectividad_raw: efectividad_raw[jug] = [0, 0]
                    efectividad_raw[jug][1] += 1 
                    if tiro["gol"]: 
                        efectividad_raw[jug][0] += 1 
                        goleadores[jug] = goleadores.get(jug, 0) + 1
            
            efectividad_porcentajes = {k: (v[0]/v[1]*100) for k, v in efectividad_raw.items() if v[1] > 0}
            
            panel_stats_dinamico.controls.append(ft.Text("Rankings del Equipo", size=18, weight="bold"))
            panel_stats_dinamico.controls.append(ft.Row([
                crear_grafico_barras("🏆 Top Goleadores", goleadores, "numero", "green700"),
                crear_grafico_barras("🎯 Top Efectividad %", efectividad_porcentajes, "porcentaje", "blue700"),
                crear_grafico_barras("⏱️ Top Minutos", minutos, "tiempo", "orange700")
            ], wrap=True, alignment="center"))
            
            if filtro_partido_id != "historico":
                grafico_gantt = dibujar_linea_tiempo_partido(filtro_partido_id, eventos_filtrados)
                panel_stats_dinamico.controls.append(grafico_gantt)
            else:
                lista_p = []
                for p in reversed(partidos_filtrados[-5:]):
                    res = "🟩" if p['goles_nuestros'] > p['goles_rival'] else ("🟥" if p['goles_nuestros'] < p['goles_rival'] else "🟨")
                    lista_p.append(ft.Text(f"{res} {p['fecha']} | {p['categoria']} | Salsipuedes {p['goles_nuestros']} - {p['goles_rival']} {p['rival']}", color="cyan"))
                panel_stats_dinamico.controls.append(ft.Container(content=ft.Column([ft.Text("Últimos Resultados:", weight="bold")] + lista_p), padding=10, bgcolor="surfaceVariant"))

        elif modo == "individual":
            jugador_sel = dropdown_jugador_stats.value
            if not jugador_sel:
                panel_stats_dinamico.controls.append(ft.Text("Selecciona un jugador arriba.", color="grey"))
            else:
                tiros_distancia = {"6m": [0,0], "9m": [0,0], "Penal": [0,0], "N/A": [0,0]} 
                tiros_posicion = {"Extremo": [0,0], "Centro": [0,0], "Pivote": [0,0], "Armado": [0,0], "N/A": [0,0]}
                sanciones = {"2 Minutos": 0, "Amarilla": 0, "Roja": 0}
                
                # Nuevas variables de tiempos
                total_segs = 0
                partidos_jugados = 0
                segs_posibles = 0
                
                for p in partidos_filtrados:
                    # Extraer el tiempo jugado del jugador en este partido
                    segs = p.get("minutos_jugados", {}).get(jugador_sel, 0)
                    total_segs += segs
                    
                    # Extraer duración total del partido (si es viejo y no lo tiene, adivina por el máximo)
                    duracion_partido = p.get("duracion_total", 0)
                    if duracion_partido == 0 and p.get("minutos_jugados"):
                        duracion_partido = max(p.get("minutos_jugados").values())
                    
                    segs_posibles += duracion_partido
                    
                    if segs > 0:
                        partidos_jugados += 1
                
                for ev in eventos_filtrados:
                    if str(ev.get("jugador")).strip() != str(jugador_sel).strip(): continue
                    accion = ev.get("accion", "")
                    tiro = procesar_tiro(accion)
                    
                    if tiro:
                        d, p = tiro["distancia"], tiro["posicion"]
                        if d in tiros_distancia: 
                            tiros_distancia[d][1] += 1
                            if tiro["gol"]: tiros_distancia[d][0] += 1
                        if p in tiros_posicion:
                            tiros_posicion[p][1] += 1
                            if tiro["gol"]: tiros_posicion[p][0] += 1
                            
                    for s in sanciones.keys():
                        if s.lower() in accion.lower(): sanciones[s] += 1
                
                def graf_efectividad_mini(titulo, datos_array):
                    goles, tiros = datos_array
                    if tiros == 0 and titulo == "Sin Distancia (N/A)": return ft.Container()
                    if tiros == 0 and titulo == "Sin Posición (N/A)": return ft.Container()
                    pct = int((goles/tiros*100)) if tiros > 0 else 0
                    return ft.Column([
                        ft.Text(f"{titulo}: {pct}% ({goles}/{tiros})", size=13),
                        ft.ProgressBar(value=goles/tiros if tiros>0 else 0, color="green", bgcolor="red", width=150)
                    ])

                tot_goles, tot_tiros = sum(v[0] for v in tiros_distancia.values()), sum(v[1] for v in tiros_distancia.values())
                
                min_m, min_s = divmod(total_segs, 60)
                pos_m, pos_s = divmod(segs_posibles, 60)
                
                panel_stats_dinamico.controls.append(ft.Text(f"Radiografía de {jugador_sel}", size=22, weight="bold", color="blue"))
                panel_stats_dinamico.controls.append(ft.Row([
                    ft.Container(content=ft.Column([
                        ft.Text("Resumen General", weight="bold"),
                        ft.Text(f"⏱ Tiempo: {min_m}m {min_s}s"),
                        ft.Text(f"📊 Participación: {partidos_jugados} partido(s)"),
                        ft.Text(f"⏳ Minutos posibles: {pos_m}m {pos_s}s", size=12, color="grey"),
                        ft.Text(f"🎯 Efectividad: {int((tot_goles/tot_tiros)*100) if tot_tiros > 0 else 0}% ({tot_goles}G / {tot_tiros}T)"),
                        ft.Text(f"⚠️ Sanciones: {sanciones['Amarilla']}🟨 | {sanciones['2 Minutos']}✌ | {sanciones['Roja']}🟥")
                    ]), padding=15, bgcolor="surfaceVariant", border_radius=10),
                    ft.Container(content=ft.Column([
                        ft.Text("Por Distancia", weight="bold"),
                        graf_efectividad_mini("6 Metros", tiros_distancia["6m"]), graf_efectividad_mini("9 Metros", tiros_distancia["9m"]),
                        graf_efectividad_mini("Penales", tiros_distancia["Penal"]), graf_efectividad_mini("Sin Distancia (N/A)", tiros_distancia["N/A"]),
                    ]), padding=15, bgcolor="surfaceVariant", border_radius=10),
                    ft.Container(content=ft.Column([
                        ft.Text("Por Posición", weight="bold"),
                        graf_efectividad_mini("Extremo", tiros_posicion["Extremo"]), graf_efectividad_mini("Centro", tiros_posicion["Centro"]),
                        graf_efectividad_mini("Pivote", tiros_posicion["Pivote"]), graf_efectividad_mini("Armado", tiros_posicion["Armado"]),
                        graf_efectividad_mini("Sin Posición (N/A)", tiros_posicion["N/A"]),
                    ]), padding=15, bgcolor="surfaceVariant", border_radius=10)
                ], wrap=True))
        page.update()

    def inicializar_filtros_stats():
        opts_cat = [ft.dropdown.Option("Todas")]
        for c in categorias.keys(): opts_cat.append(ft.dropdown.Option(c))
        dropdown_filtro_categoria.options = opts_cat
        if not dropdown_filtro_categoria.value: dropdown_filtro_categoria.value = "Todas"

        opts_partidos = [ft.dropdown.Option(key="historico", text="Histórico Total")]
        vistos = set()
        for p in reversed(partidos_historial):
            if p["id"] not in vistos:
                vistos.add(p["id"])
                opts_partidos.append(ft.dropdown.Option(key=str(p["id"]), text=f"{p['fecha']} vs {p['rival']} ({p['categoria']})"))
        dropdown_filtro_partido.options = opts_partidos
        if not dropdown_filtro_partido.value: dropdown_filtro_partido.value = "historico"
        
        opts_jugadores = [ft.dropdown.Option(key=f"{j['nombre']} (#{j['numero']})", text=f"{j['nombre']} (#{j['numero']})") for j in plantel]
        dropdown_jugador_stats.options = opts_jugadores
        if not dropdown_modo_vista.value: dropdown_modo_vista.value = "equipo"
        
        dropdown_filtro_partido.on_change = actualizar_panel_estadisticas
        dropdown_filtro_categoria.on_change = actualizar_panel_estadisticas
        dropdown_modo_vista.on_change = actualizar_panel_estadisticas
        dropdown_jugador_stats.on_change = actualizar_panel_estadisticas

    tab_stats = ft.Container(
        content=ft.Column([
            ft.Text("Analíticas Avanzadas", size=20, weight="bold"),
            ft.Row([dropdown_filtro_categoria, dropdown_filtro_partido, dropdown_modo_vista, dropdown_jugador_stats], wrap=True),
            Boton("🔄 Aplicar Filtros", on_click=actualizar_panel_estadisticas),
            ft.Divider(), panel_stats_dinamico
        ]), padding=20
    )

    # ==========================================
    # PESTAÑA 4: MODO PARTIDO (EN VIVO)
    # ==========================================
    dropdown_categorias_vivo = ft.Dropdown(label="Seleccionar Categoría", width=200, options=[])
    input_rival = ft.TextField(label="Equipo Rival", width=200)
    txt_reloj = ft.Text("00:00", size=32, weight="bold", color="yellow")
    txt_estado_periodo = ft.Text("Estado: Sin iniciar", size=16, color="cyan")
    
    view_cancha_vivo = ft.Row(wrap=True, alignment="center")
    view_banco_vivo = ft.Row(wrap=True, alignment="center")

    async def loop_cronometro():
        while True:
            await asyncio.sleep(1)
            if estado_partido["activo"]:
                estado_partido["tiempo_segundos"] += 1
                t = estado_partido["tiempo_segundos"]
                txt_reloj.value = f"{t // 60:02}:{t % 60:02}"
                for j in estado_partido["cancha_activa"]:
                    clave = f"{j['nombre']} (#{j['numero']})"
                    estado_partido["segundos_jugados"][clave] = estado_partido["segundos_jugados"].get(clave, 0) + 1
                page.update()

    page.run_task(loop_cronometro)

    def actualizar_pestana_partidos():
        dropdown_categorias_vivo.options = [ft.dropdown.Option(cat) for cat in categorias.keys()]
        page.update()

    def registrar_evento_cronologia(jugador_obj, accion, tiempo_sec=None):
        if not estado_partido["id"]: return
        t = tiempo_sec if tiempo_sec is not None else estado_partido["tiempo_segundos"]
        evento = {
            "partido_id": str(estado_partido["id"]), "rival": estado_partido["rival"],
            "categoria": estado_partido["categoria_actual"], "periodo": estado_partido["periodo"],
            "minuto": f"{t // 60:02}:{t % 60:02}", "jugador": f"{jugador_obj['nombre']} (#{jugador_obj['numero']})",
            "accion": accion, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        estadisticas.append(evento)
        guardar_json(ARCHIVO_ESTADISTICAS, estadisticas)

    def iniciar_partido_config(e):
        cat = dropdown_categorias_vivo.value
        if not cat or not input_rival.value:
            page.snack_bar = ft.SnackBar(content=ft.Text("Selecciona una categoría y escribe el rival"))
            page.snack_bar.open = True; page.update(); return
        
        estado_partido["id"] = datetime.now().strftime("%Y%m%d%H%M%S")
        estado_partido["fecha"] = datetime.now().strftime("%d/%m/%Y")
        estado_partido["categoria_actual"] = cat
        estado_partido["rival"] = input_rival.value.strip()
        estado_partido["banco_activo"] = list(categorias[cat])
        estado_partido["cancha_activa"] = []
        estado_partido["tiempo_segundos"] = 0
        estado_partido["activo"] = False
        estado_partido["segundos_jugados"] = {}
        
        cambiar_periodo("1° Tiempo", False)
        actualizar_interfaz_partido()

    def iniciar_reloj(e):
        if estado_partido["tiempo_segundos"] == 0 and not estado_partido["activo"]:
            for j in estado_partido["cancha_activa"]:
                registrar_evento_cronologia(j, "Ingresa a cancha", 0)
        cambiar_periodo(estado_partido["periodo"], True)

    def cambiar_periodo(nuevo_periodo, activar=False):
        estado_partido["periodo"] = nuevo_periodo
        estado_partido["activo"] = activar
        txt_estado_periodo.value = f"Estado: {nuevo_periodo}" + (" (Corriendo)" if activar else " (Pausado)")
        page.update()

    def finalizar_partido(e):
        if not estado_partido["id"]: return
        if any(str(p["id"]) == str(estado_partido["id"]) for p in partidos_historial):
            page.snack_bar = ft.SnackBar(content=ft.Text("Este partido ya fue guardado."))
            page.snack_bar.open = True; page.update(); return

        cambiar_periodo("Finalizado", False)
        for j in estado_partido["cancha_activa"]:
            registrar_evento_cronologia(j, "Sale al banco")
            
        goles_nuestros, goles_rival = 0, 0
        for ev in estadisticas:
            if str(ev.get("partido_id", "")) == str(estado_partido["id"]):
                acc = ev.get("accion", "")
                if ("Tiro:" in acc and "Gol" in acc and "No Gol" not in acc) or "Penal - Gol" in acc: goles_nuestros += 1
                if "Tiro Rival" in acc and "Hecho" in acc: goles_rival += 1

        resumen_partido = {
            "id": estado_partido["id"], "fecha": estado_partido["fecha"],
            "categoria": estado_partido["categoria_actual"], "rival": estado_partido["rival"],
            "goles_nuestros": goles_nuestros, "goles_rival": goles_rival,
            "minutos_jugados": estado_partido["segundos_jugados"],
            "duracion_total": estado_partido["tiempo_segundos"] # Guardamos la duración exacta del partido
        }
        partidos_historial.append(resumen_partido)
        guardar_json(ARCHIVO_PARTIDOS, partidos_historial)
        
        estado_partido["id"] = None
        page.snack_bar = ft.SnackBar(content=ft.Text("¡Partido finalizado y guardado con éxito!"))
        page.snack_bar.open = True; page.update()

    def actualizar_interfaz_partido():
        view_cancha_vivo.controls.clear(); view_banco_vivo.controls.clear()
        for j in estado_partido["cancha_activa"]:
            color_btn = "green700" if j.get("es_arquero") else "blue700"
            view_cancha_vivo.controls.append(ft.Column([
                Boton(f"{j['nombre']} (#{j['numero']})", width=110, height=80, on_click=lambda e, jug=j: abrir_menu_accion_vivo(jug), bgcolor=color_btn),
                ft.TextButton("⬇ Al Banco", on_click=lambda e, jug=j: mover_a_banco(jug))
            ], horizontal_alignment="center"))
        for j in estado_partido["banco_activo"]:
            tag_arq = " 🧤" if j.get("es_arquero") else ""
            view_banco_vivo.controls.append(ft.Row([
                ft.Text(f"{j['nombre']} (#{j['numero']}){tag_arq}", width=150),
                Boton("⬆ A Cancha", on_click=lambda e, jug=j: mover_a_cancha(jug))
            ]))
        page.update()

    def mover_a_banco(jug):
        if jug in estado_partido["cancha_activa"]:
            estado_partido["cancha_activa"].remove(jug)
            estado_partido["banco_activo"].append(jug)
            if estado_partido["tiempo_segundos"] > 0: registrar_evento_cronologia(jug, "Sale al banco")
            actualizar_interfaz_partido()

    def mover_a_cancha(jug):
        if len(estado_partido["cancha_activa"]) >= 7:
            page.snack_bar = ft.SnackBar(content=ft.Text("Ya hay 7 jugadores en cancha"))
            page.snack_bar.open = True; page.update(); return
        if jug in estado_partido["banco_activo"]:
            estado_partido["banco_activo"].remove(jug)
            estado_partido["cancha_activa"].append(jug)
            if estado_partido["tiempo_segundos"] > 0: registrar_evento_cronologia(jug, "Ingresa a cancha")
            actualizar_interfaz_partido()

    panel_content_vivo = ft.Column(alignment="center", horizontal_alignment="center")
    bottom_sheet_vivo = ft.BottomSheet(content=ft.Container(content=panel_content_vivo, padding=30, bgcolor="surfaceVariant", border_radius=20))
    page.overlay.append(bottom_sheet_vivo)

    def cerrar_panel_vivo(): bottom_sheet_vivo.open = False; page.update()

    def registrar_evento_vivo(accion_texto, jugador_obj):
        if not estado_partido["id"]:
            page.snack_bar = ft.SnackBar(content=ft.Text("Inicia un partido primero."))
            page.snack_bar.open = True; page.update(); return
        registrar_evento_cronologia(jugador_obj, accion_texto)
        page.snack_bar = ft.SnackBar(content=ft.Text(f"Registrado: {accion_texto}"))
        page.snack_bar.open = True; cerrar_panel_vivo()

    def render_menu_vivo(titulo, opciones, jugador_obj):
        botones = [Boton(txt, on_click=lambda e, fn=func: fn(jugador_obj)) for txt, func in opciones]
        panel_content_vivo.controls = [
            ft.Text(f"{titulo} - {jugador_obj['nombre']} (#{jugador_obj['numero']})", size=18, weight="bold"),
            ft.Row(botones, alignment="center", wrap=True), Boton("❌ Cancelar", on_click=lambda _: cerrar_panel_vivo())
        ]
        page.update()

    def flujo_tiro_posicion(res_parcial, jugador_obj): render_menu_vivo("Posición del Tiro", [("Extremo", lambda j: registrar_evento_vivo(f"Tiro: {res_parcial} - Extremo", j)),("Centro", lambda j: registrar_evento_vivo(f"Tiro: {res_parcial} - Centro", j)),("Pivote", lambda j: registrar_evento_vivo(f"Tiro: {res_parcial} - Pivote", j)),("Armado", lambda j: registrar_evento_vivo(f"Tiro: {res_parcial} - Armado", j))], jugador_obj)
    def flujo_tiro_distancia(res_base, jugador_obj): render_menu_vivo("Distancia", [("6 metros (de contra)", lambda j: flujo_tiro_posicion(f"{res_base} - 6m (Contra)", j)),("9 metros", lambda j: flujo_tiro_posicion(f"{res_base} - 9m", j))], jugador_obj)
    def flujo_tiro_nogol_motivo(jugador_obj): render_menu_vivo("Motivo No Gol", [("Piso línea", lambda j: flujo_tiro_distancia("No Gol - Piso línea", j)),("Falta ataque", lambda j: flujo_tiro_distancia("No Gol - Falta en ataque", j)),("Erró", lambda j: flujo_tiro_distancia("No Gol - Erró", j)),("Atajó arquero", lambda j: flujo_tiro_distancia("No Gol - Atajó", j))], jugador_obj)
    def flujo_tiro(jugador_obj): render_menu_vivo("Resultado del Tiro", [("Gol", lambda j: flujo_tiro_distancia("Gol", j)),("No Gol", lambda j: flujo_tiro_nogol_motivo(j))], jugador_obj)
    def flujo_arq_posicion(res_parcial, jugador_obj): render_menu_vivo("Lanzador Rival", [("Central", lambda j: registrar_evento_vivo(f"Tiro Rival: {res_parcial} - Central", j)),("Armado", lambda j: registrar_evento_vivo(f"Tiro Rival: {res_parcial} - Armado", j)),("Extremo", lambda j: registrar_evento_vivo(f"Tiro Rival: {res_parcial} - Extremo", j)),("Pivote", lambda j: registrar_evento_vivo(f"Tiro Rival: {res_parcial} - Pivote", j))], jugador_obj)
    def flujo_arq_distancia(res, jugador_obj): render_menu_vivo("Distancia Rival", [("Contra", lambda j: flujo_arq_posicion(f"{res} - Contra", j)),("6 metros", lambda j: flujo_arq_posicion(f"{res} - 6m", j)),("9 metros", lambda j: flujo_arq_posicion(f"{res} - 9m", j)),("Penal", lambda j: flujo_arq_posicion(f"{res} - Penal", j))], jugador_obj)
    
    def abrir_menu_accion_vivo(jugador_obj):
        if jugador_obj.get("es_arquero", False):
            render_menu_vivo("Tiro Rival", [("Atajado", lambda j: flujo_arq_distancia("Atajado", j)),("Hecho (Gol)", lambda j: flujo_arq_distancia("Hecho", j))], jugador_obj)
        else:
            render_menu_vivo("Acción de Jugador", [("Tiro", flujo_tiro),("Pérdida balón", lambda j: render_menu_vivo("Tipo Pérdida", [("Pase", lambda x: registrar_evento_vivo("Pérdida - Pase", x)),("Dribbling", lambda x: registrar_evento_vivo("Pérdida - Dribbling", x))], j)),("Amonestación", lambda j: render_menu_vivo("Sanción", [("2 min", lambda x: registrar_evento_vivo("Sanción - 2 Minutos", x)),("Amarilla", lambda x: registrar_evento_vivo("Sanción - Amarilla", x)),("Roja", lambda x: registrar_evento_vivo("Sanción - Roja", x))], j)),("Penal a favor", lambda j: render_menu_vivo("Penal", [("Gol", lambda x: registrar_evento_vivo("Penal - Gol", x)),("Atajada", lambda x: registrar_evento_vivo("Penal - Atajada", x)),("Errada", lambda x: registrar_evento_vivo("Penal - Errada", x))], j)),("Tiro bloqueado", lambda j: registrar_evento_vivo("Tiro bloqueado", j))], jugador_obj)
        bottom_sheet_vivo.open = True; page.update()

    tab_partidos = ft.Container(content=ft.Column([
        ft.Text("Modo Partido (En Vivo)", size=20, weight="bold"),
        ft.Row([dropdown_categorias_vivo, input_rival, Boton("Crear Partido", on_click=iniciar_partido_config)], alignment="center"), ft.Divider(),
        txt_estado_periodo,
        ft.Row([txt_reloj, Boton("▶ Play", on_click=iniciar_reloj, bgcolor="green700"), Boton("⏸ Pausar", on_click=lambda _: cambiar_periodo(estado_partido["periodo"], False), bgcolor="orange700")], alignment="center"),
        ft.Row([Boton("🏁 Terminar 1° Tiempo", on_click=lambda _: cambiar_periodo("Entretiempo", False), bgcolor="blueGrey700"), Boton("▶ Iniciar 2° Tiempo", on_click=lambda _: cambiar_periodo("2° Tiempo", True), bgcolor="teal700"), Boton("🛑 Guardar Partido", on_click=finalizar_partido, bgcolor="red700")], alignment="center", wrap=True),
        ft.Divider(), ft.Text("7 en Cancha", size=16, weight="bold", color="blue"), view_cancha_vivo, ft.Divider(), ft.Text("Banco", size=18, weight="bold", color="grey"), view_banco_vivo
    ]), padding=20)

    # ==========================================
    # NAVEGACIÓN
    # ==========================================
    def cambiar_vista(vista):
        vista_dinamica.content = vista
        if vista == tab_stats: 
            inicializar_filtros_stats()
            actualizar_panel_estadisticas()
        page.update()

    barra_navegacion = ft.Row([Boton("1. Jugadores", on_click=lambda _: cambiar_vista(tab_jugadores)), Boton("2. Categorías", on_click=lambda _: cambiar_vista(tab_categorias)), Boton("3. Estadísticas", on_click=lambda _: cambiar_vista(tab_stats)), Boton("4. En Vivo", on_click=lambda _: cambiar_vista(tab_partidos))], alignment="center", wrap=True)

    refrescar_lista_jugadores()
    actualizar_pestana_categorias()
    actualizar_pestana_partidos()
    cambiar_vista(tab_jugadores)

    page.add(barra_navegacion, ft.Divider(), vista_dinamica)

if hasattr(ft, "run"): ft.run(main)
else: ft.app(main)