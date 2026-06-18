/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"


/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <string.h>
#include <stdint.h>
#include <stdio.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define RX_MAX      256
#define EOF_MARK    0x00

#define PWM_ARR         999U
#define SAMPLE_RATE_HZ  100000U
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

	volatile uint32_t dbg_step = 0;

	volatile uint32_t dbg_rx_count = 0;
	volatile uint32_t dbg_eof_count = 0;
	volatile uint32_t dbg_decode_ok = 0;
	volatile uint32_t dbg_crc_ok = 0;
	volatile uint32_t dbg_cmd10 = 0;
	volatile uint32_t dbg_cmd11 = 0;

	volatile uint8_t dbg_cmd = 0;
	volatile uint8_t dbg_len = 0;
	volatile uint8_t dbg_payload0 = 0;

	volatile uint16_t dbg_crc_rx = 0;
	volatile uint16_t dbg_crc_calc = 0;

	volatile uint32_t dbg_calls = 0;
	volatile uint32_t dbg_tim3 = 0;
	volatile uint16_t dbg_ccr = 0;

/* USER CODE BEGIN PV */
typedef enum{
    WAVE_SINE     = 0X00,
    WAVE_SQUARE   = 0X01,
    WAVE_TRIANGLE = 0X02,
    WAVE_SAW      = 0x03
} WaveType_t;

static volatile WaveType_t currentWave = WAVE_SINE;

static volatile uint8_t outputEnable = 0;

static volatile uint32_t phaseAcc = 0;
static volatile uint32_t phaseStep = 0;

const uint16_t sineTable[256] =
{
500,512,524,537,549,561,573,585,
597,609,620,632,643,654,665,675,
686,696,706,715,724,733,742,750,
758,765,772,779,785,791,796,801,
805,809,812,815,817,819,820,821,
821,821,820,819,817,815,812,809,
805,801,796,791,785,779,772,765,
758,750,742,733,724,715,706,696,
686,675,665,654,643,632,620,609,
597,585,573,561,549,537,524,512,
500,487,475,462,450,438,426,414,
402,390,379,367,356,345,334,324,
313,303,293,284,275,266,257,249,
241,234,227,220,214,208,203,198,
194,190,187,184,182,180,179,178,
178,178,179,180,182,184,187,190,
194,198,203,208,214,220,227,234,
241,249,257,266,275,284,293,303,
313,324,334,345,356,367,379,390,
402,414,426,438,450,462,475,487,
500,512,524,537,549,561,573,585,
597,609,620,632,643,654,665,675,
686,696,706,715,724,733,742,750,
758,765,772,779,785,791,796,801,
805,809,812,815,817,819,820,821,
821,821,820,819,817,815,812,809,
805,801,796,791,785,779,772,765,
758,750,742,733,724,715,706,696,
686,675,665,654,643,632,620,609,
597,585,573,561,549,537,524,512,
500,487,475,462,450,438,426,414,
402,390,379,367,356,345,334,324,
313,303,293,284,275,266,257,249,
241,234,227,220,214,208,203,198,
194,190,187,184,182,180,179,178,
178,178,179,180,182,184,187,190,
194,198,203,208,214,220,227,234,
241,249,257,266,275,284,293,303,
313,324,334,345,356,367,379,390,
402,414,426,438,450,462,475,487
};
uint8_t encoded_buffer[RX_MAX];
uint8_t decoded_buffer[RX_MAX];
uint8_t tx_buffer[] = "|";
uint16_t rx_index = 0;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */
void WaveGen_SetWaveform(uint8_t waveform);
void WaveGen_SetFrequency(uint32_t freq);

uint16_t WaveGen_GetNextSample(void);

int cobs_decode(
    const uint8_t *input,
    uint16_t input_len,
    uint8_t *output);

uint16_t crc16_ccitt(
    uint8_t *data,
    uint16_t length);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
void WaveGen_SetWaveform(uint8_t Waveform)
{
    currentWave = (WaveType_t)Waveform;
}

void WaveGen_SetFrequency(uint32_t FREQ)
{
    uint64_t temp;
    temp =
        ((uint64_t)FREQ << 32);
    phaseStep =
        (uint32_t)(temp / SAMPLE_RATE_HZ);
}

