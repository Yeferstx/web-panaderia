# Decisiones del proyecto

## Tecnología

- Django 5.2 LTS (soporte hasta abril de 2028), Python 3.13, PostgreSQL con psycopg 3.
- Producción: gunicorn, whitenoise y dj-database-url. Despliegue previsto en Render con base de datos en Supabase.
- Modelo de usuario propio (`usuarios.Usuario`) desde el inicio.
- Roles con grupos de Django: Administrador y Empleado.

## Negocio (aprobadas por el propietario)

1. **Precios de prueba:** el catálogo inicial lleva precios aproximados y económicos de una panadería colombiana. Son valores de prueba que el administrador puede editar. La empanada empieza en $2.500.
2. **Pan por importe:** hay dos conceptos, «Pan básico por importe» (pan pequeño) y «Pan especial por importe» (pan más grande). Se registra el valor que paga el cliente, sin cantidad de unidades.
3. **Fiado:** no se incluye por ahora.
4. **Existencias insuficientes:** la venta se permite aunque el inventario no alcance, pero se muestra una advertencia clara. El sistema registra el movimiento real, deja ver la existencia en negativo y permite corregirla con un ajuste documentado. Nunca corrige el inventario en silencio.
5. **Permisos:** el empleado registra ventas y producción. El administrador gestiona compras, gastos, inventario, precios, usuarios e informes.

## Reglas generales

- El dinero se guarda como `Decimal`, nunca como número de punto flotante.
- Nada con historial se borra: productos e insumos se desactivan; ventas y compras se anulan.
- Ventas, compras y ajustes se guardan dentro de transacciones atómicas.
