#!/usr/bin/env python
# coding: utf-8

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import time

# Importación opcional para optimización
try:
    from scipy.spatial import cKDTree
    KDTREE_AVAILABLE = True
except ImportError:
    KDTREE_AVAILABLE = False


class InteractiveFigureCanvas(FigureCanvas):
    """
    Clase que extiende FigureCanvas con funcionalidades interactivas avanzadas:
    - Herramientas de navegación (zoom, pan, etc.)
    - Tooltips personalizados al pasar el mouse sobre puntos de datos
    - Resaltado de puntos de datos seleccionados
    """
    
    def __init__(self, figure=None, parent=None, toolbar_visible=True, tooltip_enabled=True):
        """
        Inicializa un canvas interactivo con funcionalidades avanzadas.
        
        Args:
            figure (Figure): Objeto Figure de matplotlib. Si es None, se crea uno nuevo.
            parent (QWidget): Widget padre para la jerarquía de Qt.
            toolbar_visible (bool): Si se debe mostrar la barra de herramientas.
            tooltip_enabled (bool): Si se habilitan los tooltips al pasar el mouse.
        """
        # Si no se proporciona figura, crear una nueva
        if figure is None:
            self.figure = Figure(figsize=(8, 6), dpi=100)
        else:
            self.figure = figure
        
        # Inicializar el canvas base
        super(InteractiveFigureCanvas, self).__init__(self.figure)
        self.setParent(parent)
        
        # Hacer que el canvas sea receptivo al tamaño
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, 
            QtWidgets.QSizePolicy.Expanding
        )
        self.updateGeometry()
        
        # Variables para manejo de tooltips
        self.tooltip_enabled = tooltip_enabled
        self.last_tooltip_point = None
        self.tooltip_labels = []
        self.tooltip_artists = []
        self.hover_artist = None
        self.tooltip_format = '${value:,.0f}'  # Formato monetario por defecto
        
        # Conexiones de eventos
        if tooltip_enabled:
            self.mpl_connect('motion_notify_event', self._on_mouse_move)
            self.mpl_connect('axes_leave_event', self._on_axes_leave)
        
        # Crear toolbar si está habilitada
        self.toolbar = None
        if toolbar_visible and parent is not None:
            self.toolbar_layout = QtWidgets.QVBoxLayout(parent)
            self.toolbar = NavigationToolbar(self, parent)
            self.toolbar_layout.addWidget(self.toolbar)
            self.toolbar_layout.addWidget(self)
        
        # Variables para optimización de rendimiento
        self.tooltip_delay = 100  # ms para throttling
        self.last_tooltip_time = 0
        self.last_draw_time = 0
        self.min_redraw_interval = 50  # ms mínimo entre redraws
        self._tooltip_active = False
        self._current_tooltip = None
        self._dataset_size = 0
        self._mouse_position = None
        
        # Diccionario para almacenar datos de tooltips por eje
        self.tooltip_data = {}
        
    def add_tooltip_data(self, ax, x_data, y_data, labels=None, artists=None, formatter=None, highlight_colors=None, highlight_color=None):
        """
        Agrega datos para mostrar en tooltips cuando el usuario pasa el mouse sobre ellos.
        
        Args:
            ax (Axes): Objeto Axes al que pertenecen los datos
            x_data (array-like): Datos del eje X
            y_data (array-like): Datos del eje Y
            labels (list, optional): Etiquetas para cada punto de datos
            artists (list, optional): Artistas de matplotlib asociados con los datos
            formatter (func, optional): Función para formatear los valores en el tooltip
            highlight_colors (list, optional): Colores específicos para resaltar cada punto
        """
        self.tooltip_labels.append({
            'ax': ax,
            'x_data': np.asarray(x_data),
            'y_data': np.asarray(y_data),
            'labels': labels,
            'artists': artists,
            'formatter': formatter
        })
        
        # Identificador único para este eje
        ax_id = id(ax)
        
        # Crear o actualizar los datos de tooltip para este eje
        if ax_id not in self.tooltip_data:
            self.tooltip_data[ax_id] = {'x': [], 'y': [], 'labels': [], 'highlight_colors': []}
            
        # Agregar los nuevos datos
        self.tooltip_data[ax_id]['x'].extend(x_data)
        self.tooltip_data[ax_id]['y'].extend(y_data)
        
        # Manejar el caso donde labels es None
        if labels is not None:
            self.tooltip_data[ax_id]['labels'].extend(labels)
        else:
            # Si no hay etiquetas, crear etiquetas vacías o basadas en el formatter
            if formatter is not None:
                self.tooltip_data[ax_id]['labels'].extend([None] * len(x_data))
            else:
                # Etiquetas genéricas si no hay formatter ni labels
                self.tooltip_data[ax_id]['labels'].extend([f"Punto {i+1}" for i in range(len(x_data))])
        
        # Manejar colores de resaltado
        if highlight_colors is not None:
            # Verificar si highlight_colors es una lista o un solo color
            if isinstance(highlight_colors, list):
                self.tooltip_data[ax_id]['highlight_colors'].extend(highlight_colors)
            else:
                # Si es un solo color, aplicarlo a todos los puntos
                self.tooltip_data[ax_id]['highlight_colors'].extend([highlight_colors] * len(x_data))
        else:
            # Valor por defecto si no se especifican colores
            self.tooltip_data[ax_id]['highlight_colors'].extend([None] * len(x_data))
        
        # Actualizar contador de datos para optimizar rendimiento
        self._dataset_size += len(x_data)
        
        # Optimizar umbral de distancia basado en el tamaño del dataset
        if self._dataset_size > 500:
            self._optimize_tooltip_data(ax_id)
    
    def _optimize_tooltip_data(self, ax_id):
        """Optimiza los datos de tooltip para grandes conjuntos de datos usando KD-Tree."""
        try:
            data = self.tooltip_data[ax_id]
            points = np.column_stack([data['x'], data['y']])
            
            # Crear KD-Tree para búsquedas eficientes de puntos cercanos
            if len(points) > 0:
                data['kdtree'] = cKDTree(points)
                data['using_kdtree'] = True
        except ImportError:
            # Si scipy no está disponible, usar el método estándar
            data['using_kdtree'] = False
    
    def _on_mouse_move(self, event):
        """Maneja el evento de movimiento del mouse para mostrar tooltips."""
        if not event.inaxes or not self.tooltip_enabled:
            self._clear_hover_annotation()
            return
            
        # Guardar posición del mouse para uso futuro
        self._mouse_position = event
        
        # Implementar throttling para evitar demasiadas actualizaciones
        current_time = time.time() * 1000  # Convertir a ms
        if current_time - self.last_tooltip_time < self.tooltip_delay:
            return
        
        self.last_tooltip_time = current_time
        self._process_tooltip(event)
    
    def _process_tooltip(self, event):
        """Procesa lógica de tooltips con optimizaciones de rendimiento."""
        if not event or not event.inaxes:
            self._clear_hover_annotation()
            return
            
        # Ocultar cualquier tooltip anterior
        self._clear_hover_annotation()
        
        # Verificar todos los conjuntos de datos registrados
        for data_set in self.tooltip_labels:
            if event.inaxes != data_set['ax']:
                continue
                
            # Encontrar el punto más cercano al cursor
            x, y = event.xdata, event.ydata
            x_data = data_set['x_data']
            y_data = data_set['y_data']
            
            # Solo procesar si tenemos datos
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            
            # Optimizar búsqueda para grandes conjuntos de datos
            if len(x_data) > 500 and KDTREE_AVAILABLE:
                # Usar KDTree para búsqueda eficiente de vecinos más cercanos
                points = np.column_stack([x_data, y_data])
                tree = cKDTree(points)
                dist, min_idx = tree.query([x, y], k=1)
            else:
                # Método estándar para conjuntos pequeños
                distances = np.sqrt((x_data - x)**2 + (y_data - y)**2)
                min_idx = np.argmin(distances)
                dist = distances[min_idx]
            
            # Solo mostrar tooltip si el punto está lo suficientemente cerca
            # Adaptamos el umbral según el tamaño del gráfico
            threshold = 0.02 * max(
                event.inaxes.get_xlim()[1] - event.inaxes.get_xlim()[0],
                event.inaxes.get_ylim()[1] - event.inaxes.get_ylim()[0]
            )
            
            if dist > threshold:
                continue
            
            # Obtener los valores del punto más cercano
            point_x = x_data[min_idx]
            point_y = y_data[min_idx]
            
            # Formatear el texto del tooltip
            formatter = data_set.get('formatter')
            if formatter:
                tooltip_text = formatter(point_x, point_y)
            else:
                x_value = point_x
                y_value = point_y
                
                # Aplicar formato específico si es monetario
                if self.tooltip_format.startswith('$'):
                    y_value = self.tooltip_format.format(value=y_value)
                
                tooltip_text = f"X: {x_value}\nY: {y_value}"
                
                # Usar etiquetas personalizadas si están disponibles
                if data_set.get('labels') and min_idx < len(data_set['labels']):
                    label = data_set['labels'][min_idx]
                    if label:
                        tooltip_text = f"{label}\n{tooltip_text}"
            
            # Verificar si hay un color de resaltado específico
            highlight_color = None
            if data_set.get('highlight_colors') and min_idx < len(data_set['highlight_colors']):
                highlight_color = data_set['highlight_colors'][min_idx]
            
            # Crear anotación del tooltip
            self._show_tooltip(event.inaxes, point_x, point_y, tooltip_text, highlight_color)
            
            # Resaltar el artista correspondiente si está disponible
            if data_set.get('artists') and min_idx < len(data_set['artists']):
                self._highlight_artist(data_set['artists'][min_idx])
            
            break  # Solo mostramos un tooltip a la vez
            
    def add_tooltip_data(self, ax, x_data, y_data, labels=None, artists=None, formatter=None, highlight_colors=None, highlight_color=None):
        """
        Agrega datos para mostrar en tooltips cuando el usuario pasa el mouse sobre ellos.
        
        Args:
            ax (Axes): Objeto Axes al que pertenecen los datos
            x_data (array-like): Datos del eje X
            y_data (array-like): Datos del eje Y
            labels (list, optional): Etiquetas para cada punto de datos
            artists (list, optional): Artistas de matplotlib asociados con los datos
            formatter (func, optional): Función para formatear los valores en el tooltip
            highlight_colors (list, optional): Colores específicos para resaltar cada punto
        """
        # Manejar el caso donde se proporciona highlight_color (singular) en lugar de highlight_colors (plural)
        if highlight_color is not None and highlight_colors is None:
            highlight_colors = highlight_color
            
        self.tooltip_labels.append({
            'ax': ax,
            'x_data': np.asarray(x_data),
            'y_data': np.asarray(y_data),
            'labels': labels,
            'artists': artists,
            'formatter': formatter,
            'highlight_colors': highlight_colors  # Almacenar los colores de resaltado
        })
        
        # Identificador único para este eje
        ax_id = id(ax)
        
        # Crear o actualizar los datos de tooltip para este eje
        if ax_id not in self.tooltip_data:
            self.tooltip_data[ax_id] = {'x': [], 'y': [], 'labels': [], 'highlight_colors': []}
            
        # Agregar los nuevos datos
        self.tooltip_data[ax_id]['x'].extend(x_data)
        self.tooltip_data[ax_id]['y'].extend(y_data)
        
        # Manejar el caso donde labels es None
        if labels is not None:
            self.tooltip_data[ax_id]['labels'].extend(labels)
        else:
            # Si no hay etiquetas, crear etiquetas vacías o basadas en el formatter
            if formatter is not None:
                self.tooltip_data[ax_id]['labels'].extend([None] * len(x_data))
            else:
                # Etiquetas genéricas si no hay formatter ni labels
                self.tooltip_data[ax_id]['labels'].extend([f"Punto {i+1}" for i in range(len(x_data))])
        
        # Manejar colores de resaltado
        if highlight_colors is not None:
            # Verificar si highlight_colors es una lista o un solo color
            if isinstance(highlight_colors, list):
                self.tooltip_data[ax_id]['highlight_colors'].extend(highlight_colors)
            else:
                # Si es un solo color, aplicarlo a todos los puntos
                self.tooltip_data[ax_id]['highlight_colors'].extend([highlight_colors] * len(x_data))
        else:
            # Valor por defecto si no se especifican colores
            self.tooltip_data[ax_id]['highlight_colors'].extend([None] * len(x_data))
        
        # Actualizar contador de datos para optimizar rendimiento
        self._dataset_size += len(x_data)
        
        # Optimizar umbral de distancia basado en el tamaño del dataset
        if self._dataset_size > 500:
            self._optimize_tooltip_data(ax_id)

    def _optimize_tooltip_data(self, ax_id):
        """Optimiza los datos de tooltip para grandes conjuntos de datos usando KD-Tree."""
        try:
            data = self.tooltip_data[ax_id]
            points = np.column_stack([data['x'], data['y']])
            
            # Crear KD-Tree para búsquedas eficientes de puntos cercanos
            if len(points) > 0:
                data['kdtree'] = cKDTree(points)
                data['using_kdtree'] = True
        except ImportError:
            # Si scipy no está disponible, usar el método estándar
            data['using_kdtree'] = False

    def _on_mouse_move(self, event):
        """Maneja el evento de movimiento del mouse para mostrar tooltips."""
        if not event.inaxes or not self.tooltip_enabled:
            self._clear_hover_annotation()
            return
            
        # Guardar posición del mouse para uso futuro
        self._mouse_position = event
        
        # Implementar throttling para evitar demasiadas actualizaciones
        current_time = time.time() * 1000  # Convertir a ms
        if current_time - self.last_tooltip_time < self.tooltip_delay:
            return
        
        self.last_tooltip_time = current_time
        self._process_tooltip(event)

    def _process_tooltip(self, event):
        """Procesa lógica de tooltips con optimizaciones de rendimiento."""
        if not event or not event.inaxes:
            self._clear_hover_annotation()
            return
            
        # Ocultar cualquier tooltip anterior
        self._clear_hover_annotation()
        
        # Verificar todos los conjuntos de datos registrados
        for data_set in self.tooltip_labels:
            if event.inaxes != data_set['ax']:
                continue
                
            # Encontrar el punto más cercano al cursor
            x, y = event.xdata, event.ydata
            x_data = data_set['x_data']
            y_data = data_set['y_data']
            
            # Solo procesar si tenemos datos
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            
            # Optimizar búsqueda para grandes conjuntos de datos
            if len(x_data) > 500 and KDTREE_AVAILABLE:
                # Usar KDTree para búsqueda eficiente de vecinos más cercanos
                points = np.column_stack([x_data, y_data])
                tree = cKDTree(points)
                dist, min_idx = tree.query([x, y], k=1)
            else:
                # Método estándar para conjuntos pequeños
                distances = np.sqrt((x_data - x)**2 + (y_data - y)**2)
                min_idx = np.argmin(distances)
                dist = distances[min_idx]
            
            # Solo mostrar tooltip si el punto está lo suficientemente cerca
            # Adaptamos el umbral según el tamaño del gráfico
            threshold = 0.02 * max(
                event.inaxes.get_xlim()[1] - event.inaxes.get_xlim()[0],
                event.inaxes.get_ylim()[1] - event.inaxes.get_ylim()[0]
            )
            
            if dist > threshold:
                continue
            
            # Obtener los valores del punto más cercano
            point_x = x_data[min_idx]
            point_y = y_data[min_idx]
            
            # Formatear el texto del tooltip
            formatter = data_set.get('formatter')
            if formatter:
                tooltip_text = formatter(point_x, point_y)
            else:
                x_value = point_x
                y_value = point_y
                
                # Aplicar formato específico si es monetario
                if self.tooltip_format.startswith('$'):
                    y_value = self.tooltip_format.format(value=y_value)
                
                tooltip_text = f"X: {x_value}\nY: {y_value}"
                
                # Usar etiquetas personalizadas si están disponibles
                if data_set.get('labels') and min_idx < len(data_set['labels']):
                    label = data_set['labels'][min_idx]
                    if label:
                        tooltip_text = f"{label}\n{tooltip_text}"
            
            # Verificar si hay un color de resaltado específico
            highlight_color = None
            if data_set.get('highlight_colors') and min_idx < len(data_set['highlight_colors']):
                highlight_color = data_set['highlight_colors'][min_idx]
            
            # Crear anotación del tooltip
            self._show_tooltip(event.inaxes, point_x, point_y, tooltip_text, highlight_color)
            
            # Resaltar el artista correspondiente si está disponible
            if data_set.get('artists') and min_idx < len(data_set['artists']):
                self._highlight_artist(data_set['artists'][min_idx])
            
            break  # Solo mostramos un tooltip a la vez
    
    def _on_axes_leave(self, event):
        """Maneja el evento cuando el mouse sale del área de los ejes."""
        self._clear_hover_annotation()
    
    def _show_tooltip(self, ax, x, y, text, highlight_color=None):
        """Muestra un tooltip en la posición especificada."""
        # Limpiar cualquier anotación anterior
        self._clear_hover_annotation()
        
        # Definir una lista de colores válidos predeterminados para usar cuando hay problemas
        default_colors = ['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black', 'gray']
        
        # Validar que el color de resaltado sea válido
        valid_color = 'gray'  # Color predeterminado
        
        if highlight_color is not None:
            try:
                # Intentar importar el módulo de colores de matplotlib para validación
                from matplotlib.colors import to_rgba
                
                # Usar un bloque try-except para validar si es un color válido
                try:
                    # Si esto no lanza una excepción, el color es válido
                    to_rgba(highlight_color)
                    valid_color = highlight_color
                except (ValueError, TypeError):
                    # Si hay un error, el color no es válido - usamos el predeterminado
                    if isinstance(highlight_color, (int, float)):
                        # Si es un número, usar un color predeterminado
                        valid_color = default_colors[0]
                    elif isinstance(highlight_color, str) and highlight_color.isdigit():
                        # Si es un string numérico, usar un color predeterminado
                        valid_color = default_colors[0]
                    elif isinstance(highlight_color, str) and highlight_color in ['o', '*', 'x', '+', 'D', '.', 'v', '^']:
                        # Si es un marcador, usar un color predeterminado
                        valid_color = default_colors[0]
            except ImportError:
                # Si no se puede importar el módulo de colores, usar el predeterminado
                valid_color = 'gray'
        
        # Configurar propiedades visuales del tooltip
        props = dict(
            boxstyle='round,pad=0.5',
            facecolor='white',
            edgecolor=valid_color,
            alpha=0.9
        )
        
        # Crear anotación
        self.hover_artist = ax.annotate(
            text,
            xy=(x, y),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=props,
            zorder=100
        )
        self.figure.canvas.draw_idle()
    
    def _highlight_artist(self, artist):
        """Resalta un artista específico (punto, línea, etc.)."""
        if hasattr(artist, 'set_linewidth'):
            self._original_linewidth = artist.get_linewidth()
            artist.set_linewidth(self._original_linewidth * 2)
        
        if hasattr(artist, 'set_markeredgewidth'):
            self._original_markeredgewidth = artist.get_markeredgewidth()
            artist.set_markeredgewidth(self._original_markeredgewidth * 2)
        
        if hasattr(artist, 'set_markeredgecolor'):
            self._original_markeredgecolor = artist.get_markeredgecolor()
            artist.set_markeredgecolor('red')
        
        if hasattr(artist, 'set_markersize'):
            self._original_markersize = artist.get_markersize()
            artist.set_markersize(self._original_markersize * 1.5)
        
        self.figure.canvas.draw_idle()
    
    def _clear_hover_annotation(self):
        """Limpia cualquier tooltip activo."""
        if self.hover_artist:
            self.hover_artist.remove()
            self.hover_artist = None
            self.figure.canvas.draw_idle()
    
    def create_toolbar(self, parent):
        """
        Crea una barra de herramientas para el canvas si no existe.
        
        Args:
            parent (QWidget): Widget padre para la toolbar.
        """
        if self.toolbar is None:
            self.toolbar = NavigationToolbar(self, parent)
            return self.toolbar
        return self.toolbar
        
    def get_toolbar(self):
        """Devuelve la barra de herramientas asociada."""
        return self.toolbar
