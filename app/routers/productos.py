# app/routers/productos.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas
from ..database import get_db
from ..utils.codigos import generar_codigo_barras, generar_qr_code, generar_codigo_producto
from fastapi.responses import JSONResponse
from fastapi import status
import pandas as pd
import io
from typing import List
import chardet

router = APIRouter(prefix="/productos", tags=["productos"])

@router.get("/", response_model=List[schemas.Producto])
def leer_productos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de todos los productos.
    """
    productos = crud.get_productos(db, skip=skip, limit=limit)
    return productos

@router.get("/buscar", response_model=List[schemas.Producto])
def buscar_productos(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    db: Session = Depends(get_db)
):
    """
    Buscar productos por nombre, código o descripción.
    """
    print(f"=== BUSQUEDA RECIBIDA ===")
    print(f"Término: {q}")
    print(f"Tipo: {type(q)}")
    
    productos = crud.buscar_productos(db, query=q)
    
    print(f"Productos encontrados: {len(productos)}")
    for p in productos:
        print(f"  - {p.codigo}: {p.nombre}")
    
    return productos
@router.get("/{producto_id}", response_model=schemas.Producto)
def leer_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtener un producto por su ID.
    """
    db_producto = crud.get_producto(db, producto_id=producto_id)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.get("/codigo/{codigo}", response_model=schemas.Producto)
def leer_producto_por_codigo(codigo: str, db: Session = Depends(get_db)):
    """
    Obtener un producto por su código.
    """
    db_producto = crud.get_producto_por_codigo(db, codigo=codigo)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.post("/", response_model=schemas.Producto, status_code=status.HTTP_201_CREATED)
def crear_producto(
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo producto.
    Si no se proporciona código, se generará automáticamente.
    """
    # Verificar si el código ya existe
    if producto.codigo:
        existente = crud.get_producto_por_codigo(db, codigo=producto.codigo)
        if existente:
            raise HTTPException(status_code=400, detail="El código ya existe")

    nuevo_producto = crud.crear_producto(db=db, producto=producto)
    return nuevo_producto

@router.put("/{producto_id}", response_model=schemas.Producto)
def actualizar_producto(
    producto_id: int,
    producto: schemas.ProductoUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar un producto existente.
    """
    db_producto = crud.actualizar_producto(db, producto_id=producto_id, producto=producto)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.delete("/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Eliminar un producto.
    """
    success = crud.eliminar_producto(db, producto_id=producto_id)
    if not success:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado exitosamente"}

@router.get("/{producto_id}/codigo-barras")
def obtener_codigo_barras(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtener imagen de código de barras para un producto.
    """
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    barcode = generar_codigo_barras(producto.codigo)
    if not barcode:
        raise HTTPException(status_code=500, detail="Error generando código de barras")
    
    return {"codigo_barras": barcode}

@router.get("/{producto_id}/qr-code")
def obtener_qr_code(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtener código QR para un producto.
    """
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    qr = generar_qr_code(producto.codigo, {"nombre": producto.nombre, "precio": producto.precio_unitario})
    if not qr:
        raise HTTPException(status_code=500, detail="Error generando código QR")
    
    return {"qr_code": qr}

@router.post("/cargar-excel")
async def cargar_productos_excel(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Carga masiva de productos desde archivo Excel o CSV
    El archivo DEBE tener columna 'codigo' (único) y 'nombre'
    """
    try:
        # Validar extensión
        if not (archivo.filename.endswith('.xlsx') or 
                archivo.filename.endswith('.xls') or 
                archivo.filename.endswith('.csv')):
            raise HTTPException(400, "Formato no soportado. Use .xlsx, .xls o .csv")
        
        print(f"📁 Procesando archivo: {archivo.filename}")
        
        # Leer archivo
        contents = await archivo.read()
        
        # Procesar según extensión
        if archivo.filename.endswith('.csv'):
            encoding = chardet.detect(contents)['encoding'] or 'utf-8'
            print(f"📄 Encoding detectado: {encoding}")
            df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        print(f"📊 Filas leídas: {len(df)}")
        print(f"📋 Columnas: {list(df.columns)}")
        
        # Validar columnas obligatorias
        if 'codigo' not in df.columns:
            raise HTTPException(400, "El archivo debe tener una columna 'codigo'")
        
        if 'nombre' not in df.columns:
            raise HTTPException(400, "El archivo debe tener una columna 'nombre'")
        
        # Validar que no haya códigos duplicados en el Excel
        codigos_excel = df['codigo'].astype(str).str.strip().tolist()
        codigos_duplicados = [c for c in set(codigos_excel) if codigos_excel.count(c) > 1]
        
        if codigos_duplicados:
            raise HTTPException(400, 
                f"Códigos duplicados en el Excel: {', '.join(codigos_duplicados[:5])}")
        
        # Validar que los códigos no existan ya en la BD
        from .. import models
        
        codigos_existentes = []
        for codigo in codigos_excel:
            if codigo and codigo != 'nan':
                existe = db.query(models.Producto).filter(
                    models.Producto.codigo == codigo
                ).first()
                if existe:
                    codigos_existentes.append(codigo)
        
        if codigos_existentes:
            raise HTTPException(400, 
                f"Los siguientes códigos ya existen en la BD: {', '.join(codigos_existentes[:5])}")
        
        # Preparar resultados
        resultados = []
        exitosos = 0
        fallidos = 0
        
        for idx, row in df.iterrows():
            try:
                # Obtener código (obligatorio)
                codigo = str(row['codigo']).strip()
                if not codigo or codigo == 'nan' or codigo == '':
                    raise ValueError(f"Código vacío en fila {idx+2}")
                
                # Validar nombre
                nombre = str(row['nombre']).strip()
                if not nombre or nombre == 'nan' or nombre == '':
                    raise ValueError(f"Nombre vacío en fila {idx+2} (código: {codigo})")
                
                # Crear producto con el código proporcionado
                producto = models.Producto(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=str(row.get('descripcion', '')) if pd.notna(row.get('descripcion', '')) else '',
                    categoria=str(row.get('categoria', '')) if pd.notna(row.get('categoria', '')) else '',
                    stock_minimo=int(row.get('stock_minimo', 0)) if pd.notna(row.get('stock_minimo', 0)) else 0,
                    stock_actual=0
                )
                
                db.add(producto)
                db.flush()
                
                resultados.append({
                    "codigo": codigo,
                    "nombre": nombre,
                    "categoria": producto.categoria,
                    "exitoso": True,
                    "error": None
                })
                exitosos += 1
                
            except Exception as e:
                print(f"❌ Error fila {idx+2}: {str(e)}")
                resultados.append({
                    "codigo": row.get('codigo', f'Fila {idx+2}'),
                    "nombre": row.get('nombre', ''),
                    "categoria": row.get('categoria', ''),
                    "exitoso": False,
                    "error": str(e)
                })
                fallidos += 1
        
        # Commit final
        db.commit()
        
        return {
            "total": len(resultados),
            "exitosos": exitosos,
            "fallidos": fallidos,
            "productos": resultados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error procesando archivo: {str(e)}")