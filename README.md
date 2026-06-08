# 🏛️ Sistema Municipal de Criptoactivos

Este proyecto es una simulación interactiva de una red de moneda digital local. Permite entender cómo interactúan diferentes usuarios dentro de una economía circular comunitaria.

## 👥 Roles del Sistema

El sistema cuenta con tres tipos de usuarios:
* **🏛️ Estado:** Emite la moneda, reparte fondos y supervisa la cantidad de dinero total circulando en la red.
* **👤 Ciudadano:** Puede enviar dinero a otros usuarios mediante transferencias directas y revisar sus saldos.
* **🏪 Comercio:** Recibe pagos de los ciudadanos y puede devolver el dinero acumulado al Estado para obtener ventajas fiscales.

## 🚀 Funcionalidades Principales

* **Billetera en vivo:** Los saldos se actualizan automáticamente en la pantalla cada segundo sin necesidad de recargar la página.
* **Oxidación de Moneda (Demurrage):** Si el dinero de un ciudadano no se mueve, pierde un pequeño porcentaje con el tiempo para incentivar el gasto en el comercio local.
* **Historial de Operaciones:** Un registro público e inmediato de todas las transferencias realizadas dentro de la red.
* **Modo Demo:** Incluye botones rápidos en el inicio de sesión para entrar como cualquiera de los usuarios de prueba al instante.

## 🛠️ Tecnologías Básicas

* **Servidor (Backend):** Python con Flask.
* **Base de Datos:** SQLite (guarda de forma simple el historial de transacciones).
* **Diseño (Frontend):** HTML, CSS moderno y Jinja2 para las plantillas visuales.

## 📂 Archivos del Frontend

* `base.html`: Estructura visual general y diseño de la aplicación.
* `login.html`: Pantalla de acceso con accesos rápidos de demostración.
* `state.html`: Panel de control exclusivo para la gestión del Estado.
* `citizen.html`: Billetera virtual para el uso de los ciudadanos.
* `commerce.html`: Punto de venta interactivo para los comercios locales.