uint16_t WaveGen_GetNextSample(void)
{
	dbg_calls++;
    phaseAcc += phaseStep;
    uint16_t phase = (uint16_t)(phaseAcc >> 16);

    switch(currentWave)
    {
        case WAVE_SINE:
        {
            uint8_t index =
                phase >> 8;

            return sineTable[index];
        }
        case WAVE_SQUARE:
            return
                (phase < 32768)
                ? PWM_ARR
                : 0;

        case WAVE_TRIANGLE:
            if(phase < 32768){
                return
                    ((uint32_t)phase
                    * PWM_ARR)
                    >> 15;
            }
            return
                ((uint32_t)(65535-phase)
                * PWM_ARR)
                >> 15;

        case WAVE_SAW:
            return
                ((uint32_t)phase
                *PWM_ARR)
                >> 16;
    }
    return 0;
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if(htim->Instance == TIM3)
    {
    	dbg_tim3++;
        if(outputEnable)
        {
        	dbg_ccr = WaveGen_GetNextSample();
        	TIM1->CCR1 = dbg_ccr;
        	//TIM1->CCR1 = 500;
        }
        else
        {
            TIM1->CCR1 = 0;
        }
    }
}

int cobs_decode(
    const uint8_t *input,
    uint16_t input_len,
    uint8_t *output
)
{
    uint16_t in_index = 0;
    uint16_t out_index = 0;

    while(in_index < input_len)
    {
        uint8_t code = input[in_index++];

        if(code == 0)
            return -1;

        for(uint8_t i = 1; i < code; i++)
        {
            if(in_index >= input_len)
                return -2;

            output[out_index++] = input[in_index++];
        }

        if(code < 0xFF && in_index < input_len)
        {
            output[out_index++] = 0x00;
        }
    }

    return out_index;
}
uint16_t crc16_ccitt(uint8_t *data, uint16_t length)
{
    uint16_t crc = 0xFFFF;

    for(uint16_t i = 0; i < length; i++)
    {
        crc ^= (uint16_t)data[i] << 8;

        for(uint8_t j = 0; j < 8; j++)
        {
            if(crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc <<= 1;
        }
    }

    return crc;
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_TIM1_Init();
  MX_TIM3_Init();
  MX_USART2_UART_Init();
  /* USER CODE BEGIN 2 */
  HAL_TIM_PWM_Start(
		  &htim1,
          TIM_CHANNEL_1);

  uint8_t rx_byte;

  /* USER CODE END 2 */
  //TIM1->CCR1 = 32768;   // 50%
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
 /*
  while (1)
  {
	  if(HAL_UART_Receive(
	              &huart2,
	              &rx_byte,
	              1,
	              HAL_MAX_DELAY
	          ) == HAL_OK)
	          {
	              // Fin de trama
	              if(rx_byte == EOF_MARK)
	              {
	                  int decoded_len;

	                  decoded_len = cobs_decode(
	                      encoded_buffer,
	                      rx_index,
	                      decoded_buffer
	                  );

	                  if(decoded_len > 0)
	                  {
	                      //--------------------------------
	                      // Parsear trama original
	                      //--------------------------------

	                      uint8_t SEQ = decoded_buffer[0];
	                      uint8_t CMD = decoded_buffer[1];
	                      uint8_t LEN = decoded_buffer[2];

	                      uint8_t payload[254];

	                      memcpy(
	                          payload,
	                          &decoded_buffer[3],
	                          LEN
	                      );

	                      //--------------------------------
	                      // CRC recibido
	                      //--------------------------------

	                      uint16_t received_crc;

	                      received_crc =
	                          ((uint16_t)decoded_buffer[3 + LEN] << 8) |
	                          decoded_buffer[4 + LEN];

	                      //--------------------------------
	                      // CRC calculado
	                      //--------------------------------

	                      uint16_t calculated_crc;

	                      calculated_crc =
	                          crc16_ccitt(
	                              decoded_buffer,
	                              3 + LEN
	                          );

	                      //--------------------------------
	                      // Verificación
	                      //--------------------------------

	                      if(received_crc == calculated_crc)
	                      {
	                          // TRAMA VÁLIDA

	                          // uint8_t payload[4] = {0x01, 0x02, 0x03, 0x04};
	                          if(CMD == 0x10)
	                          {
	                              if(LEN == 5)
	                              {
	                              uint32_t FREQ = ((uint32_t)payload[3] << 24) |
	                                              ((uint32_t)payload[2] << 16) |
	                                              ((uint32_t)payload[1] <<  8) |
	                                              ((uint32_t)payload[0]       );

	                              uint8_t waveform = payload[4];

	                              WaveGen_SetFrequency(FREQ);

	                              WaveGen_SetWaveform(waveform);

	                              }

	                          }

	                          else if(CMD == 0x11)
	                          {
	                              if(LEN == 1)
	                              {
	                                  if(payload[0] == 0x01)
	                                  {
	                                      outputEnable = 1;

	                                      HAL_TIM_PWM_Start_IT(
	                                          &htim1,
											  TIM_CHANNEL_1);
	                                      HAL_TIM_Base_Start_IT(
	                                      	  &htim3);
	                                  }
	                                  else
	                                  {
	                                      outputEnable = 0;
	                                      TIM1->CCR1 = 0;

	                                      HAL_TIM_Base_Stop_IT(
	                                          &htim3);
	                                      HAL_TIM_PWM_Stop(
	                                      	  &htim1,
	                                          TIM_CHANNEL_1);
	                                  }
	                              }
	                          }
	                      }
	                  }
	              }
	          }
  }
}
*/

  while (1)
  {


      if(HAL_UART_Receive(
              &huart2,
              &rx_byte,
              1,
              HAL_MAX_DELAY
         ) == HAL_OK)
      {
          dbg_rx_count++;

          dbg_step = 2;

          if(rx_byte == EOF_MARK)
          {
              HAL_UART_Transmit(&huart2, tx_buffer, sizeof(tx_buffer), _TIMEOUT);
        	  dbg_eof_count++;

              dbg_step = 3;

              int decoded_len =
                  cobs_decode(
                      encoded_buffer,
                      rx_index,
                      decoded_buffer
                  );

              if(decoded_len > 0)
              {
                  dbg_decode_ok++;

                  dbg_step = 4;

                  uint8_t SEQ = decoded_buffer[0];
                  uint8_t CMD = decoded_buffer[1];
                  uint8_t LEN = decoded_buffer[2];

                  char msg[20];

                  sprintf(msg, "CMD=%u\r\n", CMD);

                  HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), 100);

                  dbg_cmd = CMD;
                  dbg_len = LEN;

                  uint8_t payload[254];

                  memcpy(
                      payload,
                      &decoded_buffer[3],
                      LEN
                  );

                  dbg_payload0 = payload[0];

                  uint16_t received_crc =
                      ((uint16_t)decoded_buffer[4 + LEN] << 8) |
                      decoded_buffer[3 + LEN];

                  uint16_t calculated_crc =
                      crc16_ccitt(
                          decoded_buffer,
                          3 + LEN
                      );

                  dbg_crc_rx   = received_crc;
                  dbg_crc_calc = calculated_crc;

                  char msg_crc[80];

                  sprintf(msg_crc,
                          "RX_CRC=0x%04X CALC_CRC=0x%04X\r\n",
                          received_crc,
                          calculated_crc);

                  HAL_UART_Transmit(&huart2,
                                    (uint8_t *)msg_crc,
                                    strlen(msg_crc),
                                    100);

                  if(received_crc == calculated_crc)
                  {
                      dbg_crc_ok++;

                      dbg_step = 5;

                      if(CMD == 0x10)
                      {
                          dbg_cmd10++;

                          dbg_step = 6;

                          if(LEN == 5)
                          {
                              uint32_t FREQ =
                                  ((uint32_t)payload[3] << 24) |
                                  ((uint32_t)payload[2] << 16) |
                                  ((uint32_t)payload[1] << 8 ) |
                                  ((uint32_t)payload[0]);

                              uint8_t waveform = payload[4];

                              char msg[50];
                              sprintf(msg, "FREQ=%lu WAVE=%u\r\n", FREQ, waveform);
                              HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), 100);

                              WaveGen_SetFrequency(FREQ);

                              char msg_phs[80];
                              sprintf(msg_phs,
                                      "FREQ=%lu phaseStep=%lu\r\n",
                                      FREQ,
                                      phaseStep);

                              HAL_UART_Transmit(&huart2,
                                                (uint8_t *)msg_phs,
                                                strlen(msg_phs),
                                                100);

                              WaveGen_SetWaveform(waveform);
                              char msg_wvf[80];
                              sprintf(msg_wvf,
                                      "waveform=%u currentWave=%u\r\n",
                                      waveform,
                                      currentWave);

                              HAL_UART_Transmit(&huart2,
                                                (uint8_t *)msg_wvf,
                                                strlen(msg_wvf),
                                                100);

                              dbg_step = 7;
                          }
                      }
                      else if(CMD == 0x11)
                      {
                          dbg_cmd11++;

                          dbg_step = 8;
                          char msg_out[30];
                          if(LEN == 1)
                          {
                              if(payload[0] == 0x01)
                              {
                                  outputEnable = 1;
                                  HAL_TIM_PWM_Start_IT(
                                      &htim1,
                                      TIM_CHANNEL_1
                                  );

                                  HAL_TIM_Base_Start_IT(
                                      &htim3
                                  );

                                  char msg_tim3[] = "TIM3 START\r\n";
                                  HAL_UART_Transmit(&huart2,
                                                    (uint8_t*)msg_tim3,
                                                    strlen(msg_tim3),
                                                    100);

                                  dbg_step = 9;
                              }
                              else
                              {
                                  outputEnable = 0;

                                  TIM1->CCR1 = 0;
                                  HAL_TIM_Base_Stop_IT(
                                      &htim3
                                  );

                                  HAL_TIM_PWM_Stop(
                                      &htim1,
                                      TIM_CHANNEL_1
                                  );

                                  dbg_step = 10;
                              }
                          }
                          sprintf(msg_out, "outputEnable=%u\r\n", outputEnable);

                          HAL_UART_Transmit(&huart2,
                        		  (uint8_t *)msg_out,
                                  strlen(msg_out),
								  100);

                          char msg_dbg_tim3[80];

                          sprintf(msg_dbg_tim3,
                                  "dbg_tim3=%lu dbg_calls=%lu\r\n",
                                  dbg_tim3,
                                  dbg_calls);

                          HAL_UART_Transmit(&huart2,
                                            (uint8_t*)msg_dbg_tim3,
                                            strlen(msg_dbg_tim3),
                                            100);

                          char msg_ccr[50];

                          sprintf(msg_ccr,
                                  "dbg_ccr=%u\r\n",
                                  dbg_ccr);

                          HAL_UART_Transmit(&huart2,
                                            (uint8_t *)msg_ccr,
                                            strlen(msg_ccr),
                                            100);

                          char msg_arr[50];

                          sprintf(msg_arr,
                                  "ARR=%lu\r\n",
                                  TIM1->ARR);

                          HAL_UART_Transmit(&huart2,
                                            (uint8_t*)msg_arr,
                                            strlen(msg_arr),
                                            100);

                      }
                  }
                  else
                  {
                      dbg_step = 50;   // CRC ERROR
                  }
              }
              else
              {
                  dbg_step = 40;       // COBS ERROR
              }

              rx_index = 0;
          }
          else
          {
              if(rx_index < sizeof(encoded_buffer))
              {
                  encoded_buffer[rx_index++] = rx_byte;
                  //HAL_UART_Transmit(&huart2, encoded_buffer, sizeof(encoded_buffer), _TIMEOUT);
              }
              else
              {
                  rx_index = 0;
                  dbg_step = 60;       // BUFFER OVERFLOW
              }
          }
      }
  }
}
/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  __HAL_FLASH_SET_LATENCY(FLASH_LATENCY_1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSIDiv = RCC_HSI_DIV1;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
