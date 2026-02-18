# app/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Producto(Base):
    __tablename__ = "productos"
    
    # ===== ÍNDICES PARA BÚSQUEDAS RÁPIDAS =====
    __table_args__ = (
        Index('idx_producto_codigo', 'codigo'),        # Búsqueda por código
        Index('idx_producto_nombre', 'nombre'),        # Búsqueda por nombre
        Index('idx_producto_categoria', 'categoria'),  # Filtros por categoría
    )
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=True)
    stock_minimo = Column(Integer, default=0)
    stock_actual = Column(Integer, default=0)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación con movimientos
    movimientos = relationship("Movimiento", back_populates="producto", cascade="all, delete-orphan")

class Movimiento(Base):
    __tablename__ = "movimientos"
    
    # ===== ÍNDICES PARA MOVIMIENTOS =====
    __table_args__ = (
        Index('idx_movimiento_fecha', 'fecha_movimiento'),      # Ordenar por fecha
        Index('idx_movimiento_producto', 'producto_id'),        # JOIN con productos
        Index('idx_movimiento_tipo', 'tipo'),                   # Filtrar entrada/salida
        Index('idx_movimiento_fecha_tipo', 'fecha_movimiento', 'tipo'),  # Filtros compuestos
    )
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"))
    tipo = Column(String, nullable=False)  # entrada o salida
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String, nullable=True)
    tipo_origen = Column(String, nullable=True)  # compra, donacion, etc.
    origen_nombre = Column(String, nullable=True)  # Nombre del proveedor/donante
    ubicacion = Column(String, nullable=True)
    notas = Column(String, nullable=True)
    cliente_destino = Column(String, nullable=True)  # Para salidas
    usuario = Column(String, nullable=False, default="admin")
    fecha_movimiento = Column(DateTime, default=datetime.utcnow)
    pdf_firmado = Column(String, nullable=True)  # Ruta del archivo PDF
    pdf_nombre = Column(String, nullable=True)   # Nombre original del archivo
    
    # Relación
    producto = relationship("Producto", back_populates="movimientos")