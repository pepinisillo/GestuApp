import cv2
import mediapipe as mp
import numpy as np
import keyboard
import time
import math
import threading
import pystray
from PIL import Image, ImageDraw
import json
import os
from functools import partial
import customtkinter as ctk
from tkinter import messagebox

# Configuración de apariencia
ctk.set_appearance_mode("System")  # Puede ser "Light", "Dark" o "System"
ctk.set_default_color_theme("blue")  # Temas: "blue", "green", "dark-blue"

# Configuración por defecto
DEFAULT_CONFIG = {
    "DISTANCIA_MIN_VOL": 0.05,
    "DISTANCIA_MAX_VOL": 0.15,
    "UMBRAL_PAUSA": 0.025,
    "UMBRAL_ANGULO_CANCION": 50,
    "UMBRAL_ANGULO_VOLUMEN": 30,
    "TIEMPO_ENTRE_ACCIONES": 1.5,
    "INVERTIR_DIRECCION_CANCION": False,
    "VELOCIDAD_SCROLL": 0.5,
    "GESTOS_ACCIONES": {
        "pulgar_indice_cerca": "play_pause",
        "angulo_grande_izquierda": "anterior",
        "angulo_grande_derecha": "siguiente",
        "angulo_pequeno_distancia": "volumen",
        "angulo_pequeno_movimiento": "scroll"
    }
}

# Acciones disponibles
ACCIONES = {
    "play_pause": {"nombre": "Play/Pause", "tecla": "play/pause"},
    "anterior": {"nombre": "Canción Anterior", "tecla": "previous track"},
    "siguiente": {"nombre": "Canción Siguiente", "tecla": "next track"},
    "volumen": {"nombre": "Control de Volumen", "tecla": None},
    "scroll": {"nombre": "Control de Scroll", "tecla": None},  # Unificado scrol
    "nada": {"nombre": "No hacer nada", "tecla": None}
}

# Ruta del archivo de configuración
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "gesture_controller_config.json")


