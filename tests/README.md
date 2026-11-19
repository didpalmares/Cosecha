# Pruebas automáticas

Pruebas de extremo a extremo con [Playwright](https://playwright.dev/python/) sobre la app compilada: app de campo, visor
(reproducción y Gerencia), administración (usuarios y formulario editable), registro por voz y tarjetas NFC, auditoría, límite de la
plantación, historial, APK, pantalla bloqueada, alertas y reportes, carga masiva, panel del día, ciclo de censo aprobado, planificación del censo,
y piloto de IA (servicio de IA simulado). GitHub se simula: las pruebas no leen ni escriben datos reales.

Se ejecutan solas en GitHub Actions (`.github/workflows/pruebas.yml`) con cada cambio en `src/` o `tests/`.

## Ejecutarlas en el computador

```bash
pip install playwright pillow openpyxl && python -m playwright install chromium
python src/build.py RUTA/node_modules src/marca
python -m http.server 8765 --bind 127.0.0.1
python tests/run_all.py            # todas
python tests/run_all.py gerencia   # solo las que contienen «gerencia»
```

En Windows se puede usar Edge en lugar de Chromium: `set PW_CANAL=msedge`.

Si la app se sirve en otra dirección, indíquela con `PRUEBAS_URL` (por ejemplo `PRUEBAS_URL=http://127.0.0.1:8799`);
sin ella se usa `http://127.0.0.1:8765`, la de GitHub Actions.

`prueba_cosecha.py` prueba las labores en la App (Corte, Recolección con búfalo, Corte y recolección y Alce de fruto en sendero),
y `prueba_visor_cosecha.py` recorre la cosecha de punta a punta: la App arma el GeoJSON de tres jornadas (Corte, Recolección con
descargues y Alce con acopios, con fuente, pasadas y transitabilidad de cada lote), el visor lo lee y se verifican colores, leyenda,
ficha, filtro por labor, indicadores de Gerencia (🌴 Cosecha: R por labor, viajes descargados, R alzados, pendiente de alce),
tabla por lote, mapa de acopios y transitabilidad por lote.

Códigos de cosecha que usan las pruebas: R = racimo (en Corte, Recolección y Corte y recolección se suma a la palma más cercana;
en Alce, al acopio del sendero) y D = descargue del viaje (Recolección y Corte y recolección; se confirma con una segunda pasada
en 8 s o menos y guarda los racimos del viaje). Las tarjetas NFC llevan el texto «R» o «D» (también se acepta «cos:R»); cualquier
otra tarjeta (por ejemplo «C», «V» o «pol:A» de Polinización) se rechaza. Por voz: «racimo» / «erre» y «descargue».

Los datos de las pruebas son ficticios (nombres, cédulas y el polígono de `fixtures/` no son reales).
