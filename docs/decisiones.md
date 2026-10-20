# Decisiones del proyecto

## Negocio

- Nombre: **Panadería Rico Pan de Samuelito**. Está en `NOMBRE_NEGOCIO` dentro de `config/settings.py`.

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

## Compras (Fase 5)

- Una compra puede tener varias líneas de tres tipos: producto para la venta (bebidas), insumo de producción, o materiales y otros (texto libre, no afecta el inventario).
- Por cada línea se escribe la cantidad y el valor pagado. El sistema calcula el costo unitario.
- Una compra puede quedar **pendiente de pago**: suma al inventario desde que se registra, pero no resta en la caja hasta que se marque como pagada.
- Anular una compra descuenta del inventario lo que había sumado, una sola vez, sin borrar el registro.

## Gastos y caja (Fase 5)

- Los gastos son pagos generales (servicios, arriendo, transporte, mantenimiento). Las compras de artículos **no** se registran como gastos, para no contarlas dos veces.
- Efectivo esperado = efectivo al abrir + ventas en efectivo + otras entradas − gastos en efectivo − compras pagadas en efectivo − otras salidas.
- Las transferencias se muestran aparte, porque no entran a la caja física.
- El efectivo al abrir se sugiere con lo contado en el cierre anterior.
- Solo hay un cierre por día y no se modifica. Si después se registran movimientos de ese día, la pantalla avisa de la diferencia sin cambiar el cierre guardado.
- Si el efectivo esperado da negativo, se avisa que probablemente falta registrar algo.

## Producción (Fase 5)

- El empleado y el administrador pueden registrar producción. Solo el administrador anula.
- Ningún dato del resultado es obligatorio: bandejas, unidades aproximadas o un intervalo (desde–hasta). Se muestran siempre como «aprox.».
- Los insumos usados son opcionales y se descuentan del inventario. Si un insumo se repite en la misma preparación, se suma.
- La venta de pan **no** descuenta insumos: solo lo hace el registro de producción.

## Informes (Fase 6)

- Tres tipos de informe: diario, semanal (de lunes a domingo) y mensual, con botones para ir al período anterior y al siguiente. Solo los ve el administrador.
- Las fechas se calculan con la hora de Colombia. Las ventas y gastos anulados no se cuentan.
- Se separan tres ideas que no son lo mismo:
  - **Ventas:** lo que se vendió.
  - **Flujo de caja:** el dinero que realmente entró y salió (ventas cobradas, gastos pagados, compras pagadas por su fecha de pago, entradas y retiros de caja).
  - **Resultado preliminar:** ventas − costo de las bebidas vendidas − costo de los insumos usados en producción − gastos generales.
- Los costos usan el precio promedio pagado en las compras registradas. Para insumos sin compras se usa el costo de referencia.
- El resultado siempre se muestra como **preliminar** y lista lo que falta para que sea exacto (por ejemplo, bebidas sin compras registradas o producción sin insumos).
- Las compras nunca se suman como gastos.
- El panel de inicio muestra datos reales: ventas y gastos de hoy, compras del mes y pendientes, alertas de inventario, ventas de la semana y últimas ventas. El empleado solo ve sus ventas del día y la producción del día.

## Diseño visual

- Paleta «Tinta y durazno», elegida por el propietario entre tres opciones:
  - Menú lateral azul tinta `#1f2a37`, con la opción activa en durazno claro `#f4b08a`.
  - Color principal durazno horneado `#b5551f` para el botón principal, los precios y el total de la venta.
  - Fondo crema muy claro `#f9f7f4` y tarjetas blancas.
- Bordes de 2px, esquinas redondeadas de 12px, sin sombras ni degradados.
- Tipografías: Poppins para títulos y totales, Nunito Sans para el texto.
- Verde, rojo y ámbar solo para estados (normal, error, advertencia).
- Los colores están en variables con nombres genéricos (`--principal`, `--acento`, `--menu-fondo`…) en `static/css/base.css`. Para cambiar de paleta solo se cambian los valores.
- `VERSION_ESTILOS` en `config/settings.py` se agrega a los enlaces de CSS y JS. Al cambiar los estilos se aumenta ese número para que el navegador no use una copia vieja.

## Reglas generales

- El dinero se guarda como `Decimal`, nunca como número de punto flotante.
- Nada con historial se borra: productos e insumos se desactivan; ventas y compras se anulan.
- Ventas, compras y ajustes se guardan dentro de transacciones atómicas.
