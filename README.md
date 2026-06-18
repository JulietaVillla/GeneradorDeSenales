# SelectorDeSeñal — Generador de Señales STM32

Sistema de generación de señales analógicas basado en el microcontrolador **STM32C031C6**, con interfaz de escritorio para control en tiempo real vía UART.

---

## Descripción general

El proyecto está compuesto por dos partes:

- **Firmware** (C / STM32CubeIDE): corre en el STM32C031C6 y genera señales PWM con modulación por tabla de muestras, recibiendo comandos desde la PC.
- **SelectorDeSeñal** (Python): aplicación de escritorio con osciloscopio visual, selector de forma de onda, control de frecuencia y log de tramas.

La comunicación entre ambas capas usa el protocolo **FrameLink**: tramas binarias con número de secuencia, CRC-16/CCITT y codificación COBS sobre UART.

---

## Hardware

| Componente | Detalle |
|---|---|
| MCU | STM32C031C6Tx (Cortex-M0+, LQFP48) |
| Salida PWM | TIM1 CH1 — PA0 |
| UART | USART2 — TX: PA2 / RX: PA3 |
| Sample rate | 100 000 Hz |
| Resolución PWM | 10 bits (ARR = 999) |

---

## Formas de onda soportadas

| ID | Nombre | Descripción |
|---|---|---|
| `0x00` | SINE | Senoidal (tabla de 256 muestras) |
| `0x01` | SQUARE | Cuadrada |
| `0x02` | TRIANGLE | Triangular |
| `0x03` | SAWTOOTH | Diente de sierra |

---

## Protocolo FrameLink

Cada trama tiene la siguiente estructura antes de la codificación COBS:

```
[ SEQ (1B) | CMD (1B) | LEN (1B) | PAYLOAD (N B) | CRC16 (2B) ]
```

seguida de un byte delimitador `0x00`.

### Comandos

| CMD | Código | Payload | Descripción |
|---|---|---|---|
| `SET_CONFIG` | `0x10` | `uint32 freq_hz` + `uint8 waveform` | Configura frecuencia y forma de onda |
| `OUTPUT_ENABLE` | `0x11` | `uint8 enable` (0 o 1) | Activa o desactiva la salida |

El CRC se calcula sobre `SEQ + CMD + LEN + PAYLOAD` usando el polinomio **CRC-16/CCITT** (init `0xFFFF`, poly `0x1021`).

---

## Estructura del repositorio

```
GeneradorDeSenales/
├── GeneradorDeSeñales/         # Proyecto STM32CubeIDE
│   ├── Core/
│   │   └── Src/
│   │       ├── main.c          # Lógica principal + ISR de TIM3 y USART2
│   │       ├── tim.c           # Configuración de TIM1 y TIM3
│   │       └── usart.c         # Configuración de USART2 con DMA
│   ├── Drivers/                # HAL de STM32 (generado por CubeMX)
│   ├── GeneradorDeSeñales.ioc  # Configuración de STM32CubeMX
│   └── STM32C031C6TX_FLASH.ld  # Linker script
└── SelectorDeSeñal.py          # Aplicación de escritorio OsciLink
```

---

## Requisitos — SelectorDeSeñal (Python)

- Python 3.9+
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- [pyserial](https://pyserial.readthedocs.io/)

```bash
pip install customtkinter pyserial
```

---

## Cómo usar

### 1. Flashear el firmware

Abrir el proyecto `GeneradorDeSeñales/` en **STM32CubeIDE**, compilar y flashear en el STM32C031C6.

### 2. Ejecutar la interfaz

```bash
python SelectorDeSeñal.py
```

### 3. Conectar y controlar

1. Seleccionar el puerto COM / tty del dispositivo y el baudrate (por defecto 115200).
2. Hacer clic en **CONNECT**.
3. Elegir la forma de onda (SINE / SQR / TRI / SAW) e ingresar la frecuencia deseada en Hz.
4. Presionar **SET** para enviar la configuración al microcontrolador.
5. Presionar **OUT** para habilitar o deshabilitar la salida física.

El osciloscopio de la interfaz muestra una vista previa animada de la señal configurada.

---

## Interfaz SelectorDeSeñal

La aplicación está dividida en tres capas internas:

- **SelectorDeSeñal**: interfaz gráfica construida con `customtkinter` y `tkinter`.
- **FrameLink**: capa de protocolo que arma, codifica y transmite las tramas.
- **UART**: capa de transporte usando `pyserial`.

La paleta visual utiliza tonos rosa/magenta sobre fondo oscuro.

---

## Notas

- La frecuencia máxima está limitada por el sample rate de 100 kHz del firmware y la resolución de la tabla de seno de 256 muestras.
- La aplicación funciona en modo de solo visualización si `pyserial` no está instalado.
- El campo de frecuencia acepta valores entre 1 Hz y 4 294 967 295 Hz; el rango útil real depende del hardware.