class GestureController:
    def __init__(self):
        # Cargar configuración
        self.load_config()

        # Variables de control
        self.running = False
        self.paused = False
        self.window_visible = False
        self.ultimo_gesto = 0
        self.cambio_listo = True
        self.cap = None

        # Configuración de MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = None
        self.mp_drawing = mp.solutions.drawing_utils

        # Crear ventana principal con CustomTkinter
        self.root = ctk.CTk()
        self.root.title("Control por Gestos")
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.withdraw()  # Ocultar ventana al inicio

        # Configurar interfaz de usuario
        self.setup_ui()

        # Configurar icono en la bandeja del sistema
        self.setup_tray()

        # Iniciar thread para procesamiento de video
        self.video_thread = None

        # Añadir variables para control de la ventana
        self._camera_window_open = True
        self._camera_lock = threading.Lock()

    def load_config(self):
        """Cargar configuración desde archivo o usar valores por defecto"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                for key, value in DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
            else:
                self.config = DEFAULT_CONFIG.copy()
            self.save_config()
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            self.config = DEFAULT_CONFIG.copy()

    def save_config(self):
        """Guardar configuración actual a archivo"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error al guardar configuración: {e}")

    def setup_ui(self):
        """Configurar interfaz de usuario moderna con CustomTkinter"""
        self.root.geometry("900x650")
        self.root.minsize(800, 600)

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Notebook con pestañas
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)

        # Añadir pestañas
        self.tabview.add("Parámetros")
        self.tabview.add("Mapeo de Gestos")

        # Configurar pestaña de parámetros
        self.setup_parametros_ui(self.tabview.tab("Parámetros"))

        # Configurar pestaña de mapeo de gestos
        self.setup_gestos_ui(self.tabview.tab("Mapeo de Gestos"))

        # Frame de botones
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Botones
        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="Guardar Configuración",
            command=self.save_ui_config,
            fg_color="#2e8b57",
            hover_color="#3cb371"
        )
        self.save_btn.pack(side="left", padx=5, pady=5)

        self.reset_btn = ctk.CTkButton(
            self.button_frame,
            text="Restaurar Valores",
            command=self.reset_config,
            fg_color="#d2691e",
            hover_color="#cd853f"
        )
        self.reset_btn.pack(side="left", padx=5, pady=5)

        self.minimize_btn = ctk.CTkButton(
            self.button_frame,
            text="Minimizar a Bandeja",
            command=self.minimize_to_tray
        )
        self.minimize_btn.pack(side="right", padx=5, pady=5)

        # Status bar
        self.status_bar = ctk.CTkLabel(
            self.main_frame,
            text="Estado: Listo",
            anchor="w",
            font=("Arial", 10)
        )
        self.status_bar.pack(fill="x", padx=10, pady=(0, 5))

    def setup_parametros_ui(self, parent):
        """Configurar controles para ajuste de parámetros con diseño moderno"""
        # Frame con scroll
        self.scroll_frame = ctk.CTkScrollableFrame(parent)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Crear variables de control para cada parámetro
        self.param_vars = {}

        # Definir rangos para cada parámetro
        param_ranges = {
            "DISTANCIA_MIN_VOL": (0.01, 0.1, 0.01),
            "DISTANCIA_MAX_VOL": (0.05, 0.3, 0.01),
            "UMBRAL_PAUSA": (0.01, 0.1, 0.005),
            "UMBRAL_ANGULO_CANCION": (20, 90, 5),
            "UMBRAL_ANGULO_VOLUMEN": (10, 60, 5),
            "VELOCIDAD_SCROLL": (0.1, 1.0, 0.1),
            "TIEMPO_ENTRE_ACCIONES": (0.5, 3.0, 0.1)
        }

        param_descriptions = {
            "DISTANCIA_MIN_VOL": "Distancia mínima para control de volumen",
            "DISTANCIA_MAX_VOL": "Distancia máxima para control de volumen",
            "UMBRAL_PAUSA": "Umbral para detectar gesto de pausa",
            "UMBRAL_ANGULO_CANCION": "Ángulo para cambio de canción",
            "UMBRAL_ANGULO_VOLUMEN": "Ángulo máximo para control de volumen/scroll",
            "VELOCIDAD_SCROLL": "Velocidad del scroll (0.1 lento - 1.0 rápido)",
            "TIEMPO_ENTRE_ACCIONES": "Tiempo entre acciones (segundos)"
        }

        for param, (min_val, max_val, step) in param_ranges.items():
            # Frame para cada parámetro
            frame = ctk.CTkFrame(self.scroll_frame)
            frame.pack(fill="x", padx=5, pady=5)

            # Etiqueta descriptiva
            label = ctk.CTkLabel(
                frame,
                text=param_descriptions[param],
                width=200,
                anchor="w"
            )
            label.pack(side="left", padx=(5, 10))

            # Slider
            self.param_vars[param] = ctk.DoubleVar(value=self.config[param])
            slider = ctk.CTkSlider(
                frame,
                from_=min_val,
                to=max_val,
                number_of_steps=int((max_val - min_val) / step),
                variable=self.param_vars[param]
            )
            slider.pack(side="left", fill="x", expand=True, padx=5)

            # Valor actual
            value_label = ctk.CTkLabel(
                frame,
                textvariable=self.param_vars[param],
                width=50
            )
            value_label.pack(side="right", padx=(5, 10))

        # Opciones adicionales
        self.option_frame = ctk.CTkFrame(self.scroll_frame)
        self.option_frame.pack(fill="x", padx=5, pady=10)

        self.invertir_var = ctk.BooleanVar(value=self.config["INVERTIR_DIRECCION_CANCION"])
        self.invertir_check = ctk.CTkCheckBox(
            self.option_frame,
            text="Invertir dirección para cambio de canción",
            variable=self.invertir_var,
            onvalue=True,
            offvalue=False
        )
        self.invertir_check.pack(anchor="w", padx=5, pady=5)

    def setup_gestos_ui(self, parent):
        """Configurar controles para mapeo de gestos a acciones"""
        # Frame con scroll
        self.gestos_scroll_frame = ctk.CTkScrollableFrame(parent)
        self.gestos_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.gesto_vars = {}

        gestos_descripcion = {
            "pulgar_indice_cerca": "Pulgar e índice tocándose",
            "angulo_grande_izquierda": "Ángulo grande con pulgar y dedo índice(mano hacia la izquierda)",
            "angulo_grande_derecha": "Ángulo grande con pulgar y dedo índice(mano hacia la derecha)",
            "angulo_pequeno_distancia": "Pinzas pequeñas con pulgar y dedo índice"
        }

        for gesto, descripcion in gestos_descripcion.items():
            # Frame para cada gesto
            frame = ctk.CTkFrame(self.gestos_scroll_frame)
            frame.pack(fill="x", padx=5, pady=5)

            # Etiqueta descriptiva
            label = ctk.CTkLabel(
                frame,
                text=descripcion,
                width=200,
                anchor="w"
            )
            label.pack(side="left", padx=(5, 10))

            # Combobox para seleccionar acción
            self.gesto_vars[gesto] = ctk.StringVar(value=self.config["GESTOS_ACCIONES"][gesto])

            # Obtener nombre de la acción actual
            accion_actual = self.config["GESTOS_ACCIONES"][gesto]
            nombre_accion_actual = ACCIONES[accion_actual]["nombre"]

            combo = ctk.CTkComboBox(
                frame,
                variable=self.gesto_vars[gesto],
                values=[accion["nombre"] for accion in ACCIONES.values()],
                state="readonly",
                width=200
            )
            combo.set(nombre_accion_actual)
            combo.pack(side="left", padx=5, pady=5)

            # Mapear nombre de acción a clave
            self.accion_a_clave = {accion["nombre"]: clave for clave, accion in ACCIONES.items()}

    def save_ui_config(self):
        """Guardar la configuración desde la UI al archivo"""
        try:
            # Actualizar configuración desde variables de UI
            for param, var in self.param_vars.items():
                self.config[param] = var.get()

            self.config["INVERTIR_DIRECCION_CANCION"] = self.invertir_var.get()

            # Actualizar mapeo de gestos
            for gesto, var in self.gesto_vars.items():
                nombre_accion = var.get()
                for clave, accion in ACCIONES.items():
                    if accion["nombre"] == nombre_accion:
                        self.config["GESTOS_ACCIONES"][gesto] = clave
                        break

            # Guardar en archivo
            self.save_config()

            # Actualizar estado
            self.status_bar.configure(text="Configuración guardada correctamente", text_color="#2e8b57")

            # Si el procesamiento está en curso, reiniciar para aplicar la nueva configuración
            if self.running:
                self.restart_processing()

            # Temporizador para limpiar el mensaje
            self.root.after(3000, lambda: self.status_bar.configure(text="Estado: Listo", text_color="white"))

        except Exception as e:
            self.status_bar.configure(text=f"Error al guardar: {str(e)}", text_color="#ff3333")
            self.root.after(3000, lambda: self.status_bar.configure(text="Estado: Error", text_color="#ff3333"))

    def reset_config(self):
        """Restaurar configuración por defecto"""
        if messagebox.askyesno("Restaurar valores", "¿Está seguro de restaurar la configuración por defecto?"):
            self.config = DEFAULT_CONFIG.copy()
            self.save_config()

            # Actualizar UI
            for param, var in self.param_vars.items():
                var.set(self.config[param])

            self.invertir_var.set(self.config["INVERTIR_DIRECCION_CANCION"])

            for gesto, var in self.gesto_vars.items():
                accion = self.config["GESTOS_ACCIONES"][gesto]
                var.set(ACCIONES[accion]["nombre"])

            # Actualizar estado
            self.status_bar.configure(text="Configuración restaurada a valores predeterminados", text_color="#2e8b57")

            # Reiniciar procesamiento si está en curso
            if self.running:
                self.restart_processing()

            # Temporizador para limpiar el mensaje
            self.root.after(3000, lambda: self.status_bar.configure(text="Estado: Listo", text_color="white"))

    def create_tray_icon(self):
        """Crear imagen para icono de bandeja"""
        width = 64
        height = 64
        color1 = (0, 128, 255)  # Azul claro
        color2 = (255, 255, 255)  # Blanco

        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)

        # Dibujar un ícono simple de una mano
        points = [
            (20, 50), (20, 30), (30, 20),  # Pulgar
            (35, 15), (35, 40),  # Índice
            (42, 17), (42, 38),  # Medio
            (49, 19), (49, 36),  # Anular
            (56, 22), (56, 34),  # Meñique
            (20, 50)  # Cerrar forma
        ]

        dc.polygon(points, fill=color2)
        return image

    def setup_tray(self):
        """Configurar icono en la bandeja del sistema"""
        icon_image = self.create_tray_icon()

        menu = (
            pystray.MenuItem('Mostrar/Ocultar Config', self.toggle_window),
            pystray.MenuItem('Mostrar/Ocultar Cámara', self.toggle_camera_window),
            pystray.MenuItem('Iniciar/Detener', self.toggle_processing),
            pystray.MenuItem('Salir', self.quit_app)
        )

        self.icon = pystray.Icon("gesture_controller", icon_image, "Control por Gestos", menu)
        # Asignar la función al clic izquierdo
        self.icon.on_click = self.on_icon_click

        # Iniciar el icono en un thread separado
        threading.Thread(target=self.icon.run, daemon=True).start()

    def toggle_window(self):
        """Mostrar u ocultar la ventana de configuración"""
        if self.window_visible:
            self.root.withdraw()
            self.window_visible = False
        else:
            self.root.deiconify()
            self.root.lift()
            self.window_visible = True

    def minimize_to_tray(self):
        """Minimizar la aplicación a la bandeja del sistema"""
        self.root.withdraw()
        self.window_visible = False

    def toggle_processing(self):
        """Iniciar o detener el procesamiento de video"""
        if self.running:
            self.stop_processing()
            self.status_bar.configure(text="Procesamiento detenido", text_color="#ff3333")
        else:
            self.start_processing()
            self.status_bar.configure(text="Procesamiento iniciado", text_color="#2e8b57")

        # Temporizador para limpiar el mensaje
        self.root.after(3000, lambda: self.status_bar.configure(text="Estado: Listo", text_color="white"))

    def start_processing(self):
        """Iniciar el procesamiento de video en un thread separado"""
        if not self.running:
            self.running = True
            self.paused = False
            self.video_thread = threading.Thread(target=self.process_video)
            self.video_thread.daemon = True
            self.video_thread.start()

    def stop_processing(self):
        """Detener el procesamiento de video"""
        self.running = False
        if self.video_thread:
            self.video_thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()

    def restart_processing(self):
        """Reiniciar el procesamiento de video para aplicar nueva configuración"""
        self.stop_processing()
        self.start_processing()

    def quit_app(self):
        """Salir de la aplicación"""
        self.stop_processing()
        self.icon.stop()
        self.root.quit()
        self.root.destroy()

    def calcular_angulo(self, a, b, c):
        """Calcular el ángulo entre tres puntos (b es el vértice)"""
        ba = np.array([a.x - b.x, a.y - b.y])
        bc = np.array([c.x - b.x, c.y - b.y])

        coseno_angulo = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        # Asegurar que el valor está dentro del rango válido para arccos
        coseno_angulo = np.clip(coseno_angulo, -1.0, 1.0)
        angulo = np.arccos(coseno_angulo)

        return np.degrees(angulo)

    def ejecutar_accion(self, accion_clave, parametro=None):
        """Ejecutar la acción correspondiente"""
        if accion_clave == "nada":
            return
        current_time = time.time()

        if accion_clave == "volumen":
            if parametro < 30:
                keyboard.press_and_release('volume down')
                return "BAJAR VOLUMEN"
            elif parametro > 70:
                keyboard.press_and_release('volume up')
                return "SUBIR VOLUMEN"
            return None

        elif accion_clave == "scroll":
            # Usar el parámetro de velocidad para controlar la frecuencia de scroll
            scroll_threshold = 100 - (self.config["VELOCIDAD_SCROLL"] * 80)  # Ajustar el rango

            if parametro < 30:
                # Solo hacer scroll si ha pasado suficiente tiempo
                if hasattr(self, 'last_scroll_time'):
                    if current_time - self.last_scroll_time > (1.1 - self.config["VELOCIDAD_SCROLL"]):
                        keyboard.press_and_release('page down')
                        self.last_scroll_time = current_time
                else:
                    keyboard.press_and_release('page down')
                    self.last_scroll_time = current_time
                return "SCROLL ABAJO"
            elif parametro > 70:
                if hasattr(self, 'last_scroll_time'):
                    if current_time - self.last_scroll_time > (1.1 - self.config["VELOCIDAD_SCROLL"]):
                        keyboard.press_and_release('page up')
                        self.last_scroll_time = current_time
                else:
                    keyboard.press_and_release('page up')
                    self.last_scroll_time = current_time
                return "SCROLL ARRIBA"
            return None


        elif accion_clave in ACCIONES and ACCIONES[accion_clave]["tecla"]:
            keyboard.press_and_release(ACCIONES[accion_clave]["tecla"])
            return ACCIONES[accion_clave]["nombre"].upper()

        return None

    def toggle_camera_window(self):
        """Alternar la visibilidad de la ventana de cámara"""
        with self._camera_lock:
            self._camera_window_open = not self._camera_window_open
            if not self._camera_window_open:
                cv2.destroyAllWindows()

    def process_video(self):
        """Procesar video para detectar gestos"""
        try:
            self.cap = cv2.VideoCapture(0)
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )

            while self.running and self.cap.isOpened():
                success, image = self.cap.read()
                if not success:
                    continue

                # Procesar solo si no está pausado
                if not self.paused:
                    # Convertir imagen a RGB para MediaPipe
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    results = self.hands.process(image_rgb)
                    gesto_actual = None

                    if results.multi_hand_landmarks:
                        hand_landmarks = results.multi_hand_landmarks[0]
                        indice = hand_landmarks.landmark[8]  # Punta del dedo índice
                        pulgar = hand_landmarks.landmark[4]  # Punta del dedo pulgar
                        mcp_indice = hand_landmarks.landmark[5]  # Base del dedo índice
                        wrist = hand_landmarks.landmark[0]  # Muñeca

                        # Calcular distancia entre pulgar e índice
                        distancia = np.linalg.norm([indice.x - pulgar.x, indice.y - pulgar.y])
                        tiempo_actual = time.time()

                        # Calcular ángulo entre pulgar, muñeca e índice
                        angulo_pulgar = self.calcular_angulo(pulgar, wrist, indice)

                        # Lógica de gestos con anti-rebote
                        if self.cambio_listo:
                            # Gesto 1: Pulgar e índice muy cercanos (PAUSA)
                            if distancia < self.config["UMBRAL_PAUSA"]:
                                accion = self.config["GESTOS_ACCIONES"]["pulgar_indice_cerca"]
                                gesto_actual = self.ejecutar_accion(accion)
                                self.cambio_listo = False
                                self.ultimo_gesto = tiempo_actual
                                
                                # Mostrar "PAUSA" en rojo cuando se detecta el gesto
                                if accion == "play_pause":
                                    # Obtener dimensiones de la imagen
                                    height, width = image.shape[:2]
                                    # Calcular posición central
                                    text = "PAUSA"
                                    font = cv2.FONT_HERSHEY_SIMPLEX
                                    font_scale = 2
                                    thickness = 3
                                    # Obtener tamaño del texto
                                    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                                    # Calcular posición para centrar el texto
                                    text_x = (width - text_width) // 2
                                    text_y = (height + text_height) // 2
                                    # Dibujar el texto en rojo
                                    cv2.putText(image, text, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)

                            # Gesto 2 y 3: Ángulo grande (izquierda o derecha)
                            elif angulo_pulgar > self.config["UMBRAL_ANGULO_CANCION"]:
                                invertir = self.config["INVERTIR_DIRECCION_CANCION"]
                                if indice.x < wrist.x:
                                    accion = self.config["GESTOS_ACCIONES"]["angulo_grande_" + ("derecha" if invertir else "izquierda")]
                                else:
                                    accion = self.config["GESTOS_ACCIONES"]["angulo_grande_" + ("izquierda" if invertir else "derecha")]
                                gesto_actual = self.ejecutar_accion(accion)
                                self.cambio_listo = False
                                self.ultimo_gesto = tiempo_actual

                            # Gesto 4: Ángulo pequeño con distancia variable (volumen u otro)
                            elif angulo_pulgar <= self.config["UMBRAL_ANGULO_VOLUMEN"] and distancia >= self.config["UMBRAL_PAUSA"]:
                                accion = self.config["GESTOS_ACCIONES"]["angulo_pequeno_distancia"]
                                if accion == "volumen":
                                    vol = np.interp(
                                        distancia,
                                        [self.config["DISTANCIA_MIN_VOL"], self.config["DISTANCIA_MAX_VOL"]],
                                        [0, 100]
                                    )
                                    gesto_actual = self.ejecutar_accion("volumen", vol)
                                elif accion == "scroll":
                                    scroll_pos = np.interp(
                                        indice.x,
                                        [wrist.x - 0.2, wrist.x + 0.2],
                                        [0, 100]
                                    )
                                    gesto_actual = self.ejecutar_accion("scroll", scroll_pos)
                                else:
                                    gesto_actual = self.ejecutar_accion(accion)
                                    if accion != "nada":
                                        self.cambio_listo = False
                                        self.ultimo_gesto = tiempo_actual

                        # Reactivar después del tiempo de espera
                        if not self.cambio_listo and (tiempo_actual - self.ultimo_gesto) > self.config["TIEMPO_ENTRE_ACCIONES"]:
                            self.cambio_listo = True

                        # Dibujar landmarks y ángulo
                        self.mp_drawing.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                        # Mostrar ángulo
                        cv2.putText(image, f"Angulo: {angulo_pulgar:.1f}°",
                                    (int(wrist.x * image.shape[1]), int(wrist.y * image.shape[0])),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                        # Mostrar estado del control de volumen
                        if angulo_pulgar <= self.config["UMBRAL_ANGULO_VOLUMEN"]:
                            vol_status = "ACTIVO" if self.config["GESTOS_ACCIONES"][
                                                         "angulo_pequeno_distancia"] == "volumen" else "INACTIVO"
                            color = (0, 255, 0) if vol_status == "ACTIVO" else (0, 0, 255)

                            cv2.putText(image, f"Control de volumen: {vol_status}", (10, 150),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                # Mostrar "PAUSA" en rojo cuando está pausado
                if self.paused:
                    # Obtener dimensiones de la imagen
                    height, width = image.shape[:2]
                    # Calcular posición central
                    text = "PAUSA"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 2
                    thickness = 3
                    # Obtener tamaño del texto
                    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                    # Calcular posición para centrar el texto
                    text_x = (width - text_width) // 2
                    text_y = (height + text_height) // 2
                    # Dibujar el texto en rojo
                    cv2.putText(image, text, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)

                # Mostrar información
                cv2.putText(image, f"Ultimo comando: {gesto_actual if gesto_actual else 'Ninguno'}", (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(
                    image,
                    f"Tiempo restante: {max(0, self.config['TIEMPO_ENTRE_ACCIONES'] - (time.time() - self.ultimo_gesto)):.1f}s",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )

                # Mostrar controles
                cv2.putText(image, "Presiona 'q' para cerrar, 'p' para pausar", (10, image.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Solo mostrar la ventana si está configurada para estar abierta
                with self._camera_lock:
                    if self._camera_window_open:
                        cv2.imshow('Control por Gestos', image)
                        key = cv2.waitKey(1) & 0xFF

                        if key == ord('q'):
                            # En lugar de cerrar, minimizar a la bandeja
                            self._camera_window_open = False
                            cv2.destroyAllWindows()
                        elif key == ord('p'):
                            self.paused = not self.paused

        except Exception as e:
            print(f"Error en procesamiento de video: {e}")
        finally:
            if self.hands:
                self.hands.close()
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            self.running = False

    def on_icon_click(self, icon, button):
        """Manejar clic en el icono"""
        if str(button) == "Button.left":
            self.toggle_camera_window()
        # Los clics con botón derecho ya son manejados por pystray para mostrar el menú

    def handle_camera_window_close(self):
        """Manejar el cierre de la ventana de cámara"""
        self.toggle_camera_window()


if __name__ == "__main__":
    app = GestureController()
    app.start_processing()  # Iniciar procesamiento automáticamente
    app.root.mainloop()