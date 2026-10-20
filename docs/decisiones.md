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

## Inventario (Fase 3)

- Cada producto tiene dos datos separados: **forma de venta** (por unidad o por importe) y **control de inventario** (contar unidades, producción aproximada o sin control).
- Un producto por importe no tiene precio fijo y no puede contar unidades.
- La existencia se guarda en el producto o insumo y cada cambio crea un `MovimientoInventario` con la existencia anterior y la resultante, el motivo y el usuario.
- La existencia puede quedar en negativo (decisión 4); se marca como «Negativo, revisar».
- La existencia solo cambia con movimientos: existencia inicial, entradas, salidas y ajustes. No se edita a mano en el formulario del producto.
- No se puede cambiar la unidad de medida de un insumo que ya tiene movimientos.
- Cambios de precio, activaciones, desactivaciones y ajustes quedan en `RegistroActividad`.

## Ventas (Fase 4)

- El servidor calcula los precios y los totales; el navegador solo los muestra.
- Cada línea guarda el nombre y el precio del producto en el momento de la venta, para que el historial no cambie si después cambia el precio.
- Las líneas por importe guardan solo el valor pagado; la cantidad y el precio unitario quedan vacíos.
- Cada pantalla de venta lleva un `codigo_operacion` único: si el mismo formulario llega dos veces, se guarda una sola venta.
- Si una bebida no tiene existencias suficientes, la venta se guarda y se muestra una advertencia (decisión 4).
- Solo el administrador anula ventas. La anulación exige un motivo, no borra la venta y devuelve las bebidas al inventario una sola vez.
- El empleado solo ve sus propias ventas del día.

## Reglas generales

- El dinero se guarda como `Decimal`, nunca como número de punto flotante.
- Nada con historial se borra: productos e insumos se desactivan; ventas y compras se anulan.
- Ventas, compras y ajustes se guardan dentro de transacciones atómicas.
