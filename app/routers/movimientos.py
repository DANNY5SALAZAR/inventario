# app/routers/movimientos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from fastapi.responses import Response
from ..utils.pdf_generator import PDFGenerator
import pandas as pd
import io
import json

# Importaciones locales
from .. import crud, schemas, models  # Añadí 'models' aquí
from ..database import get_db

router = APIRouter(prefix="/movimientos", tags=["movimientos"])

@router.get("/", response_model=List[schemas.Movimiento])
def leer_movimientos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de todos los movimientos.
    """
    movimientos = crud.get_movimientos(db, skip=skip, limit=limit)
    return movimientos

@router.get("/producto/{producto_id}", response_model=List[schemas.Movimiento])
def leer_movimientos_producto(
    producto_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener movimientos de un producto específico.
    """
    movimientos = crud.get_movimientos_por_producto(db, producto_id=producto_id)
    return movimientos

@router.post("/", response_model=schemas.Movimiento)
def crear_movimiento(
    movimiento: schemas.MovimientoCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo movimiento (entrada o salida).
    """
    try:
        return crud.crear_movimiento(db=db, movimiento=movimiento)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/entrada-rapida")
def entrada_rapida(
    producto_id: int,
    cantidad: int,
    motivo: str = "Entrada rápida",
    db: Session = Depends(get_db)
):
    """
    Registrar una entrada rápida de productos.
    """
    movimiento = schemas.MovimientoCreate(
        producto_id=producto_id,
        tipo="entrada",
        cantidad=cantidad,
        motivo=motivo,
        usuario="admin"
    )
    
    try:
        resultado = crud.crear_movimiento(db=db, movimiento=movimiento)
        return {
            "message": "Entrada registrada exitosamente",
            "movimiento_id": resultado.id,
            "stock_actual": resultado.producto.stock_actual
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/salida-rapida")
def salida_rapida(
    producto_id: int,
    cantidad: int,
    motivo: str = "Salida rápida",
    db: Session = Depends(get_db)
):
    """
    Registrar una salida rápida de productos.
    """
    movimiento = schemas.MovimientoCreate(
        producto_id=producto_id,
        tipo="salida",
        cantidad=cantidad,
        motivo=motivo,
        usuario="admin"
    )
    
    try:
        resultado = crud.crear_movimiento(db=db, movimiento=movimiento)
        return {
            "message": "Salida registrada exitosamente",
            "movimiento_id": resultado.id,
            "stock_actual": resultado.producto.stock_actual
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/salida-multiple", response_model=List[schemas.Movimiento])
def crear_salida_multiple(
    salida: schemas.SalidaMultipleCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una salida con múltiples productos.
    """
    try:
        # Preparar lista de productos
        productos_lista = [
            {
                'producto_id': item['producto_id'],
                'cantidad': item['cantidad']
            }
            for item in salida.productos
        ]
        
        # Usar la nueva función de crud
        movimientos = crud.crear_salida_multiple(
            db=db,
            productos=productos_lista,
            destino=salida.destino,
            razon=salida.razon,
            observaciones=salida.observaciones,
            usuario=salida.usuario
        )
        
        return movimientos
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/generar-pdf-salida")
def generar_pdf_salida_endpoint(
    salida_data: dict,  # Cambiamos a dict para más flexibilidad
    db: Session = Depends(get_db)
):
    """
    Generar PDF de comprobante de salida.
    """
    try:
        # Extraer datos
        productos = salida_data.get('productos', [])
        destino = salida_data.get('destino', 'No especificado')
        razon = salida_data.get('razon', 'Salida de inventario')
        observaciones = salida_data.get('observaciones', '')
        usuario = salida_data.get('usuario', 'admin')
        kit_nombre = salida_data.get('kit_nombre')
        
        # Preparar información de productos para el PDF
        productos_info = []
        
        for item in productos:
            producto_id = item.get('producto_id')
            cantidad = item.get('cantidad')
            
            if producto_id:
                producto = crud.get_producto(db, producto_id=producto_id)
                if producto:
                    producto_info = {
                        'producto_nombre': producto.nombre,
                        'producto_codigo': producto.codigo,
                        'cantidad': cantidad
                    }
                    
                    # Si es kit, agregar información adicional
                    if kit_nombre and 'cantidad_por_kit' in item:
                        producto_info['cantidad_por_kit'] = item['cantidad_por_kit']
                        producto_info['cantidad_total'] = cantidad
                    
                    productos_info.append(producto_info)
                else:
                    productos_info.append({
                        'producto_nombre': f"Producto ID {producto_id}",
                        'producto_codigo': 'N/A',
                        'cantidad': cantidad
                    })
        
        # Preparar datos de la salida
        datos_salida = {
            'destino': destino,
            'razon': razon,
            'observaciones': observaciones,
            'usuario': usuario,
            'fecha': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'kit_nombre': kit_nombre
        }
        
        # Generar PDF
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generar_comprobante_salida(datos_salida, productos_info)
        
        # Crear nombre de archivo
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if kit_nombre:
            nombre_base = f"kit_{kit_nombre}"
        else:
            nombre_base = f"salida_{destino}"
        
        # Limpiar nombre para archivo
        nombre_limpio = "".join([c for c in nombre_base if c.isalnum() or c in [' ', '_', '-']])[:30]
        nombre_limpio = nombre_limpio.replace(' ', '_')
        
        filename = f"{nombre_limpio}_{fecha_str}.pdf"
        
        # Devolver PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
    
@router.get("/exportar/excel")
def exportar_movimientos_excel(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Exportar movimientos a Excel.
    """
    try:
        print(f"=== INICIANDO EXPORTACIÓN EXCEL ===")
        print(f"Filtros: inicio={fecha_inicio}, fin={fecha_fin}, tipo={tipo}")
        
        # Obtener movimientos con sus productos (usar join para mejor performance)
        query = db.query(models.Movimiento).join(models.Producto)
        
        if fecha_inicio:
            try:
                # Convertir string a fecha
                fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                query = query.filter(models.Movimiento.fecha_movimiento >= fecha_inicio_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha inicio inválido. Use YYYY-MM-DD")
        
        if fecha_fin:
            try:
                # Convertir string a fecha y agregar 23:59:59
                fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
                fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(models.Movimiento.fecha_movimiento <= fecha_fin_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha fin inválido. Use YYYY-MM-DD")
        
        if tipo:
            query = query.filter(models.Movimiento.tipo == tipo)
        
        movimientos = query.order_by(models.Movimiento.fecha_movimiento.desc()).all()
        print(f"Total movimientos encontrados: {len(movimientos)}")
        
        if not movimientos:
            # Devolver un Excel vacío con mensaje
            df = pd.DataFrame({"Mensaje": ["No hay movimientos para exportar con los filtros aplicados"]})
        else:
            # Convertir a DataFrame de pandas
            data = []
            for mov in movimientos:
                producto_nombre = mov.producto.nombre if mov.producto else "Producto eliminado"
                productoCodigo = mov.producto.codigo if mov.producto else "N/A"
                stockActual = mov.producto.stock_actual if mov.producto else 0
                
                # Calcular stock anterior
                stockAnterior = 0
                if mov.producto:
                    if mov.tipo == "salida":
                        stockAnterior = stockActual + mov.cantidad
                    elif mov.tipo == "entrada":
                        stockAnterior = stockActual - mov.cantidad
                
                # Determinar origen/destino
                origenDestino = ""
                if mov.tipo == "entrada":
                    origenDestino = mov.origen_nombre or "-"
                else:
                    origenDestino = mov.cliente_destino or "-"
                
                data.append({
                    "ID": mov.id,
                    "Fecha": mov.fecha_movimiento.strftime("%Y-%m-%d %H:%M:%S"),
                    "Tipo": "ENTRADA" if mov.tipo == "entrada" else "SALIDA",
                    "Producto ID": mov.producto_id,
                    "Código Producto": productoCodigo,
                    "Nombre Producto": producto_nombre,
                    "Cantidad": mov.cantidad,
                    "Motivo": mov.motivo or "-",
                    "Proveedor/Cliente": origenDestino,
                    "Ubicación": mov.ubicacion or "-",
                    "Tipo Origen": mov.tipo_origen or "-",
                    "Notas": mov.notas or "-",
                    "Usuario": mov.usuario or "admin",
                    "Stock Anterior": stockAnterior,
                    "Stock Actual": stockActual,
                    "Diferencia": f"+{mov.cantidad}" if mov.tipo == "entrada" else f"-{mov.cantidad}"
                })
            
            df = pd.DataFrame(data)
            print(f"DataFrame creado con {len(df)} filas y {len(df.columns)} columnas")
        
        # Crear Excel en memoria
        output = io.BytesIO()
        
        # Usar ExcelWriter con openpyxl
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja principal de movimientos
            df.to_excel(writer, sheet_name='Movimientos', index=False)
            
            # Ajustar ancho de columnas automáticamente
            worksheet = writer.sheets['Movimientos']
            
            for column in df.columns:
                # Encontrar la longitud máxima en la columna
                max_length = 0
                col_idx = df.columns.get_loc(column)
                
                # Longitud del encabezado
                max_length = max(max_length, len(str(column)))
                
                # Longitud de los datos
                if len(df) > 0:
                    column_data = df[column].astype(str)
                    max_length = max(max_length, column_data.map(len).max())
                
                # Limitar ancho máximo a 50 caracteres
                adjusted_width = min(max_length + 2, 50)
                
                # Aplicar ancho a la columna
                col_letter = chr(65 + col_idx)  # A, B, C, ...
                worksheet.column_dimensions[col_letter].width = adjusted_width
            
            # Formato de celdas para números
            for row in worksheet.iter_rows(min_row=2, max_row=len(df)+1):
                # Columna Cantidad (columna G, índice 6)
                row[6].number_format = '#,##0'
                # Columnas Stock (índices 13 y 14)
                if len(row) > 13:
                    row[13].number_format = '#,##0'
                    row[14].number_format = '#,##0'
            
            # Agregar una hoja de resumen si hay datos
            if len(movimientos) > 0:
                # Crear resumen
                resumen_data = {
                    "Estadística": [
                        "Total Movimientos",
                        "Total Entradas", 
                        "Total Salidas",
                        "Unidades Entrantes",
                        "Unidades Salientes",
                        "Balance Neto"
                    ],
                    "Valor": [
                        len(movimientos),
                        len([m for m in movimientos if m.tipo == "entrada"]),
                        len([m for m in movimientos if m.tipo == "salida"]),
                        sum(m.cantidad for m in movimientos if m.tipo == "entrada"),
                        sum(m.cantidad for m in movimientos if m.tipo == "salida"),
                        sum(m.cantidad for m in movimientos if m.tipo == "entrada") - 
                        sum(m.cantidad for m in movimientos if m.tipo == "salida")
                    ]
                }
                resumen_df = pd.DataFrame(resumen_data)
                resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
        
        output.seek(0)
        
        # Nombre del archivo
        fecha_descarga = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimientos_inventario_{fecha_descarga}.xlsx"
        
        print(f"=== EXPORTACIÓN COMPLETADA: {filename} ===")
        
        # Devolver archivo Excel
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"=== ERROR EN EXPORTACIÓN ===")
        print(error_details)
        raise HTTPException(
            status_code=500, 
            detail=f"Error al generar archivo Excel: {str(e)}"
        )
@router.get("/salida/{salida_id}/pdf")
def generar_pdf_salida(salida_id: int, db: Session = Depends(get_db)):
    """
    Generar PDF de comprobante de salida.
    """
    try:
        # Obtener todos los movimientos de esta salida
        # (Necesitas tener un campo para agrupar salidas)
        movimientos = db.query(models.Movimiento).filter(
            # Aquí necesitas filtrar por el ID de la salida
            # Depende de cómo estés agrupando los movimientos
        ).all()
        
        if not movimientos:
            raise HTTPException(status_code=404, detail="Salida no encontrada")
        
        # Datos de la salida (del primer movimiento o de una tabla Salida)
        primer_movimiento = movimientos[0]
        salida_data = {
            'destino': primer_movimiento.cliente_destino or "No especificado",
            'razon': primer_movimiento.motivo or "No especificada",
            'observaciones': primer_movimiento.notas or "",
            'usuario': primer_movimiento.usuario or "admin",
            'fecha': primer_movimiento.fecha_movimiento.strftime("%d/%m/%Y")
        }
        
        # Generar PDF
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generar_comprobante_salida(salida_data, movimientos)
        
        # Devolver PDF
        filename = f"comprobante_salida_{salida_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
@router.post("/salida-multiple", response_model=List[schemas.Movimiento])
def crear_salida_multiple(
    salida: schemas.SalidaMultipleCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una salida con múltiples productos.
    """
    try:
        # Preparar lista de productos
        productos_lista = [
            {
                'producto_id': item['producto_id'],
                'cantidad': item['cantidad']
            }
            for item in salida.productos
        ]
        
        # Usar la nueva función de crud
        movimientos = crud.crear_salida_multiple(
            db=db,
            productos=productos_lista,
            destino=salida.destino,
            razon=salida.razon,
            observaciones=salida.observaciones,
            usuario=salida.usuario
        )
        
        # Generar PDF automáticamente (opcional)
        # pdf_generator = PDFGenerator()
        # pdf_bytes = pdf_generator.generar_comprobante_salida(
        #     {
        #         'destino': salida.destino,
        #         'razon': salida.razon,
        #         'observaciones': salida.observaciones,
        #         'usuario': salida.usuario
        #     },
        #     movimientos
        # )
        # Guardar PDF en disco o devolverlo
        
        return movimientos
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")