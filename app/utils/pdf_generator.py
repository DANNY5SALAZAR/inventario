# app/utils/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from datetime import datetime
import io
import os

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.page_size = A4
        
    def generar_comprobante_salida(self, salida_data, productos_data):
        """
        Genera un comprobante de salida PDF.
        
        Args:
            salida_data: dict con {
                'destino': str,
                'razon': str,
                'observaciones': str,
                'usuario': str,
                'kit_nombre': str (opcional),
                'fecha': str (opcional)
            }
            productos_data: lista de dicts con {
                'producto_nombre': str,
                'producto_codigo': str,
                'cantidad': int,
                'cantidad_por_kit': int (opcional),
                'cantidad_total': int (opcional)
            }
        
        Returns:
            bytes del PDF
        """
        # Crear buffer para el PDF
        buffer = io.BytesIO()
        
        # Crear documento
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=self.page_size,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Elementos del documento
        story = []
        
        # 1. ENCABEZADO
        story.extend(self._crear_encabezado())
        story.append(Spacer(1, 1*cm))
        
        # 2. INFORMACIÓN DE LA SALIDA
        story.extend(self._crear_info_salida(salida_data))
        story.append(Spacer(1, 0.5*cm))
        
        # 3. TABLA DE PRODUCTOS
        story.extend(self._crear_tabla_productos(productos_data, salida_data))
        story.append(Spacer(1, 1*cm))
        
        # 4. OBSERVACIONES
        if salida_data.get('observaciones'):
            story.extend(self._crear_observaciones(salida_data['observaciones']))
            story.append(Spacer(1, 0.5*cm))
        
        # 5. FIRMAS
        story.extend(self._crear_seccion_firmas())
        
        # 6. PIE DE PÁGINA
        story.append(Spacer(1, 1*cm))
        story.extend(self._crear_pie_pagina())
        
        # Construir PDF
        doc.build(story)
        
        # Obtener bytes del buffer
        buffer.seek(0)
        return buffer.getvalue()
    
    def _crear_encabezado(self):
        """Crea el encabezado con logo y título."""
        elements = []
        
        # Agregar logo si existe
        # Estilo para el título
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=1,  # Centrado
            spaceAfter=6,
            textColor=colors.HexColor('#1a3d7c'),  # Azul oscuro
            fontName='Helvetica-Bold'
        )
        
        # Estilo para subtítulo
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=1,
            spaceAfter=12,
            textColor=colors.HexColor('#2c5282'),
            fontName='Helvetica'
        )
        
        # Logo FIMLM (texto por ahora - puedes cambiar por imagen)
        elements.append(Paragraph("FUNDACIÓN INTERNACIONAL MARIA LUISA DE MORENO", title_style))
        elements.append(Paragraph("FIMLM", subtitle_style))
        elements.append(Paragraph("COMPROBANTE DE SALIDA DE INVENTARIO", subtitle_style))
        
        # Línea decorativa
        elements.append(Spacer(1, 0.2*cm))
        elements.append(self._crear_linea_divisoria())
        
        return elements
    
    def _crear_info_salida(self, salida_data):
        """Crea la sección de información de la salida."""
        elements = []
        
        # Estilo para información
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
            spaceAfter=3
        )
        
        fecha = salida_data.get('fecha') or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        info_text = f"""
        <b>FECHA Y HORA:</b> {fecha}<br/>
        <b>DESTINO/RESPONSABLE:</b> {salida_data.get('destino', 'No especificado')}<br/>
        <b>RAZÓN/MOTIVO:</b> {salida_data.get('razon', 'No especificada')}<br/>
        """
        
        if salida_data.get('kit_nombre'):
            info_text += f"<b>NOMBRE DEL KIT:</b> {salida_data['kit_nombre']}<br/>"
        
        info_text += f"<b>REGISTRADO POR:</b> {salida_data.get('usuario', 'Sistema')}"
        
        elements.append(Paragraph(info_text, info_style))
        return elements
    
    def _crear_tabla_productos(self, productos_data, salida_data):
        """Crea la tabla de productos."""
        elements = []
        
        # Título de la tabla
        title_style = ParagraphStyle(
            'TableTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.black
        )
        
        if salida_data.get('kit_nombre'):
            elements.append(Paragraph(f"PRODUCTOS DEL KIT: {salida_data['kit_nombre']}", title_style))
        else:
            elements.append(Paragraph("PRODUCTOS", title_style))
        
        # Preparar datos de la tabla
        table_data = []
        
        # Encabezados
        headers = ['No.', 'CÓDIGO', 'DESCRIPCIÓN', 'CANTIDAD']
        if salida_data.get('kit_nombre'):
            headers = ['No.', 'CÓDIGO', 'DESCRIPCIÓN', 'UNID/KIT', 'TOTAL']
        
        table_data.append(headers)
        
        # Datos de productos
        total_general = 0
        for i, producto in enumerate(productos_data, 1):
            row = [
                str(i),
                producto.get('producto_codigo', 'N/A'),
                producto.get('producto_nombre', 'Producto'),
            ]
            
            if salida_data.get('kit_nombre'):
                cantidad_kit = producto.get('cantidad_por_kit', 0)
                cantidad_total = producto.get('cantidad_total', 0)
                row.extend([str(cantidad_kit), str(cantidad_total)])
                total_general += cantidad_total
            else:
                cantidad = producto.get('cantidad', 0)
                row.append(str(cantidad))
                total_general += cantidad
        
            table_data.append(row)
        
        # Fila de total
        total_row = ['', '', 'TOTAL', str(total_general)]
        if salida_data.get('kit_nombre'):
            total_row = ['', '', 'TOTAL GENERAL', '', str(total_general)]
        
        table_data.append(total_row)
        
        # Crear tabla
        col_widths = [1*cm, 2.5*cm, 9*cm, 2.5*cm]
        if salida_data.get('kit_nombre'):
            col_widths = [1*cm, 2.5*cm, 7*cm, 2*cm, 2*cm]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Estilos de la tabla
        style = TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3d7c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Bordes
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('BOX', (0, -1), (-1, -1), 1.5, colors.black),
            
            # Alineación
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Código
            ('ALIGN', (-1, 1), (-1, -2), 'CENTER'),  # Cantidad
            
            # Fila total
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])
        
        table.setStyle(style)
        elements.append(table)
        
        return elements
    
    def _crear_observaciones(self, observaciones):
        """Crea la sección de observaciones."""
        elements = []
        
        obs_style = ParagraphStyle(
            'ObservacionesStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            backColor=colors.HexColor('#f8f9fa'),
            borderPadding=8,
            borderWidth=1,
            borderColor=colors.grey,
            borderRadius=3
        )
        
        obs_text = f"""
        <b>OBSERVACIONES / NOTAS ADICIONALES:</b><br/>
        {observaciones}
        """
        
        elements.append(Paragraph(obs_text, obs_style))
        return elements
    
    def _crear_seccion_firmas(self):
        """Crea la sección de firmas."""
        elements = []
        
        # Título
        title_style = ParagraphStyle(
            'FirmasTitle',
            parent=self.styles['Heading3'],
            fontSize=11,
            spaceAfter=15,
            alignment=1
        )
        
        elements.append(Paragraph("FIRMAS Y SELLOS", title_style))
        
        # Tabla de firmas
        firmas_data = [
            ['ENTREGADO POR:', 'RECIBIDO POR:', 'TRANSPORTISTA:'],
            ['', '', ''],
            ['_________________________', '_________________________', '_________________________'],
            ['Nombre y Apellido', 'Nombre y Apellido', 'Nombre y Apellido'],
            ['', '', ''],
            ['_________________________', '_________________________', '_________________________'],
            ['C.C./NIT', 'C.C./NIT', 'C.C.'],
            ['', '', ''],
            ['_________________________', '_________________________', '_________________________'],
            ['Firma / Sello', 'Firma / Sello', 'Firma / Sello'],
        ]
        
        table = Table(firmas_data, colWidths=[6*cm, 6*cm, 6*cm])
        
        style = TableStyle([
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 3), (-1, 3), 'CENTER'),  # Nombres
            ('ALIGN', (0, 6), (-1, 6), 'CENTER'),  # Documentos
            ('ALIGN', (0, 9), (-1, 9), 'CENTER'),  # Firmas
            ('SPAN', (0, 1), (2, 1)),  # Espacio
            ('SPAN', (0, 4), (2, 4)),  # Espacio
            ('SPAN', (0, 7), (2, 7)),  # Espacio
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        table.setStyle(style)
        elements.append(table)
        
        return elements
    
    def _crear_pie_pagina(self):
        """Crea el pie de página."""
        elements = []
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=1,
            textColor=colors.grey,
            spaceBefore=10
        )
        
        footer_text = """
        <b>FUNDACIÓN INTERNACIONAL MARIA LUISA DE MORENO - FIMLM</b><br/>
        Sistema de Gestión de Inventarios • Documento generado automáticamente
        """
        
        elements.append(self._crear_linea_divisoria())
        elements.append(Paragraph(footer_text, footer_style))
        
        return elements
    
    def _crear_linea_divisoria(self):
        """Crea una línea divisoria."""
        from reportlab.platypus.flowables import HRFlowable
        return HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#1a3d7c'),
            spaceBefore=5,
            spaceAfter=5
        )


# Función de conveniencia para uso rápido
def generar_pdf_salida_simple(salida_data, productos_data):
    """Función simple para generar PDF de salida."""
    generator = PDFGenerator()
    return generator.generar_comprobante_salida(salida_data, productos_data)