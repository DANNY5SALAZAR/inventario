# app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

# Esquemas para Productos
class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    #precio_unitario: float = Field(ge=0, default=0.0)
    stock_minimo: int = Field(ge=0, default=0)
    #ubicacion: Optional[str] = None

class ProductoCreate(ProductoBase):
    codigo: Optional[str] = None  # Si no se proporciona, se generará

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    #precio_unitario: Optional[float] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    #ubicacion: Optional[str] = None

class Producto(ProductoBase):
    id: int
    codigo: str
    stock_actual: int
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Esquemas para Movimientos
# app/schemas.py - Modifica MovimientoBase y MovimientoCreate
class MovimientoBase(BaseModel):
    producto_id: int
    tipo: str = Field(..., pattern="^(entrada|salida)$")
    cantidad: int = Field(..., gt=0)
    motivo: Optional[str] = None
    tipo_origen: Optional[str] = Field(
        None, description="compra, donacion, devolucion, traslado"
    )
    origen_nombre: Optional[str] = Field(
        None, description="Proveedor, donante o tercero"
    )
    ubicacion: Optional[str] = None
    notas: Optional[str] = None
    usuario: str = "admin"
    # 🆕 AGREGAR estos campos para salidas
    cliente_destino: Optional[str] = Field(
        None, description="Cliente o destino (para salidas)"
    )

class MovimientoCreate(MovimientoBase):
    pass

class Movimiento(MovimientoBase):
    id: int
    fecha_movimiento: datetime
    producto: Optional[Producto] = None
    pdf_firmado: Optional[str] = None
    pdf_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

# Esquemas para respuestas API
class InventarioProducto(BaseModel):
    producto: Producto
    historial: List[Movimiento] = []

class ReporteInventario(BaseModel):
    total_productos: int
    productos_bajo_stock: List[Producto]
    valor_total_inventario: float
    ultimos_movimientos: List[Movimiento]

# Esquema para escaneo
class CodigoEscaneado(BaseModel):
    codigo: str
    tipo_operacion: str = "consulta"  # entrada, salida, consulta
    # app/schemas.py (agregar al final)

# Esquema para múltiples productos en una salida
class SalidaMultipleCreate(BaseModel):
    productos: List[dict] = Field(..., description="Lista de productos con cantidad")
    destino: str = Field(..., min_length=1, description="Destino o responsable")
    razon: str = Field(..., min_length=1, description="Razón de la salida")
    observaciones: Optional[str] = None
    usuario: str = "admin"
    
    @validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for producto in v:
            if 'producto_id' not in producto or 'cantidad' not in producto:
                raise ValueError("Cada producto debe tener producto_id y cantidad")
            if producto['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        
        return v
    # app/schemas.py - Agregar al final

class EntradaMultipleCreate(BaseModel):
    productos: List[dict] = Field(..., description="Lista de productos con cantidad")
    tipo_origen: str = Field(..., description="compra, donacion, devolucion, traslado, ajuste")
    origen_nombre: str = Field(..., min_length=1, description="Proveedor, donante o tercero")
    ubicacion: Optional[str] = Field(None, description="Ubicación donde se almacena")
    observaciones: Optional[str] = None
    usuario: str = "admin"
    
    @validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Debe haber al menos un producto")
        
        for producto in v:
            if 'producto_id' not in producto or 'cantidad' not in producto:
                raise ValueError("Cada producto debe tener producto_id y cantidad")
            if producto['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
        
        return v
    
    @validator('tipo_origen')
    def validar_tipo_origen(cls, v):
        tipos_validos = ['compra', 'donacion', 'devolucion', 'traslado', 'ajuste']
        v_lower = v.lower()
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo de origen debe ser uno de: {', '.join(tipos_validos)}")
        return v_lower